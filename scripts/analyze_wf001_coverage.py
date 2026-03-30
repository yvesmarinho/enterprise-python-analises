#!/usr/bin/env python3
"""
Análise de cobertura e validação de dados para instância wf001.
Período: 23-30 de março de 2026
Objetivo: Validar suficiência de dados para análise de lentidão com variables de hardware/software.
"""

import json
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List

import requests

# Configuração
PROMETHEUS_URL = "https://prometheus.vya.digital"
INSTANCE_FILTER = "wf001"
START_DATE = "2026-03-23T00:00:00Z"
END_DATE = "2026-03-30T23:59:59Z"

# Métricas de interesse por categoria
METRICS_CATEGORIES = {
    "N8N Application": [
        "n8n_workflow_execution_duration_seconds_bucket",
        "n8n_workflow_execution_duration_seconds_count",
        "n8n_workflow_execution_duration_seconds_sum",
        "n8n_node_execution_duration_seconds_bucket",
        "n8n_node_execution_duration_seconds_count",
        "n8n_api_request_duration_seconds_bucket",
        "n8n_api_request_duration_seconds_count",
        "n8n_workflow_executions_total",
        "n8n_node_executions_total",
        "n8n_api_request_errors_total",
        "n8n_workflow_queue_size",
        "n8n_active_workflows",
    ],
    "Container/Docker": [
        "container_cpu_usage_seconds_total",
        "container_memory_usage_bytes",
        "container_memory_max_usage_bytes",
        "container_memory_working_set_bytes",
        "container_network_receive_bytes_total",
        "container_network_transmit_bytes_total",
        "container_network_receive_errors_total",
        "container_network_transmit_errors_total",
        "container_fs_usage_bytes",
        "container_fs_limit_bytes",
        "container_last_seen",
    ],
    "Host/Node": [
        "node_cpu_seconds_total",
        "node_memory_MemAvailable_bytes",
        "node_memory_MemTotal_bytes",
        "node_memory_MemFree_bytes",
        "node_memory_Buffers_bytes",
        "node_memory_Cached_bytes",
        "node_disk_io_reads_completed_total",
        "node_disk_io_writes_completed_total",
        "node_disk_io_time_seconds_total",
        "node_disk_read_time_seconds_total",
        "node_disk_write_time_seconds_total",
        "node_network_receive_bytes_total",
        "node_network_transmit_bytes_total",
        "node_network_receive_errs_total",
        "node_network_transmit_errs_total",
        "node_network_receive_drop_total",
        "node_network_transmit_drop_total",
        "node_load1",
        "node_load5",
        "node_load15",
        "node_context_switches_total",
        "node_processes_running",
        "node_processes_blocked",
    ],
    "Process": [
        "process_cpu_seconds_total",
        "process_resident_memory_bytes",
        "process_virtual_memory_bytes",
        "process_open_fds",
        "process_max_fds",
    ],
}

def query_prometheus(query: str) -> List[Dict[str, Any]]:
    """Execute PromQL query and return results."""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=30,
            verify=True
        )
        if response.status_code == 200:
            return response.json().get("data", {}).get("result", [])
        else:
            print(f"⚠️  Query failed: {query[:80]}... → HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error querying Prometheus: {e}")
        return []

def query_range_prometheus(query: str, start: str, end: str, step: str = "5m") -> List[Dict[str, Any]]:
    """Execute PromQL range query."""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query_range",
            params={
                "query": query,
                "start": start,
                "end": end,
                "step": step
            },
            timeout=30,
            verify=True
        )
        if response.status_code == 200:
            return response.json().get("data", {}).get("result", [])
        else:
            print(f"⚠️  Range query failed: {query[:60]}... → HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error in range query: {e}")
        return []

