#!/usr/bin/env python3
"""
N8N Bottleneck Analyzer
Analisa métricas do Victoria Metrics para identificar gargalos de performance
"""

import requests
import json
from typing import List, Dict, Tuple
from datetime import datetime

VICTORIA_METRICS_URL = "http://localhost:8428"

def query_victoria_metrics(query: str) -> List[Dict]:
    """Executa query PromQL no Victoria Metrics"""
    url = f"{VICTORIA_METRICS_URL}/api/v1/query"
    response = requests.get(url, params={"query": query})
    response.raise_for_status()
    return response.json()["data"]["result"]

def get_slowest_workflows(top_n: int = 10) -> List[Tuple[str, float, int]]:
    """Retorna os N workflows mais lentos com suas durações e volume"""
    # Obter durações
    durations = query_victoria_metrics("n8n_workflow_execution_duration_seconds")
    # Obter totais de execuções
    totals = query_victoria_metrics("n8n_workflow_executions_total")
    
    # Criar mapa de totais
    total_map = {}
    for result in totals:
        wf_name = result["metric"].get("workflow_name", "unknown")
        total = int(float(result["value"][1]))
        total_map[wf_name] = total
    
    # Combinar dados
    workflows = []
    for result in durations:
        wf_name = result["metric"].get("workflow_name", "unknown")
        duration = float(result["value"][1])
        total = total_map.get(wf_name, 0)
        workflows.append((wf_name, duration, total))
    
    # Ordenar por duração (descendente)
    workflows.sort(key=lambda x: x[1], reverse=True)
    return workflows[:top_n]

def get_most_executed_workflows(top_n: int = 10) -> List[Tuple[str, int, float]]:
    """Retorna os N workflows mais executados com total de tempo consumido"""
    # Obter totais
    totals = query_victoria_metrics("n8n_workflow_executions_total")
    # Obter durações
    durations = query_victoria_metrics("n8n_workflow_execution_duration_seconds")
    
    # Criar mapa de durações
    duration_map = {}
    for result in durations:
        wf_name = result["metric"].get("workflow_name", "unknown")
        duration = float(result["value"][1])
        duration_map[wf_name] = duration
    
    # Combinar dados
    workflows = []
    for result in totals:
        wf_name = result["metric"].get("workflow_name", "unknown")
        total = int(float(result["value"][1]))
        duration = duration_map.get(wf_name, 0)
        total_time = total * duration
        workflows.append((wf_name, total, total_time))
    
    # Ordenar por número de execuções (descendente)
    workflows.sort(key=lambda x: x[1], reverse=True)
    return workflows[:top_n]

def get_failed_workflows() -> List[Tuple[str, int, int, float]]:
    """Retorna workflows com falhas"""
    # Obter falhas
    failed = query_victoria_metrics("n8n_workflow_executions_failed")
    # Obter totais
    totals = query_victoria_metrics("n8n_workflow_executions_total")
    
    # Criar mapa de totais
    total_map = {}
    for result in totals:
        wf_name = result["metric"].get("workflow_name", "unknown")
        total = int(float(result["value"][1]))
        total_map[wf_name] = total
    
    # Combinar dados
    workflows = []
    for result in failed:
        wf_name = result["metric"].get("workflow_name", "unknown")
        failed_count = int(float(result["value"][1]))
        
        if failed_count > 0:  # Apenas workflows com falhas
            total = total_map.get(wf_name, failed_count)
            failure_rate = (failed_count / total * 100) if total > 0 else 0
            workflows.append((wf_name, failed_count, total, failure_rate))
    
    # Ordenar por taxa de falha (descendente)
    workflows.sort(key=lambda x: x[3], reverse=True)
    return workflows

def calculate_bottleneck_score(duration: float, executions: int) -> float:
    """
    Calcula score de gargalo baseado em duração e volume
    Score = duração_média * log10(executions + 1)
    Quanto maior o score, maior o impacto no sistema
    """
    import math
    return duration * math.log10(executions + 1)

