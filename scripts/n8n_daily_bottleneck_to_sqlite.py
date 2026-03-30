#!/usr/bin/env python3
"""Persist N8N daily bottleneck analysis into SQLite.

Focuses on analysis data for latency bottlenecks (not alerting):
- Daily workflow execution volume, average duration and p95 duration.
- Daily instance-level API load/error and workflow latency pressure.
- Daily host-level CPU/memory/load/network context.
- Daily bottleneck classification per N8N instance.

Example:
  uv run python scripts/n8n_daily_bottleneck_to_sqlite.py \
    --start-date 2026-03-19 --end-date 2026-03-25 \
    --sqlite-path data/n8n_bottleneck_daily.sqlite
"""

from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import math
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import httpx

UTC = dt.timezone.utc

DEFAULT_PROM_URL = "https://prometheus.vya.digital"
DEFAULT_DB_PATH = "data/n8n_bottleneck_daily.sqlite"
COLLECTOR_INSTANCE_ALIASES = {
    "0.0.0.0:5000": "prod-collector-api",
}


@dataclass(frozen=True)
class WorkflowKey:
    day: str
    instance: str
    workflow_id: str
    workflow_name: str


@dataclass(frozen=True)
class InstanceKey:
    day: str
    instance: str


def parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def to_utc_start(value: dt.date) -> dt.datetime:
    return dt.datetime(value.year, value.month, value.day, 0, 0, 0, tzinfo=UTC)


def to_utc_end(value: dt.date) -> dt.datetime:
    return dt.datetime(value.year, value.month, value.day, 23, 59, 59, tzinfo=UTC)


def ts_to_day(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts, tz=UTC).date().isoformat()


def normalize_host_token(value: str) -> str:
    """Normalize instance/host labels to improve cross-metric joins.

    Examples:
    - "wf001.vya.digital:9100" -> "wf001"
    - "wf001" -> "wf001"
    - "172.17.0.1:9100" -> "172.17.0.1"
    """
    if not value:
        return "unknown"

    token = value.split(":", 1)[0].strip().lower()
    if not token:
        return "unknown"

    try:
        ipaddress.ip_address(token)
        return token
    except ValueError:
        pass

    return token.split(".", 1)[0]


def host_from_instance(instance: str) -> str:
    return normalize_host_token(instance)


def instance_source_name(instance: str) -> str:
    """Return a human-readable source name for the metrics instance label."""
    return COLLECTOR_INSTANCE_ALIASES.get(instance, instance)


def parse_prom_value(raw: Any) -> float | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return value