def check_metric_availability(metric_name: str) -> dict:
    """Check if a metric is available and has data for wf001."""
    # Query: check if metric exists with instance="wf001"
    query = f'{metric_name}{{instance="{INSTANCE_FILTER}"}}'

    results = query_prometheus(query)

    if results:
        # Have data - now check time range
        range_query = f'count({metric_name}{{instance="{INSTANCE_FILTER}"}}) > 0'
        range_results = query_range_prometheus(
            range_query,
            START_DATE,
            END_DATE,
            step="1h"
        )

        if range_results:
            data_points = len(range_results[0].get("values", [])) if range_results else 0
            return {
                "metric": metric_name,
                "available": True,
                "data_points": data_points,
                "coverage": f"{(data_points / ((30*24) if data_points > 0 else 1)) * 100:.1f}%"
            }

    return {
        "metric": metric_name,
        "available": False,
        "data_points": 0,
        "coverage": "0%"
    }

def main():
    print("\n" + "="*80)
    print("WF001 DATA COVERAGE ANALYSIS")
    print("="*80)
    print(f"Instance: {INSTANCE_FILTER}")
    print(f"Period: {START_DATE} → {END_DATE}")
    print(f"Analysis Date: {datetime.utcnow().isoformat()}Z")
    print("="*80 + "\n")

    all_results = {}

    for category, metrics in METRICS_CATEGORIES.items():
        print(f"\n📊 Category: {category}")
        print("-" * 80)

        category_results = []
        available_count = 0

        for metric in metrics:
            result = check_metric_availability(metric)
            category_results.append(result)

            if result["available"]:
                available_count += 1
                status = "✅"
                print(f"{status} {metric:55} | {result['data_points']:5} points | {result['coverage']:>6}")
            else:
                status = "⚠️ "
                print(f"{status} {metric:55} | NOT AVAILABLE")

        all_results[category] = {
            "total_metrics": len(metrics),
            "available": available_count,
            "coverage_pct": (available_count / len(metrics)) * 100 if metrics else 0,
            "metrics": category_results
        }

        print(f"\nCategory Coverage: {available_count}/{len(metrics)} ({all_results[category]['coverage_pct']:.1f}%)")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY BY CATEGORY")
    print("="*80)

    total_metrics = 0
    total_available = 0

    for category, data in all_results.items():
        total_metrics += data["total_metrics"]
        total_available += data["available"]
        pct = data["coverage_pct"]
        status = "✅" if pct >= 80 else "⚠️ " if pct >= 50 else "❌"
        print(f"{status} {category:30} | {data['available']:2}/{data['total_metrics']:2} ({pct:5.1f}%)")

    overall_pct = (total_available / total_metrics) * 100 if total_metrics > 0 else 0
    print("-" * 80)
    print(f"TOTAL COVERAGE: {total_available}/{total_metrics} ({overall_pct:.1f}%)")

    # Recommendations
    print("\n" + "="*80)
    print("ANALYSIS READINESS ASSESSMENT")
    print("="*80)

    n8n_pct = all_results.get("N8N Application", {}).get("coverage_pct", 0)
    container_pct = all_results.get("Container/Docker", {}).get("coverage_pct", 0)
    host_pct = all_results.get("Host/Node", {}).get("coverage_pct", 0)

    print(f"\nN8N Metrics Coverage:     {n8n_pct:5.1f}% → {'✅ READY' if n8n_pct >= 70 else '⚠️  LIMITED'}")
    print(f"Container Metrics:       {container_pct:5.1f}% → {'✅ READY' if container_pct >= 70 else '⚠️  LIMITED'}")
    print(f"Host/Node Metrics:       {host_pct:5.1f}% → {'✅ READY' if host_pct >= 70 else '⚠️  LIMITED'}")

    # Vitals check
    print("\n" + "="*80)
    print("CRITICAL METRICS FOR LATENCY ANALYSIS")
    print("="*80)

    critical_metrics = [
        ("n8n_workflow_execution_duration_seconds_bucket", "N8N Workflow Latency"),
        ("container_cpu_usage_seconds_total", "Container CPU"),
        ("container_memory_usage_bytes", "Container Memory"),
        ("node_load1", "Host CPU Load"),
        ("node_disk_io_time_seconds_total", "Disk I/O Wait"),
        ("node_network_receive_bytes_total", "Network I/O"),
        ("process_cpu_seconds_total", "N8N Process CPU"),
    ]

    for metric, label in critical_metrics:
        result = check_metric_availability(metric)
        status = "✅" if result["available"] else "❌"
        print(f"{status} {label:30} | {result['metric']}")

    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
