#!/usr/bin/env python3
"""
Análise rápida de cobertura de dados para instância wf001.
Período: 23-30 de março de 2026
Versão otimizada com bulk queries.
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict, List

import requests

PROMETHEUS_URL = "https://prometheus.vya.digital"
INSTANCE_FILTER = "wf001"
START_DATE = "2026-03-23T00:00:00Z"
END_DATE = "2026-03-30T23:59:59Z"

CRITICAL_METRICS = [
    # N8N
    "n8n_workflow_execution_duration_seconds_bucket",
    "n8n_workflow_execution_duration_seconds_count",
    "n8n_workflow_execution_duration_seconds_sum",
    "n8n_workflow_executions_total",
    "n8n_node_executions_total",
    "n8n_api_request_duration_seconds_bucket",
    "n8n_api_request_errors_total",
    # Container
    "container_cpu_usage_seconds_total",
    "container_memory_usage_bytes",
    "container_memory_max_usage_bytes",
    "container_network_receive_bytes_total",
    "container_network_transmit_bytes_total",
    "container_fs_usage_bytes",
    # Node/Host
    "node_cpu_seconds_total",
    "node_memory_MemAvailable_bytes",
    "node_memory_MemTotal_bytes",
    "node_disk_io_reads_completed_total",
    "node_disk_io_writes_completed_total",
    "node_disk_io_time_seconds_total",
    "node_network_receive_bytes_total",
    "node_load1",
    "process_cpu_seconds_total",
    "process_resident_memory_bytes",
]

def query_prometheus(query: str, start: str = None, end: str = None) -> dict:
    """Execute PromQL instant or range query."""
    try:
        if start and end:
            # Range query
            response = requests.get(
                f"{PROMETHEUS_URL}/api/v1/query_range",
                params={
                    "query": query,
                    "start": start,
                    "end": end,
                    "step": "1h"
                },
                timeout=30,
                verify=True
            )
        else:
            # Instant query
            response = requests.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": query},
                timeout=30,
                verify=True
            )

        if response.status_code == 200:
            data = response.json().get("data", {}).get("result", [])
            return {"status": "ok", "data": data, "count": len(data)}
        else:
            return {"status": "error", "code": response.status_code, "count": 0}
    except Exception as e:
        return {"status": "error", "message": str(e), "count": 0}

def main():
    print("\n" + "="*90)
    print("WF001 DATA COVERAGE VALIDATION — 23-30 March 2026")
    print("="*90)
    print(f"Instance Filter: {INSTANCE_FILTER}")
    print(f"Analysis Time: {datetime.utcnow().isoformat()}Z")
    print("="*90 + "\n")

    results = {
        "n8n": [],
        "container": [],
        "host": [],
        "process": []
    }

    # Categorize metrics
    for metric in CRITICAL_METRICS:
        query = f'count({metric}{{instance="{INSTANCE_FILTER}"}}) > 0'
        result = query_prometheus(query, START_DATE, END_DATE)

        if result["status"] == "ok" and result["count"] > 0:
            status = "✅"
            result_data = result
        else:
            status = "❌"
            result_data = result

        # Categorize
        if "n8n_" in metric:
            category = "n8n"
        elif "container_" in metric:
            category = "container"
        elif "process_" in metric:
            category = "process"
        else:
            category = "host"

        available = result["status"] == "ok" and result["count"] > 0
        results[category].append({
            "metric": metric,
            "available": available,
            "status": status
        })

        print(f"{status} {metric:50} | wf001")

    # Summary
    print("\n" + "="*90)
    print("COVERAGE SUMMARY")
    print("="*90)

    for category, metrics in results.items():
        available = sum(1 for m in metrics if m["available"])
        total = len(metrics)
        pct = (available / total * 100) if total > 0 else 0
        print(f"{category:20} | {available:2}/{total:2} ({pct:5.1f}%)")

    total_available = sum(sum(1 for m in metrics if m["available"]) for metrics in results.values())
    total_metrics = sum(len(metrics) for metrics in results.values())
    overall_pct = (total_available / total_metrics * 100) if total_metrics > 0 else 0

    print("-" * 90)
    print(f"{'TOTAL':20} | {total_available:2}/{total_metrics:2} ({overall_pct:5.1f}%)")
    print("="*90 + "\n")

    # Assessment
    print("📋 READINESS ASSESSMENT FOR WF001 LATENCY ANALYSIS:")
    print("-" * 90)

    n8n_ready = sum(1 for m in results["n8n"] if m["available"]) / len(results["n8n"]) >= 0.7 if results["n8n"] else False
    container_ready = sum(1 for m in results["container"] if m["available"]) / len(results["container"]) >= 0.7 if results["container"] else False
    host_ready = sum(1 for m in results["host"] if m["available"]) / len(results["host"]) >= 0.7 if results["host"] else False
    process_ready = sum(1 for m in results["process"] if m["available"]) / len(results["process"]) >= 0.7 if results["process"] else False

    print(f"✅ N8N Application Metrics:     {'READY' if n8n_ready else 'LIMITED'}")
    print(f"✅ Container Metrics:          {'READY' if container_ready else 'LIMITED'}")
    print(f"✅ Host/Node Metrics:          {'READY' if host_ready else 'LIMITED'}")
    print(f"✅ Process Metrics:            {'READY' if process_ready else 'LIMITED'}")

    if n8n_ready and (container_ready or host_ready):
        print("\n✅ SUFFICIENT DATA AVAILABLE FOR COMPREHENSIVE LATENCY ANALYSIS")
        print("   → Can correlate N8N latency with infrastructure metrics")
    else:
        print("\n⚠️  LIMITED DATA - Analysis may be constrained to application layer")

    print("="*90 + "\n")

if __name__ == "__main__":
    main()
