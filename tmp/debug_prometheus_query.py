"""
Debug: testa a PromQL do ANA-001 diretamente contra o Prometheus.

PROBLEMA IDENTIFICADO: TimeoutError ao consultar 10 dias × step 5m via HTTPS.
A query histogram_quantile é computacionalmente pesada no lado do servidor;
acessar de forma remota via HTTPS excede o timeout de 30s.

SOLUÇÃO: executar o script no próprio wfdb01 (acesso local ao Prometheus/VM).
  bash scripts/run_analysis_on_wfdb01.sh

Este script de debug testa ranges menores para identificar o limite viável:
  python tmp/debug_prometheus_query.py --step 1h       # range completo, step 1h
  python tmp/debug_prometheus_query.py --step 6h       # range completo, step 6h
  python tmp/debug_prometheus_query.py --start 2026-03-13 --end 2026-03-14 --step 5m
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

PROMETHEUS_URL = "https://prometheus.vya.digital"
QUERY = (
    "histogram_quantile(0.95, "
    "sum by (workflow_id, workflow_name, instance, le) ("
    "rate(n8n_workflow_execution_duration_seconds_bucket[{window}])"
    "))"
)

STEP_TO_WINDOW = {"5m": "10m", "15m": "30m", "30m": "1h", "1h": "2h", "6h": "12h", "1d": "2d"}


def fetch(url: str, timeout: int = 30) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310
            return json.loads(r.read().decode())
    except TimeoutError as exc:
        print(f"TimeoutError: {exc!r}", file=sys.stderr)
        print("→ O step é muito pequeno para o range. Tente --step 1h ou --step 6h.", file=sys.stderr)
        sys.exit(1)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print(f"HTTP {exc.code}: {body[:500]}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc!r}", file=sys.stderr)
        sys.exit(1)


def run(start: str, end: str, step: str, timeout: int) -> None:
    window = STEP_TO_WINDOW.get(step, f"{step}")
    query = QUERY.format(window=window)
    params = urllib.parse.urlencode({"query": query, "start": start, "end": end, "step": step})
    url = f"{PROMETHEUS_URL}/api/v1/query_range?{params}"

    # Estimate data points
    try:
        s_ts = datetime.fromisoformat(start.replace("Z", "+00:00")).timestamp()
        e_ts = datetime.fromisoformat(end.replace("Z", "+00:00")).timestamp()
        step_seconds = {"5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "6h": 21600, "1d": 86400}.get(step, 300)
        points = int((e_ts - s_ts) / step_seconds)
    except Exception:
        points = -1

    print(f"URL  : {url[:160]}...")
    print(f"Start: {start}   End: {end}   Step: {step}   Window: {window}")
    print(f"Estimated points per series: {points}   Timeout: {timeout}s")
    print("Querying...")

    data = fetch(url, timeout=timeout)
    status = data.get("status")
    print(f"Status: {status}")
    if status != "success":
        print(f"Error: {data.get('error')}", file=sys.stderr)
        sys.exit(1)

    results = data.get("data", {}).get("result", [])
    print(f"Series returned: {len(results)}")

    nan_count = 0
    valid_count = 0
    violations = 0
    max_p95 = 0.0
    max_workflow = ""

    for series in results:
        metric = series.get("metric", {})
        values = series.get("values", [])
        for _, v in values:
            try:
                f = float(v)
            except ValueError:
                continue
            if math.isnan(f) or f <= 0:
                nan_count += 1
            else:
                valid_count += 1
                if f >= 1.0:
                    violations += 1
                if f > max_p95:
                    max_p95 = f
                    max_workflow = metric.get("workflow_name", "?")

    print(f"Points: valid={valid_count}  NaN/zero={nan_count}  violations(≥1s)={violations}")
    if max_p95 > 0:
        print(f"Highest p95: {max_p95:.3f}s  workflow={max_workflow}")

    print("\nTop 5 series with valid data:")
    shown = 0
    for series in results:
        metric = series.get("metric", {})
        values = series.get("values", [])
        valid_vals = []
        for _, v in values:
            try:
                f = float(v)
                if not math.isnan(f) and f > 0:
                    valid_vals.append(f)
            except ValueError:
                continue
        if valid_vals:
            print(f"  {metric.get('workflow_name', '?'):<40}  p95_max={max(valid_vals):.3f}s  pts={len(valid_vals)}")
            shown += 1
            if shown >= 5:
                break

    print("\nDIAGNÓSTICO:")
    if violations > 0:
        print(f"  ⚠️  {violations} pontos com p95 ≥ 1s detectados — ANA-001 deveria reportar violações.")
    elif valid_count > 0:
        print(f"  ✅ {valid_count} pontos válidos mas todos p95 < 1s — nenhuma violação real no período.")
    else:
        print("  ❌ Nenhum dado válido — verifique collector/scrape config no Prometheus.")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Debug PromQL ANA-001 histogram_quantile")
    p.add_argument("--start", default="2026-03-04T00:00:00Z")
    p.add_argument("--end", default="2026-03-14T00:00:00Z")
    p.add_argument("--step", default="1h", help="Tente 1h ou 6h para evitar timeout (padrão: 1h)")
    p.add_argument("--timeout", type=int, default=60, help="Timeout HTTP em segundos (padrão: 60)")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(args.start, args.end, args.step, args.timeout)



def fetch(url: str, timeout: int = 30) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print(f"HTTP {exc.code}: {body[:500]}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc!r}", file=sys.stderr)
        sys.exit(1)


def run(start: str, end: str, step: str) -> None:
    params = urllib.parse.urlencode({
        "query": QUERY,
        "start": start,
        "end": end,
        "step": step,
    })
    url = f"{PROMETHEUS_URL}/api/v1/query_range?{params}"
    print(f"URL: {url[:200]}...")
    print(f"Start: {start}   End: {end}   Step: {step}")

    data = fetch(url)
    status = data.get("status")
    print(f"Status: {status}")
    if status != "success":
        print(f"Error: {data.get('error')}", file=sys.stderr)
        sys.exit(1)

    results = data.get("data", {}).get("result", [])
    print(f"Series returned: {len(results)}")

    nan_count = 0
    valid_count = 0
    violations = 0

    for series in results:
        metric = series.get("metric", {})
        values = series.get("values", [])
        for _, v in values:
            try:
                f = float(v)
            except ValueError:
                continue
            if math.isnan(f) or f <= 0:
                nan_count += 1
            else:
                valid_count += 1
                if f >= 1.0:
                    violations += 1

    print(f"Data points — valid: {valid_count}  NaN/zero: {nan_count}  violations(≥1s): {violations}")

    # Show top 5 series with valid data
    print("\nSample series (first 5 with valid values):")
    shown = 0
    for series in results:
        metric = series.get("metric", {})
        values = series.get("values", [])
        valid_vals = [float(v) for _, v in values if not math.isnan(float(v)) and float(v) > 0]
        if valid_vals:
            print(f"  {metric.get('workflow_name', '?'):<40}  max={max(valid_vals):.3f}s  pts={len(valid_vals)}")
            shown += 1
            if shown >= 5:
                break


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Debug PromQL ANA-001 histogram_quantile")
    p.add_argument("--start", default="2026-03-04T00:00:00Z")
    p.add_argument("--end", default="2026-03-14T00:00:00Z")
    p.add_argument("--step", default="5m")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(args.start, args.end, args.step)