def print_report():
    """Gera relatório de análise de gargalos"""
    
    print("=" * 80)
    print("N8N BOTTLENECK ANALYSIS REPORT")
    print("=" * 80)
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    # Workflows mais lentos
    print("🐌 TOP 10 SLOWEST WORKFLOWS (by average duration)")
    print("-" * 80)
    slowest = get_slowest_workflows(10)
    
    if slowest:
        print(f"{'Workflow':<50} {'Duration':>10} {'Executions':>10} {'Total Time':>10}")
        print("-" * 80)
        for wf_name, duration, total in slowest:
            total_time = duration * total
            print(f"{wf_name[:49]:<50} {duration:>9.2f}s {total:>10} {total_time:>9.1f}s")
    else:
        print("No data available")
    
    print()
    print()
    
    # Workflows mais executados
    print("🔥 TOP 10 MOST EXECUTED WORKFLOWS (by execution count)")
    print("-" * 80)
    most_executed = get_most_executed_workflows(10)
    
    if most_executed:
        print(f"{'Workflow':<50} {'Executions':>12} {'Total Time':>12}")
        print("-" * 80)
        for wf_name, total, total_time in most_executed:
            print(f"{wf_name[:49]:<50} {total:>12} {total_time:>11.1f}s")
    else:
        print("No data available")
    
    print()
    print()
    
    # Workflows com falhas
    print("❌ WORKFLOWS WITH FAILURES")
    print("-" * 80)
    failed = get_failed_workflows()
    
    if failed:
        print(f"{'Workflow':<45} {'Failed':>10} {'Total':>10} {'Failure %':>10}")
        print("-" * 80)
        for wf_name, failed_count, total, failure_rate in failed:
            print(f"{wf_name[:44]:<45} {failed_count:>10} {total:>10} {failure_rate:>9.1f}%")
    else:
        print("✅ No failures detected!")
    
    print()
    print()
    
    # Bottleneck Score
    print("🎯 BOTTLENECK PRIORITY (duration × log(executions))")
    print("-" * 80)
    print("Higher score = Higher priority for optimization")
    print("-" * 80)
    
    # Combinar dados para calcular score
    bottlenecks = []
    slowest = get_slowest_workflows(100)  # Pegar todos
    for wf_name, duration, total in slowest:
        score = calculate_bottleneck_score(duration, total)
        bottlenecks.append((wf_name, score, duration, total))
    
    bottlenecks.sort(key=lambda x: x[1], reverse=True)
    
    if bottlenecks:
        print(f"{'Workflow':<45} {'Score':>12} {'Duration':>10} {'Execs':>8}")
        print("-" * 80)
        for wf_name, score, duration, total in bottlenecks[:10]:
            print(f"{wf_name[:44]:<45} {score:>12.2f} {duration:>9.2f}s {total:>8}")
    else:
        print("No data available")
    
    print()
    print("=" * 80)
    print("💡 RECOMMENDATIONS:")
    print("=" * 80)
    
    if bottlenecks:
        top_bottleneck = bottlenecks[0]
        print(f"1. CRITICAL: Optimize '{top_bottleneck[0]}'")
        print(f"   - Bottleneck Score: {top_bottleneck[1]:.2f}")
        print(f"   - Average Duration: {top_bottleneck[2]:.2f}s")
        print(f"   - Total Executions: {top_bottleneck[3]}")
        print(f"   - Total Time Consumed: {top_bottleneck[2] * top_bottleneck[3]:.1f}s")
        print()
    
    if failed:
        print(f"2. HIGH: Investigate failures in '{failed[0][0]}'")
        print(f"   - Failure Rate: {failed[0][3]:.1f}%")
        print(f"   - Failed Executions: {failed[0][1]}")
        print()
    
    print("3. Monitor workflows with 'unknown' names - may indicate orphaned executions")
    print()
    
    print("=" * 80)

if __name__ == "__main__":
    try:
        print_report()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to Victoria Metrics at", VICTORIA_METRICS_URL)
        print("   Make sure Victoria Metrics is running: docker compose up -d")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
