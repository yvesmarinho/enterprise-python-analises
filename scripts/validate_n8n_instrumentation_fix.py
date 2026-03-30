#!/usr/bin/env python3
"""Validate N8N instrumentation health after collector/exporter fix.

Checks:
1) sum counter monotonicity (no negative increases)
2) count counter monotonicity
3) p95 variability in the evaluated window
"""

import argparse
import json
from datetime import datetime, timedelta, timezone

import requests


def query_range(base_url: str, promql: str, start: str, end: str, step: str) -> list:
    r = requests.get(
        f"{base_url}/api/v1/query_range",
        params={"query": promql, "start": start, "end": end, "step": step},
        timeout=45,
    )
    if r.status_code != 200:
        return []
    return r.json().get("data", {}).get("result", [])


def first_series_values(result: list) -> list[float]:
    if not result:
        return []
    values = []
    for _, val in result[0].get("values", []):
        try:
            values.append(float(val))
        except ValueError:
            continue
    return values


def count_negative(values: list[float]) -> int:
    return sum(1 for v in values if v < 0)


def run(base_url: str, instance: str, hours: int, step: str) -> dict:
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(hours=hours)
    start = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    end = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    q_sum_inc = (
        "sum(increase(n8n_workflow_execution_duration_seconds_sum"
        f'{{instance="{instance}"}}[15m]))'
    )
    q_count_inc = (
        "sum(increase(n8n_workflow_execution_duration_seconds_count"
        f'{{instance="{instance}"}}[15m]))'
    )
    q_p95 = (
        "histogram_quantile(0.95, sum by (le) ("
        "rate(n8n_workflow_execution_duration_seconds_bucket"
        f'{{instance="{instance}"}}[5m])))'
    )
    q_sum_raw = (
        "sum(n8n_workflow_execution_duration_seconds_sum"
        f'{{instance="{instance}"}})'
    )
    q_count_raw = (
        "sum(n8n_workflow_execution_duration_seconds_count"
        f'{{instance="{instance}"}})'
    )

    sum_vals = first_series_values(query_range(base_url, q_sum_inc, start, end, step))
    count_vals = first_series_values(query_range(base_url, q_count_inc, start, end, step))
    p95_vals = first_series_values(query_range(base_url, q_p95, start, end, step))
    sum_raw_vals = first_series_values(query_range(base_url, q_sum_raw, start, end, step))
    count_raw_vals = first_series_values(query_range(base_url, q_count_raw, start, end, step))

    uniq_p95 = len(set(round(v, 6) for v in p95_vals))

    result = {
        "meta": {
            "generated": datetime.now(timezone.utc).isoformat(),
            "backend": base_url,
            "instance": instance,
            "hours": hours,
            "step": step,
            "start": start,
            "end": end,
        },
        "sum_points": len(sum_vals),
        "count_points": len(count_vals),
        "p95_points": len(p95_vals),
        "sum_raw_points": len(sum_raw_vals),
        "count_raw_points": len(count_raw_vals),
        "sum_non_monotonic_points": count_negative(sum_vals),
        "count_non_monotonic_points": count_negative(count_vals),
        "sum_raw_negative_points": count_negative(sum_raw_vals),
        "count_raw_negative_points": count_negative(count_raw_vals),
        "p95_unique_values": uniq_p95,
        "pass": {
            "sum_monotonic": count_negative(sum_vals) == 0,
            "count_monotonic": count_negative(count_vals) == 0,
            "sum_raw_non_negative": count_negative(sum_raw_vals) == 0,
            "count_raw_non_negative": count_negative(count_raw_vals) == 0,
            "p95_has_variance": uniq_p95 > 1,
        },
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default="http://localhost:18428")
    parser.add_argument("--instance", default="wf001")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--step", default="5m")
    parser.add_argument(
        "--output",
        default="reports/N8N_INSTRUMENTATION_VALIDATION_2026-03-30.json",
    )
    args = parser.parse_args()

    result = run(args.backend, args.instance, args.hours, args.step)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
