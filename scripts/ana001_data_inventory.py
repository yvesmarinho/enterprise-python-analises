#!/usr/bin/env python3
"""
ANA001 - Inventario de dados e diagnostico inicial de performance N8N.

Objetivo:
1) Descobrir quais dados realmente existem nas fontes (Prometheus/VictoriaMetrics e DB N8N).
2) Medir cobertura temporal e cardinalidade basica para workflows.
3) Preparar evidencias para a analise de causa de lentidao dos workflows N8N.

Boas praticas aplicadas:
- Pydantic para validacao de configuracao e schema de saida.
- HTTPX com timeouts e tratamento de falhas de rede.
- SQLAlchemy para introspecao de schema e consultas SQL seguras.
- Pandas para sumarizacao tabular e geracao de insights.
- Saida reproduzivel em JSON e Markdown.

Exemplo de uso:
    uv run python scripts/ana001_data_inventory.py \
    --from 2026-01-01T00:00:00Z \
    --to 2026-03-19T23:59:59Z \
    --prometheus-url https://prometheus.vya.digital \
    --victoria-metrics-url http://localhost:8428 \
    --output-dir reports

DB opcional:
  export N8N_DB_DSN='postgresql+psycopg2://user:pass@host:5432/n8n'
    uv run python scripts/ana001_data_inventory.py ...
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
from pydantic import BaseModel, Field, ValidationError, model_validator
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

DEFAULT_PROMETHEUS_URL = "https://prometheus.vya.digital"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_STEP = "1h"
DEFAULT_FROM = "2026-01-01T00:00:00Z"
DEFAULT_TO = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

CORE_METRICS = [
    "n8n_workflow_execution_duration_seconds_bucket",
    "n8n_workflow_execution_duration_seconds_sum",
    "n8n_workflow_execution_duration_seconds_count",
    "n8n_api_request_errors_total",
]


class InventoryConfig(BaseModel):
    prometheus_url: str = Field(default=DEFAULT_PROMETHEUS_URL)
    victoria_metrics_url: str | None = None
    n8n_db_dsn: str | None = None
    from_ts: str = Field(default=DEFAULT_FROM)
    to_ts: str = Field(default=DEFAULT_TO)
    step: str = Field(default=DEFAULT_STEP)
    timeout_seconds: int = Field(default=DEFAULT_TIMEOUT_SECONDS, ge=5, le=120)
    output_dir: Path = Field(default=Path("reports"))

    @model_validator(mode="after")
    def validate_time_window(self) -> InventoryConfig:
        start = _parse_dt(self.from_ts)
        end = _parse_dt(self.to_ts)
        if end <= start:
            raise ValueError("to_ts precisa ser maior que from_ts")
        return self


class DataSourceStatus(BaseModel):
    name: str
    url: str | None = None
    reachable: bool
    error: str | None = None


class MetricsInventory(BaseModel):
    backend: str
    status: DataSourceStatus
    n8n_metric_count: int = 0
    n8n_metrics: list[str] = Field(default_factory=list)
    core_metric_presence: dict[str, bool] = Field(default_factory=dict)
    first_sample_utc: str | None = None
    last_sample_utc: str | None = None
    coverage_days: float = 0.0
    instance_count: int = 0
    workflow_count: int = 0
    top_workflows_by_executions: list[dict[str, Any]] = Field(default_factory=list)


class DatabaseInventory(BaseModel):
    status: DataSourceStatus
    table_count: int = 0
    tables: list[str] = Field(default_factory=list)
    has_workflow_table: bool = False
    has_execution_table: bool = False
    workflow_rows: int | None = None
    execution_rows: int | None = None
    execution_rows_last_24h: int | None = None


class Ana001InventoryReport(BaseModel):
    generated_at_utc: str
    objective: str
    config: dict[str, Any]
    prometheus: MetricsInventory
    victoria_metrics: MetricsInventory | None = None
    database: DatabaseInventory | None = None
    analysis_readiness: dict[str, Any]
    recommendations: list[str]


@dataclass
class PromQueryResult:
    result_type: str
    result: list[dict[str, Any]]


def _parse_dt(value: str) -> datetime:
    if value.endswith("Z"):
        value = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _safe_url(url: str | None) -> str | None:
    if not url:
        return None
    return url.rstrip("/")


def _to_iso_utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class PrometheusClient:
    def __init__(self, base_url: str, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.base_url = base_url.rstrip("/")
        timeout = httpx.Timeout(timeout_seconds)
        self.client = httpx.Client(timeout=timeout, follow_redirects=True)

    def close(self) -> None:
        self.client.close()

    def is_reachable(self) -> tuple[bool, str | None]:
        for path in ("/-/ready", "/api/v1/status/buildinfo"):
            try:
                response = self.client.get(f"{self.base_url}{path}")
                if response.status_code == 200:
                    return True, None
            except httpx.HTTPError as exc:
                last_error = str(exc)
                continue
        return False, locals().get("last_error", "backend nao respondeu")

    def label_values(self, label: str) -> list[str]:
        response = self.client.get(f"{self.base_url}/api/v1/label/{label}/values")
        response.raise_for_status()
        payload = response.json()
        return payload.get("data", [])

    def query(self, promql: str) -> PromQueryResult:
        response = self.client.get(
            f"{self.base_url}/api/v1/query",
            params={"query": promql},
        )
        response.raise_for_status()
        payload = response.json().get("data", {})
        return PromQueryResult(result_type=payload.get("resultType", ""), result=payload.get("result", []))

    def query_range(self, promql: str, start: str, end: str, step: str) -> PromQueryResult:
        response = self.client.get(
            f"{self.base_url}/api/v1/query_range",
            params={"query": promql, "start": start, "end": end, "step": step},
        )
        response.raise_for_status()
        payload = response.json().get("data", {})
        return PromQueryResult(result_type=payload.get("resultType", ""), result=payload.get("result", []))

    def series(self, metric_name: str, start: str, end: str) -> list[dict[str, str]]:
        response = self.client.get(
            f"{self.base_url}/api/v1/series",
            params={"match[]": metric_name, "start": start, "end": end},
        )
        response.raise_for_status()
        return response.json().get("data", [])


def _collect_metrics_inventory(config: InventoryConfig, backend_name: str, url: str) -> MetricsInventory:
    client = PrometheusClient(url, timeout_seconds=config.timeout_seconds)
    reachable, error = client.is_reachable()

    status = DataSourceStatus(name=backend_name, url=url, reachable=reachable, error=error)
    inventory = MetricsInventory(backend=backend_name, status=status)

    if not reachable:
        client.close()
        return inventory

    try:
        metric_names = sorted([m for m in client.label_values("__name__") if "n8n" in m.lower()])
        inventory.n8n_metrics = metric_names
        inventory.n8n_metric_count = len(metric_names)
        inventory.core_metric_presence = {name: name in metric_names for name in CORE_METRICS}

        # Cardinalidade historica deve ser baseada em series no intervalo,
        # nao em query instantanea no "agora".
        historical_series = client.series(
            "n8n_workflow_execution_duration_seconds_count",
            start=config.from_ts,
            end=config.to_ts,
        )
        if historical_series:
            df_series = pd.DataFrame(historical_series)
            if "instance" in df_series.columns:
                inventory.instance_count = int(df_series["instance"].nunique())
            if "workflow_id" in df_series.columns:
                inventory.workflow_count = int(df_series["workflow_id"].nunique())

        range_query = "n8n_workflow_execution_duration_seconds_count"
        range_result = client.query_range(
            range_query,
            start=config.from_ts,
            end=config.to_ts,
            step=config.step,
        ).result

        timestamps: list[float] = []
        delta_rows: list[dict[str, Any]] = []
        for series in range_result:
            metric = series.get("metric", {})
            values = series.get("values", [])
            for ts, _ in series.get("values", []):
                timestamps.append(float(ts))

            # Estimativa de execucoes por workflow no periodo com base no contador.
            numeric_values: list[float] = []
            for _, raw_v in values:
                try:
                    numeric_values.append(float(raw_v))
                except (TypeError, ValueError):
                    continue

            if numeric_values:
                executions = max(0.0, max(numeric_values) - min(numeric_values))
                delta_rows.append(
                    {
                        "workflow_id": metric.get("workflow_id", "unknown"),
                        "workflow_name": metric.get("workflow_name", "unknown"),
                        "instance": metric.get("instance", "unknown"),
                        "executions": executions,
                    }
                )

        if timestamps:
            min_ts = min(timestamps)
            max_ts = max(timestamps)
            inventory.first_sample_utc = _to_iso_utc(min_ts)
            inventory.last_sample_utc = _to_iso_utc(max_ts)
            inventory.coverage_days = round((max_ts - min_ts) / 86400.0, 2)

        if delta_rows:
            df_delta = pd.DataFrame(delta_rows)
            top_df = (
                df_delta.groupby(["workflow_id", "workflow_name", "instance"], as_index=False)
                .agg(executions=("executions", "sum"))
                .sort_values("executions", ascending=False)
                .head(10)
            )
            inventory.top_workflows_by_executions = top_df.to_dict(orient="records")

    except httpx.HTTPError as exc:
        inventory.status.error = f"falha em consulta PromQL: {exc}"
    finally:
        client.close()

    return inventory


def _introspect_database(dsn: str, timeout_seconds: int) -> DatabaseInventory:
    status = DataSourceStatus(name="n8n-postgresql", url=None, reachable=False)
    report = DatabaseInventory(status=status)

    try:
        engine = create_engine(
            dsn,
            pool_pre_ping=True,
            connect_args={"connect_timeout": timeout_seconds},
        )
    except SQLAlchemyError as exc:
        report.status.error = f"erro ao criar engine SQLAlchemy: {exc}"
        return report

    try:
        with engine.connect() as conn:
            report.status.reachable = True
            inspector = inspect(engine)
            tables = sorted(inspector.get_table_names(schema="public"))
            report.tables = tables
            report.table_count = len(tables)

            report.has_workflow_table = "workflow_entity" in tables
            report.has_execution_table = "execution_entity" in tables

            if report.has_workflow_table:
                report.workflow_rows = int(pd.read_sql(text("SELECT count(*) AS n FROM workflow_entity"), conn)["n"].iloc[0])

            if report.has_execution_table:
                report.execution_rows = int(pd.read_sql(text("SELECT count(*) AS n FROM execution_entity"), conn)["n"].iloc[0])
                report.execution_rows_last_24h = int(
                    pd.read_sql(
                        text(
                            """
                            SELECT count(*) AS n
                            FROM execution_entity
                            WHERE "startedAt" >= now() - interval '24 hours'
                            """
                        ),
                        conn,
                    )["n"].iloc[0]
                )

    except SQLAlchemyError as exc:
        report.status.error = f"falha na introspecao SQLAlchemy: {exc}"
    finally:
        engine.dispose()

    return report


def _build_readiness(
    prom: MetricsInventory,
    vm: MetricsInventory | None,
    db: DatabaseInventory | None,
) -> dict[str, Any]:
    chosen_long_term = vm if vm and vm.status.reachable else prom

    required_metrics_ok = all(chosen_long_term.core_metric_presence.get(name, False) for name in CORE_METRICS)
    has_temporal_coverage = chosen_long_term.coverage_days >= 7
    has_workflow_cardinality = chosen_long_term.workflow_count > 0

    db_signal_ok = True
    if db:
        db_signal_ok = bool(db.status.reachable and db.has_execution_table)

    ready = required_metrics_ok and has_temporal_coverage and has_workflow_cardinality

    return {
        "ready_for_ana001": ready,
        "selected_backend": chosen_long_term.backend,
        "required_metrics_ok": required_metrics_ok,
        "has_temporal_coverage": has_temporal_coverage,
        "has_workflow_cardinality": has_workflow_cardinality,
        "database_signal_ok": db_signal_ok,
        "observed_workflows": chosen_long_term.workflow_count,
        "observed_instances": chosen_long_term.instance_count,
        "observed_coverage_days": chosen_long_term.coverage_days,
    }


def _build_recommendations(
    readiness: dict[str, Any],
    prom: MetricsInventory,
    vm: MetricsInventory | None,
    db: DatabaseInventory | None,
) -> list[str]:
    recs: list[str] = []

    if not prom.status.reachable:
        recs.append("Restaurar conectividade com Prometheus publico para validacoes rapidas.")

    if vm and not vm.status.reachable:
        recs.append(
            "VictoriaMetrics indisponivel. Abrir SSH SPA e tunnel para executar analise historica (12 meses)."
        )

    selected = vm if vm and vm.status.reachable else prom

    missing = [name for name, ok in selected.core_metric_presence.items() if not ok]
    if missing:
        recs.append(
            "Metricas essenciais ausentes para ANA001: " + ", ".join(missing) + "."
        )

    if selected.coverage_days < 7:
        recs.append(
            "Cobertura temporal baixa. Aumentar janela e priorizar VictoriaMetrics para diagnostico de tendencia."
        )

    if selected.workflow_count == 0:
        recs.append(
            "Nenhum workflow detectado. Validar scrape, labels workflow_id/workflow_name e remote_write."
        )

    if db and db.status.reachable and not db.has_execution_table:
        recs.append(
            "Tabela execution_entity nao encontrada no DB N8N. Revisar schema e versao do banco de aplicacao."
        )

    if readiness.get("ready_for_ana001"):
        recs.append(
            "Ambiente apto para ANA001: executar analyze-n8n com janela ampla e drill-down no pico de latencia."
        )

    if not recs:
        recs.append("Sem recomendacoes adicionais no momento.")

    return recs


def _write_outputs(report: Ana001InventoryReport, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    json_path = output_dir / f"ana001_data_inventory_{stamp}.json"
    md_path = output_dir / f"ana001_data_inventory_{stamp}.md"

    json_path.write_text(
        json.dumps(report.model_dump(), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    lines: list[str] = []
    lines.append("# ANA001 - Data Inventory Report")
    lines.append("")
    lines.append(f"Generated at (UTC): {report.generated_at_utc}")
    lines.append("")
    lines.append("## Objective")
    lines.append(report.objective)
    lines.append("")

    def append_backend(title: str, inv: MetricsInventory) -> None:
        lines.append(f"## {title}")
        lines.append(f"- Reachable: {inv.status.reachable}")
        if inv.status.error:
            lines.append(f"- Error: {inv.status.error}")
        lines.append(f"- N8N metrics: {inv.n8n_metric_count}")
        lines.append(f"- Workflow count: {inv.workflow_count}")
        lines.append(f"- Instance count: {inv.instance_count}")
        lines.append(f"- Coverage days: {inv.coverage_days}")
        lines.append(f"- First sample: {inv.first_sample_utc}")
        lines.append(f"- Last sample: {inv.last_sample_utc}")
        lines.append("- Core metrics presence:")
        for metric_name, ok in inv.core_metric_presence.items():
            lines.append(f"  - {metric_name}: {ok}")
        if inv.top_workflows_by_executions:
            lines.append("- Top workflows by executions:")
            for row in inv.top_workflows_by_executions:
                lines.append(
                    "  - "
                    + f"{row.get('workflow_name')} ({row.get('workflow_id')}) | "
                    + f"instance={row.get('instance')} | executions={row.get('executions', 0):.2f}"
                )
        lines.append("")

    append_backend("Prometheus", report.prometheus)
    if report.victoria_metrics:
        append_backend("VictoriaMetrics", report.victoria_metrics)

    if report.database:
        db = report.database
        lines.append("## N8N Database (SQLAlchemy)")
        lines.append(f"- Reachable: {db.status.reachable}")
        if db.status.error:
            lines.append(f"- Error: {db.status.error}")
        lines.append(f"- Public tables: {db.table_count}")
        lines.append(f"- Has workflow_entity: {db.has_workflow_table}")
        lines.append(f"- Has execution_entity: {db.has_execution_table}")
        lines.append(f"- workflow_entity rows: {db.workflow_rows}")
        lines.append(f"- execution_entity rows: {db.execution_rows}")
        lines.append(f"- execution_entity rows last 24h: {db.execution_rows_last_24h}")
        lines.append("")

    lines.append("## ANA001 Readiness")
    for k, v in report.analysis_readiness.items():
        lines.append(f"- {k}: {v}")
    lines.append("")

    lines.append("## Recommendations")
    for rec in report.recommendations:
        lines.append(f"- {rec}")
    lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ANA001 data inventory and readiness report")
    parser.add_argument("--prometheus-url", default=DEFAULT_PROMETHEUS_URL)
    parser.add_argument("--victoria-metrics-url", default=os.getenv("VICTORIA_METRICS_URL"))
    parser.add_argument("--n8n-db-dsn", default=os.getenv("N8N_DB_DSN"))
    parser.add_argument("--from", dest="from_ts", default=DEFAULT_FROM)
    parser.add_argument("--to", dest="to_ts", default=DEFAULT_TO)
    parser.add_argument("--step", default=DEFAULT_STEP)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--output-dir", default="reports")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    try:
        config = InventoryConfig(
            prometheus_url=_safe_url(args.prometheus_url),
            victoria_metrics_url=_safe_url(args.victoria_metrics_url),
            n8n_db_dsn=args.n8n_db_dsn,
            from_ts=args.from_ts,
            to_ts=args.to_ts,
            step=args.step,
            timeout_seconds=args.timeout_seconds,
            output_dir=Path(args.output_dir),
        )
    except ValidationError as exc:
        print(f"[ERROR] configuracao invalida: {exc}")
        return 2
    except ValueError as exc:
        print(f"[ERROR] {exc}")
        return 2

    print("[INFO] Coletando inventario de dados para ANA001...")

    prometheus_inventory = _collect_metrics_inventory(
        config=config,
        backend_name="prometheus",
        url=config.prometheus_url,
    )

    vm_inventory: MetricsInventory | None = None
    if config.victoria_metrics_url:
        vm_inventory = _collect_metrics_inventory(
            config=config,
            backend_name="victoriametrics",
            url=config.victoria_metrics_url,
        )

    db_inventory: DatabaseInventory | None = None
    if config.n8n_db_dsn:
        db_inventory = _introspect_database(config.n8n_db_dsn, config.timeout_seconds)

    readiness = _build_readiness(prometheus_inventory, vm_inventory, db_inventory)
    recommendations = _build_recommendations(readiness, prometheus_inventory, vm_inventory, db_inventory)

    report = Ana001InventoryReport(
        generated_at_utc=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        objective=(
            "Identificar quais dados existem hoje para diagnosticar fatores de degradacao de "
            "performance dos workflows N8N no projeto ANA001."
        ),
        config={
            "prometheus_url": config.prometheus_url,
            "victoria_metrics_url": config.victoria_metrics_url,
            "n8n_db_dsn": "<set>" if config.n8n_db_dsn else "<not set>",
            "from_ts": config.from_ts,
            "to_ts": config.to_ts,
            "step": config.step,
            "timeout_seconds": config.timeout_seconds,
        },
        prometheus=prometheus_inventory,
        victoria_metrics=vm_inventory,
        database=db_inventory,
        analysis_readiness=readiness,
        recommendations=recommendations,
    )

    json_path, md_path = _write_outputs(report, config.output_dir)

    print("[INFO] Inventario concluido.")
    print(f"[INFO] JSON: {json_path}")
    print(f"[INFO] Markdown: {md_path}")
    print(f"[INFO] Ready for ANA001: {report.analysis_readiness.get('ready_for_ana001')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