class PromClient:
    def __init__(self, base_url: str, timeout_seconds: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        timeout = httpx.Timeout(timeout_seconds)
        self.client = httpx.Client(timeout=timeout, follow_redirects=True)

    def close(self) -> None:
        self.client.close()

    def query_range(self, promql: str, start: dt.datetime, end: dt.datetime, step: str = "1d") -> list[dict[str, Any]]:
        response = self.client.get(
            f"{self.base_url}/api/v1/query_range",
            params={
                "query": promql,
                "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "step": step,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success":
            raise RuntimeError(f"Prometheus query_range failed: {payload}")
        return payload.get("data", {}).get("result", [])


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS daily_workflow_metrics (
            day TEXT NOT NULL,
            instance TEXT NOT NULL,
            host TEXT NOT NULL,
            workflow_id TEXT NOT NULL,
            workflow_name TEXT NOT NULL,
            executions REAL,
            duration_sum_seconds REAL,
            avg_duration_seconds REAL,
            p95_duration_seconds REAL,
            PRIMARY KEY (day, instance, workflow_id)
        );

        CREATE TABLE IF NOT EXISTS daily_instance_metrics (
            day TEXT NOT NULL,
            instance TEXT NOT NULL,
            host TEXT NOT NULL,
            workflow_executions REAL,
            workflow_p95_max_seconds REAL,
            workflow_avg_weighted_seconds REAL,
            api_requests REAL,
            api_errors REAL,
            api_error_rate_pct REAL,
            PRIMARY KEY (day, instance)
        );

        CREATE TABLE IF NOT EXISTS daily_host_metrics (
            day TEXT NOT NULL,
            host TEXT NOT NULL,
            node_instance TEXT,
            cpu_utilization_pct REAL,
            memory_utilization_pct REAL,
            load1_avg REAL,
            network_rx_bytes REAL,
            network_tx_bytes REAL,
            PRIMARY KEY (day, host)
        );

        CREATE TABLE IF NOT EXISTS daily_bottleneck_analysis (
            day TEXT NOT NULL,
            instance TEXT NOT NULL,
            host TEXT NOT NULL,
            dominant_bottleneck TEXT NOT NULL,
            top_workflow_id TEXT,
            top_workflow_name TEXT,
            top_workflow_p95_seconds REAL,
            score_app_latency REAL,
            score_api_errors REAL,
            score_cpu REAL,
            score_memory REAL,
            notes TEXT,
            PRIMARY KEY (day, instance)
        );
        """
    )


def delete_range(conn: sqlite3.Connection, start_day: str, end_day: str) -> None:
    for table in (
        "daily_workflow_metrics",
        "daily_instance_metrics",
        "daily_host_metrics",
        "daily_bottleneck_analysis",
    ):
        conn.execute(
            f"DELETE FROM {table} WHERE day >= ? AND day <= ?",
            (start_day, end_day),
        )


def collect_workflow_metrics(client: PromClient, start: dt.datetime, end: dt.datetime) -> dict[WorkflowKey, dict[str, float | None]]:
    executions_q = (
        "sum by (instance, workflow_id, workflow_name) "
        "(clamp_min(increase(n8n_workflow_execution_duration_seconds_count[1d]), 0))"
    )
    duration_sum_q = (
        "sum by (instance, workflow_id, workflow_name) "
        "(clamp_min(increase(n8n_workflow_execution_duration_seconds_sum[1d]), 0))"
    )
    p95_q = (
        "histogram_quantile(0.95, "
        "sum by (le, instance, workflow_id, workflow_name) "
        "(clamp_min(increase(n8n_workflow_execution_duration_seconds_bucket[1d]), 0)))"
    )

    by_key: dict[WorkflowKey, dict[str, float | None]] = defaultdict(dict)

    for promql, field_name in (
        (executions_q, "executions"),
        (duration_sum_q, "duration_sum_seconds"),
        (p95_q, "p95_duration_seconds"),
    ):
        results = client.query_range(promql, start, end, step="1d")
        for series in results:
            metric = series.get("metric", {})
            instance = metric.get("instance", "unknown")
            workflow_id = metric.get("workflow_id", "unknown")
            workflow_name = metric.get("workflow_name", "unknown")
            for ts, raw in series.get("values", []):
                value = parse_prom_value(raw)
                if value is None:
                    continue
                day = ts_to_day(float(ts))
                key = WorkflowKey(
                    day=day,
                    instance=instance,
                    workflow_id=workflow_id,
                    workflow_name=workflow_name,
                )
                by_key[key][field_name] = value

    for key, row in by_key.items():
        executions = row.get("executions")
        duration_sum = row.get("duration_sum_seconds")
        if executions and duration_sum is not None and executions > 0 and duration_sum >= 0:
            row["avg_duration_seconds"] = duration_sum / executions
        else:
            row["avg_duration_seconds"] = None

    return by_key


def collect_instance_api_metrics(client: PromClient, start: dt.datetime, end: dt.datetime) -> dict[InstanceKey, dict[str, float | None]]:
    request_q = "sum by (instance) (clamp_min(increase(n8n_api_request_total[1d]), 0))"
    error_q = "sum by (instance) (clamp_min(increase(n8n_api_request_errors_total[1d]), 0))"

    by_key: dict[InstanceKey, dict[str, float | None]] = defaultdict(dict)

    for promql, field_name in ((request_q, "api_requests"), (error_q, "api_errors")):
        results = client.query_range(promql, start, end, step="1d")
        for series in results:
            instance = series.get("metric", {}).get("instance", "unknown")
            for ts, raw in series.get("values", []):
                value = parse_prom_value(raw)
                if value is None:
                    continue
                key = InstanceKey(day=ts_to_day(float(ts)), instance=instance)
                by_key[key][field_name] = value

    for key, row in by_key.items():
        req = row.get("api_requests") or 0.0
        err = row.get("api_errors") or 0.0
        row["api_error_rate_pct"] = (err / req * 100.0) if req > 0 else 0.0

    return by_key


def collect_host_metrics(client: PromClient, start: dt.datetime, end: dt.datetime) -> dict[tuple[str, str], dict[str, float | str | None]]:
    cpu_q = (
        "avg_over_time((100 - (avg by (instance) "
        "(rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100))[1d:5m])"
    )
    mem_q = (
        "avg_over_time(((1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))"
        " * 100)[1d:5m])"
    )
    load_q = "avg_over_time(node_load1[1d])"
    rx_q = (
        "sum by (instance) "
        "(clamp_min(increase(node_network_receive_bytes_total{device!~\"lo|veth.*|docker.*\"}[1d]), 0))"
    )
    tx_q = (
        "sum by (instance) "
        "(clamp_min(increase(node_network_transmit_bytes_total{device!~\"lo|veth.*|docker.*\"}[1d]), 0))"
    )

    by_key: dict[tuple[str, str], dict[str, float | str | None]] = defaultdict(dict)

    for promql, field_name in (
        (cpu_q, "cpu_utilization_pct"),
        (mem_q, "memory_utilization_pct"),
        (load_q, "load1_avg"),
        (rx_q, "network_rx_bytes"),
        (tx_q, "network_tx_bytes"),
    ):
        results = client.query_range(promql, start, end, step="1d")
        for series in results:
            node_instance = series.get("metric", {}).get("instance", "unknown")
            host = normalize_host_token(node_instance)
            for ts, raw in series.get("values", []):
                value = parse_prom_value(raw)
                if value is None:
                    continue
                day = ts_to_day(float(ts))
                key = (day, host)
                by_key[key]["node_instance"] = node_instance
                by_key[key][field_name] = value

    return by_key


def write_workflow_rows(conn: sqlite3.Connection, rows: dict[WorkflowKey, dict[str, float | None]]) -> None:
    sql = (
        "INSERT OR REPLACE INTO daily_workflow_metrics "
        "(day, instance, host, workflow_id, workflow_name, executions, duration_sum_seconds, avg_duration_seconds, p95_duration_seconds) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    payload = []
    for key, row in rows.items():
        payload.append(
            (
                key.day,
                key.instance,
                host_from_instance(key.instance),
                key.workflow_id,
                key.workflow_name,
                row.get("executions"),
                row.get("duration_sum_seconds"),
                row.get("avg_duration_seconds"),
                row.get("p95_duration_seconds"),
            )
        )
    conn.executemany(sql, payload)


def build_instance_rows(
    workflow_rows: dict[WorkflowKey, dict[str, float | None]],
    api_rows: dict[InstanceKey, dict[str, float | None]],
) -> tuple[list[tuple[Any, ...]], dict[InstanceKey, dict[str, Any]]]:
    sql_payload: list[tuple[Any, ...]] = []
    detail: dict[InstanceKey, dict[str, Any]] = {}

    grouped: dict[InstanceKey, list[tuple[WorkflowKey, dict[str, float | None]]]] = defaultdict(list)
    for key, values in workflow_rows.items():
        grouped[InstanceKey(day=key.day, instance=key.instance)].append((key, values))

    all_keys = set(grouped.keys()) | set(api_rows.keys())

    for ikey in sorted(all_keys, key=lambda x: (x.day, x.instance)):
        workflows = grouped.get(ikey, [])
        wf_exec = 0.0
        weighted_avg_numerator = 0.0
        p95_max = 0.0
        top_wf_id = None
        top_wf_name = None

        for wf_key, wf_values in workflows:
            executions = wf_values.get("executions") or 0.0
            avg = wf_values.get("avg_duration_seconds") or 0.0
            p95 = wf_values.get("p95_duration_seconds") or 0.0
            wf_exec += executions
            weighted_avg_numerator += executions * avg
            if p95 > p95_max:
                p95_max = p95
                top_wf_id = wf_key.workflow_id
                top_wf_name = wf_key.workflow_name

        weighted_avg = (weighted_avg_numerator / wf_exec) if wf_exec > 0 else None

        api = api_rows.get(ikey, {})
        api_requests = api.get("api_requests")
        api_errors = api.get("api_errors")
        api_error_rate = api.get("api_error_rate_pct", 0.0)

        sql_payload.append(
            (
                ikey.day,
                ikey.instance,
                host_from_instance(ikey.instance),
                wf_exec,
                p95_max if p95_max > 0 else None,
                weighted_avg,
                api_requests,
                api_errors,
                api_error_rate,
            )
        )

        detail[ikey] = {
            "top_workflow_id": top_wf_id,
            "top_workflow_name": top_wf_name,
            "top_workflow_p95": p95_max if p95_max > 0 else None,
            "workflow_executions": wf_exec,
            "api_error_rate_pct": api_error_rate,
        }

    return sql_payload, detail


def write_instance_rows(conn: sqlite3.Connection, payload: list[tuple[Any, ...]]) -> None:
    sql = (
        "INSERT OR REPLACE INTO daily_instance_metrics "
        "(day, instance, host, workflow_executions, workflow_p95_max_seconds, workflow_avg_weighted_seconds, api_requests, api_errors, api_error_rate_pct) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    conn.executemany(sql, payload)


def write_host_rows(conn: sqlite3.Connection, rows: dict[tuple[str, str], dict[str, float | str | None]]) -> None:
    sql = (
        "INSERT OR REPLACE INTO daily_host_metrics "
        "(day, host, node_instance, cpu_utilization_pct, memory_utilization_pct, load1_avg, network_rx_bytes, network_tx_bytes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    )
    payload = []
    for (day, host), values in rows.items():
        payload.append(
            (
                day,
                host,
                values.get("node_instance"),
                values.get("cpu_utilization_pct"),
                values.get("memory_utilization_pct"),
                values.get("load1_avg"),
                values.get("network_rx_bytes"),
                values.get("network_tx_bytes"),
            )
        )
    conn.executemany(sql, payload)


def classify_bottleneck(
    p95_seconds: float | None,
    api_error_rate_pct: float | None,
    cpu_pct: float | None,
    mem_pct: float | None,
) -> tuple[str, float, float, float, float]:
    score_app_latency = min((p95_seconds or 0.0) / 1.0, 3.0)
    score_api_errors = min((api_error_rate_pct or 0.0) / 5.0, 3.0)
    score_cpu = min((cpu_pct or 0.0) / 80.0, 3.0)
    score_memory = min((mem_pct or 0.0) / 85.0, 3.0)

    scores = {
        "APP_LATENCY": score_app_latency,
        "API_ERRORS": score_api_errors,
        "CPU_PRESSURE": score_cpu,
        "MEMORY_PRESSURE": score_memory,
    }
    top_label, top_value = max(scores.items(), key=lambda kv: kv[1])

    if top_value <= 0.05:
        return "NO_SIGNAL", score_app_latency, score_api_errors, score_cpu, score_memory

    sorted_scores = sorted(scores.values(), reverse=True)
    if len(sorted_scores) > 1 and abs(sorted_scores[0] - sorted_scores[1]) < 0.10:
        return "MIXED", score_app_latency, score_api_errors, score_cpu, score_memory

    return top_label, score_app_latency, score_api_errors, score_cpu, score_memory


def build_host_aliases(instance_payload: list[tuple[Any, ...]]) -> dict[tuple[str, str], str]:
    """Build day-scoped host aliases for instance names that are not host-like.

    Current practical case: instance `0.0.0.0:5000` (prod-collector-api)
    should inherit host context from a co-existing canonical N8N host
    (for example `wf001`) on the same day.
    """
    per_day: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for day, _instance, host, wf_exec, *_rest in instance_payload:
        if host in {"unknown", "0.0.0.0"}:
            continue
        try:
            ipaddress.ip_address(host)
            continue
        except ValueError:
            pass
        per_day[day].append((host, float(wf_exec or 0.0)))

    aliases: dict[tuple[str, str], str] = {}
    for day, hosts in per_day.items():
        if not hosts:
            continue
        canonical_host = sorted(hosts, key=lambda item: item[1], reverse=True)[0][0]
        aliases[(day, "0.0.0.0")] = canonical_host

    return aliases


def write_bottleneck_rows(
    conn: sqlite3.Connection,
    instance_payload: list[tuple[Any, ...]],
    host_rows: dict[tuple[str, str], dict[str, float | str | None]],
    instance_detail: dict[InstanceKey, dict[str, Any]],
) -> int:
    sql = (
        "INSERT OR REPLACE INTO daily_bottleneck_analysis "
        "(day, instance, host, dominant_bottleneck, top_workflow_id, top_workflow_name, top_workflow_p95_seconds, "
        "score_app_latency, score_api_errors, score_cpu, score_memory, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )

    aliases = build_host_aliases(instance_payload)
    rows = []
    for row in instance_payload:
        day, instance, host, wf_exec, wf_p95, _wf_avg, _api_req, _api_err, api_err_rate = row
        host_lookup = aliases.get((day, host), host)
        host_ctx = host_rows.get((day, host_lookup), {})
        cpu = host_ctx.get("cpu_utilization_pct")
        mem = host_ctx.get("memory_utilization_pct")

        dominant, score_app, score_err, score_cpu, score_mem = classify_bottleneck(
            p95_seconds=wf_p95,
            api_error_rate_pct=api_err_rate,
            cpu_pct=cpu if isinstance(cpu, float) else None,
            mem_pct=mem if isinstance(mem, float) else None,
        )

        ikey = InstanceKey(day=day, instance=instance)
        detail = instance_detail.get(ikey, {})
        top_wf_id = detail.get("top_workflow_id")
        top_wf_name = detail.get("top_workflow_name")
        top_wf_p95 = detail.get("top_workflow_p95")

        notes = (
            f"source={instance_source_name(instance)}; "
            f"raw_instance={instance}; "
            f"wf_exec={wf_exec or 0:.0f}; "
            f"cpu={cpu if isinstance(cpu, float) else 'n/a'}; "
            f"mem={mem if isinstance(mem, float) else 'n/a'}; "
            f"api_err_rate={api_err_rate or 0:.2f}%"
        )

        rows.append(
            (
                day,
                instance,
                host_lookup,
                dominant,
                top_wf_id,
                top_wf_name,
                top_wf_p95,
                score_app,
                score_err,
                score_cpu,
                score_mem,
                notes,
            )
        )

    conn.executemany(sql, rows)
    return len(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze N8N latency bottlenecks and persist daily datasets in SQLite",
    )
    parser.add_argument("--prometheus-url", default=DEFAULT_PROM_URL, help="Prometheus base URL")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--sqlite-path", default=DEFAULT_DB_PATH, help="SQLite output file path")
    parser.add_argument(
        "--overwrite-range",
        action="store_true",
        help="Delete existing rows in selected date range before insert",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    start_date = parse_date(args.start_date)
    end_date = parse_date(args.end_date)
    if end_date < start_date:
        raise ValueError("end-date must be greater than or equal to start-date")

    start_dt = to_utc_start(start_date)
    end_dt = to_utc_end(end_date)

    client = PromClient(args.prometheus_url)
    conn = sqlite3.connect(args.sqlite_path)

    try:
        create_schema(conn)
        if args.overwrite_range:
            delete_range(conn, start_date.isoformat(), end_date.isoformat())

        workflow_rows = collect_workflow_metrics(client, start_dt, end_dt)
        api_rows = collect_instance_api_metrics(client, start_dt, end_dt)
        host_rows = collect_host_metrics(client, start_dt, end_dt)

        write_workflow_rows(conn, workflow_rows)
        instance_payload, instance_detail = build_instance_rows(workflow_rows, api_rows)
        write_instance_rows(conn, instance_payload)
        write_host_rows(conn, host_rows)
        bottleneck_count = write_bottleneck_rows(conn, instance_payload, host_rows, instance_detail)

        conn.commit()

        print("Daily bottleneck analysis persisted in SQLite")
        print(f"  DB path           : {args.sqlite_path}")
        print(f"  Date range        : {start_date.isoformat()} -> {end_date.isoformat()}")
        print(f"  Workflow rows     : {len(workflow_rows)}")
        print(f"  Instance rows     : {len(instance_payload)}")
        print(f"  Host rows         : {len(host_rows)}")
        print(f"  Bottleneck rows   : {bottleneck_count}")

    finally:
        client.close()
        conn.close()


if __name__ == "__main__":
    main()
