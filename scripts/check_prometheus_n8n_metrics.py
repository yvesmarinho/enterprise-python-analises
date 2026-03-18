"""
Verificação de disponibilidade de métricas N8N no stack de observabilidade.

Arquitetura do stack (docs/Prometheus/docker-compose.yaml):
  Prometheus      — scraping engine, 15 dias de retenção, público HTTPS via Traefik.
  VictoriaMetrics — armazenamento de longo prazo (12 meses), somente interno
                    (http://victoriametrics:8428, sem rota Traefik / sem DNS público).
                    Requer SSH SPA (fwknop) + tunnel para acesso externo:
                      fwknop --rc-file ~/.fwknoprc -n wfdb01 && sleep 3 &&
                      ssh -p 5010 -N -L 8428:victoriametrics:8428 archaris@wfdb01.vya.digital
                      (ou: source .secrets/wfdb01_connection.sh && wfdb01_tunnel_vm)

Este script consulta um ou ambos os backends e exibe:
  - Conectividade e status de cada backend
  - Métricas N8N disponíveis
  - Range de datas dos dados históricos
  - Instâncias (servidores) reportando
  - Lista de workflows monitorados e execuções

Uso:
    python scripts/check_prometheus_n8n_metrics.py
    python scripts/check_prometheus_n8n_metrics.py --victoria-metrics-url http://localhost:8428
    python scripts/check_prometheus_n8n_metrics.py --start 2026-01-01 --end 2026-03-18

Análise Registry: ANA-001 (suporte)
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_PROMETHEUS_URL = "https://prometheus.vya.digital"
DEFAULT_VM_URL: str | None = None  # internal only; set via --victoria-metrics-url or SSH tunnel
PROMETHEUS_RETENTION_DAYS = 15
VM_RETENTION_MONTHS = 12
N8N_METRIC_DURATION = "n8n_workflow_execution_duration_seconds_count"
N8N_METRIC_PREFIX = "n8n"
DEFAULT_START = "2026-01-01T00:00:00Z"
DEFAULT_END_DAYS_BACK = 0  # hoje


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class WorkflowSummary:
    workflow_id: str
    workflow_name: str
    instance: str
    first_seen: datetime.datetime | None
    last_seen: datetime.datetime | None
    total_executions: float


@dataclass
class BackendCheckResult:
    """Diagnostic result for a single metrics backend (Prometheus or VictoriaMetrics)."""

    label: str      # e.g. "Prometheus (público, 15d)"
    url: str
    role: str       # "short-term" | "long-term"
    reachable: bool
    error: str | None = None
    available_n8n_metrics: list[str] = field(default_factory=list)
    data_range_start: datetime.datetime | None = None
    data_range_end: datetime.datetime | None = None
    instances: list[str] = field(default_factory=list)
    workflows: list[WorkflowSummary] = field(default_factory=list)


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _get_json(url: str, timeout: int = 30) -> dict[str, Any]:
    """Perform HTTP GET and parse JSON response."""
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode())


def _prometheus_query(base_url: str, query: str) -> list[dict]:
    """Instant query against Prometheus /api/v1/query."""
    params = urllib.parse.urlencode({"query": query})
    url = f"{base_url}/api/v1/query?{params}"
    data = _get_json(url)
    return data.get("data", {}).get("result", [])


def _prometheus_query_range(
    base_url: str,
    query: str,
    start: str,
    end: str,
    step: str = "1d",
) -> list[dict]:
    """Range query against Prometheus /api/v1/query_range."""
    params = urllib.parse.urlencode({"query": query, "start": start, "end": end, "step": step})
    url = f"{base_url}/api/v1/query_range?{params}"
    data = _get_json(url)
    return data.get("data", {}).get("result", [])


def _list_metric_names(base_url: str) -> list[str]:
    """Return all metric names from Prometheus label __name__ values."""
    url = f"{base_url}/api/v1/label/__name__/values"
    data = _get_json(url)
    return data.get("data", [])


def _ts_to_dt(ts: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)


# ── Analysis logic ────────────────────────────────────────────────────────────

def check_reachability(prometheus_url: str) -> bool:
    """Return True if the Prometheus endpoint answers to /-/ready or /api/v1/status/buildinfo."""
    for path in ("/-/ready", "/api/v1/status/buildinfo"):
        try:
            with urllib.request.urlopen(f"{prometheus_url}{path}", timeout=10) as r:  # noqa: S310
                if r.status == 200:
                    return True
        except Exception:
            continue
    return False


def collect_available_n8n_metrics(prometheus_url: str) -> list[str]:
    """Return list of metric names containing 'n8n'."""
    all_names = _list_metric_names(prometheus_url)
    return sorted(m for m in all_names if N8N_METRIC_PREFIX in m.lower())


def collect_workflow_summaries(
    prometheus_url: str,
    start: str,
    end: str,
) -> tuple[list[WorkflowSummary], datetime.datetime | None, datetime.datetime | None]:
    """
    Query range data and build per-workflow summaries.

    Returns:
        Tuple of (workflow_summaries, global_start, global_end).
    """
    results = _prometheus_query_range(
        prometheus_url,
        N8N_METRIC_DURATION,
        start=start,
        end=end,
        step="1d",
    )

    summaries: list[WorkflowSummary] = []
    all_timestamps: list[float] = []

    for series in results:
        metric = series.get("metric", {})
        values: list[list] = series.get("values", [])

        if not values:
            continue

        timestamps = [v[0] for v in values]
        counts = [float(v[1]) for v in values]
        all_timestamps.extend(timestamps)

        first_dt = _ts_to_dt(min(timestamps))
        last_dt = _ts_to_dt(max(timestamps))
        total_exec = max(counts) if counts else 0.0

        summaries.append(WorkflowSummary(
            workflow_id=metric.get("workflow_id", "unknown"),
            workflow_name=metric.get("workflow_name", "unknown"),
            instance=metric.get("instance", "unknown"),
            first_seen=first_dt,
            last_seen=last_dt,
            total_executions=total_exec,
        ))

    global_start = _ts_to_dt(min(all_timestamps)) if all_timestamps else None
    global_end = _ts_to_dt(max(all_timestamps)) if all_timestamps else None

    return sorted(summaries, key=lambda s: (-s.total_executions, s.workflow_name)), global_start, global_end


def run_backend_check(
    url: str,
    label: str,
    role: str,
    start: str,
    end: str,
) -> BackendCheckResult:
    """Execute full availability check for one metrics backend and return structured result."""
    result = BackendCheckResult(label=label, url=url, role=role, reachable=False)

    if not check_reachability(url):
        result.error = f"Cannot reach {url}"
        return result

    result.reachable = True

    result.available_n8n_metrics = collect_available_n8n_metrics(url)

    if not result.available_n8n_metrics:
        result.error = "No N8N metrics found in label index"
        return result

    workflows, data_start, data_end = collect_workflow_summaries(url, start, end)
    result.workflows = workflows
    result.data_range_start = data_start
    result.data_range_end = data_end
    result.instances = sorted({w.instance for w in workflows})

    return result


# ── Formatting ────────────────────────────────────────────────────────────────

def print_backend_report(r: BackendCheckResult, start: str, end: str) -> None:
    """Print a human-readable diagnostic report for one backend to stdout."""
    sep = "─" * 70
    print(f"\n{'═' * 70}")
    print(f"  {r.label}")
    print(f"  URL  : {r.url}  [{r.role}]")
    print(f"{'═' * 70}")
    print(f"  Status   : {'✅ Acessível' if r.reachable else '❌ Inacessível'}")
    if r.error:
        print(f"  Erro     : {r.error}")
    if not r.reachable:
        return

    # Available metrics
    print(f"\n{sep}")
    print(f"MÉTRICAS N8N DISPONÍVEIS ({len(r.available_n8n_metrics)} encontradas)")
    print(sep)
    for m in r.available_n8n_metrics:
        print(f"  {m}")

    # Data range
    print(f"\n{sep}")
    print("COBERTURA DE DADOS HISTÓRICOS")
    print(sep)
    if r.data_range_start and r.data_range_end:
        print(f"  Primeiro dado: {r.data_range_start.strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"  Último dado  : {r.data_range_end.strftime('%Y-%m-%d %H:%M UTC')}")
        delta = r.data_range_end - r.data_range_start
        print(f"  Cobertura    : {delta.days} dias")
    else:
        print("  ⚠️  Nenhum dado histórico encontrado no período consultado")

    # Instances
    print(f"\n{sep}")
    print(f"INSTÂNCIAS REPORTANDO ({len(r.instances)} servidores)")
    print(sep)
    for inst in r.instances:
        count = sum(1 for w in r.workflows if w.instance == inst)
        print(f"  {inst:30s}  {count} workflows")

    # Workflows
    print(f"\n{sep}")
    print(f"WORKFLOWS MONITORADOS ({len(r.workflows)} séries)")
    print(sep)
    header = f"  {'Workflow':<45} {'Instância':<10} {'Execuções':>12}  {'Última coleta'}"
    print(header)
    print(f"  {'-'*45} {'-'*10} {'-'*12}  {'-'*16}")
    for w in r.workflows:
        last = w.last_seen.strftime("%Y-%m-%d") if w.last_seen else "n/a"
        name = w.workflow_name[:44]
        print(f"  {name:<45} {w.instance:<10} {w.total_executions:>12.0f}  {last}")

    # Assessment for this backend
    print(f"\n{sep}")
    print(f"DIAGNÓSTICO — {r.label}")
    print(sep)
    if r.workflows:
        metric_ok = "n8n_workflow_execution_duration_seconds_bucket" in r.available_n8n_metrics
        node_level = "n8n_node_execution_duration_seconds_bucket" in r.available_n8n_metrics
        print(f"  ✅ Dados de execução disponíveis : {len(r.workflows)} workflows, {len(r.instances)} instâncias")
        if metric_ok:
            print("  ✅ Histograma de duração de workflow presente (análise de p95 viável)")
        else:
            print("  ⚠️  Histograma de duração de workflow AUSENTE")
        if node_level:
            print("  ✅ Histograma node-level presente (análise detalhada por nó viável)")
        else:
            print("  ⚠️  Métrica node-level (n8n_node_execution_duration_seconds) AUSENTE")
            print("       → ANA-001 adapta análise para nível de workflow")
    else:
        print("  ❌ Nenhum dado de workflow no período consultado")
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verifica disponibilidade de métricas N8N para ANA-001 (ambos backends)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--prometheus-url",
        default=DEFAULT_PROMETHEUS_URL,
        help=f"URL pública do Prometheus (padrão: {DEFAULT_PROMETHEUS_URL})",
    )
    parser.add_argument(
        "--victoria-metrics-url",
        default=DEFAULT_VM_URL,
        metavar="URL",
        help=(
            "URL do VictoriaMetrics — somente interno ou via SSH tunnel. "
            "Ex: http://localhost:8428. "
            "Se não informado, apenas Prometheus é verificado."
        ),
    )
    parser.add_argument(
        "--start",
        default=DEFAULT_START,
        help=f"Início do período de análise ISO-8601 (padrão: {DEFAULT_START})",
    )
    parser.add_argument(
        "--end",
        default=datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        help="Fim do período de análise ISO-8601 (padrão: agora)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    now_str = datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    print(f"\n{'═' * 70}")
    print("  ANA-001 — Verificação de Métricas N8N (stack observabilidade)")
    print(f"{'═' * 70}")
    print(f"  Período  : {args.start}  →  {args.end}")
    print(f"  Executado: {now_str}")
    print()
    print("  Arquitetura do stack:")
    print(f"    Prometheus      — público HTTPS, {PROMETHEUS_RETENTION_DAYS}d retenção")
    print(f"    VictoriaMetrics — interno apenas, {VM_RETENTION_MONTHS} meses retenção (requer SSH tunnel)")

    any_reachable = False

    # Always check Prometheus
    prom = run_backend_check(
        url=args.prometheus_url.rstrip("/"),
        label=f"Prometheus (público, {PROMETHEUS_RETENTION_DAYS}d)",
        role="short-term",
        start=args.start,
        end=args.end,
    )
    print_backend_report(prom, args.start, args.end)
    if prom.reachable:
        any_reachable = True

    # Check VictoriaMetrics only if URL provided
    vm_url = (args.victoria_metrics_url or "").rstrip("/")
    if vm_url:
        vm = run_backend_check(
            url=vm_url,
            label=f"VictoriaMetrics (interno, {VM_RETENTION_MONTHS} meses)",
            role="long-term",
            start=args.start,
            end=args.end,
        )
        print_backend_report(vm, args.start, args.end)
        if vm.reachable:
            any_reachable = True
    else:
        print(f"\n{'─' * 70}")
        print(f"  VictoriaMetrics (interno, {VM_RETENTION_MONTHS} meses)  [long-term]")
        print("  Status: ⏭ Não verificado (--victoria-metrics-url não informado)")
        print("  Dica  : configure SSH tunnel e passe --victoria-metrics-url http://localhost:8428")

    # Final summary
    print(f"\n{'═' * 70}")
    print("  RESULTADO FINAL ANA-001")
    print(f"{'═' * 70}")
    if any_reachable:
        print("  ✅ Ao menos um backend acessível — análise ANA-001 pode prosseguir")
        if not vm_url:
            print(f"  ⚠️  VictoriaMetrics não verificado: dados limitados a {PROMETHEUS_RETENTION_DAYS} dias (Prometheus)")
            print("       Para dados históricos completos (12 meses), use SSH tunnel:")
            print("         fwknop --rc-file ~/.fwknoprc -n wfdb01 && sleep 3 &&")
            print("         ssh -p 5010 -N -L 8428:victoriametrics:8428 archaris@wfdb01.vya.digital")
            print("         (ou: source .secrets/wfdb01_connection.sh && wfdb01_tunnel_vm)")
            print("         python scripts/check_prometheus_n8n_metrics.py --victoria-metrics-url http://localhost:8428")
    else:
        print("  ❌ Nenhum backend acessível — análise ANA-001 não pode prosseguir")
    print()

    sys.exit(0 if any_reachable else 1)


if __name__ == "__main__":
    main()
