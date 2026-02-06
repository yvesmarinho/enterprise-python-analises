#!/usr/bin/env python3
"""
Verificação de População de Métricas
Verifica se métricas estão sendo coletadas e armazenadas corretamente
Stack: enterprise-observability @ wfdb01.vya.digital
"""

import requests
import json
from datetime import datetime, timezone
from typing import Dict, List, Any
from urllib.parse import quote

# Configurações
PROMETHEUS_URL = "https://prometheus.vya.digital"
PUSHGATEWAY_URL = "https://prometheus.vya.digital/pushgateway"
TIMEOUT = 15

# Jobs que devem estar enviando métricas
EXPECTED_JOBS = [
    "collector_api_wf001_usa",
    "n8n_metrics",
    "n8n_node_metrics"
]


def get_pushgateway_metrics() -> Dict[str, Any]:
    """
    Lista todas as métricas disponíveis no Pushgateway
    
    Returns:
        Dict com resultado
    """
    result = {
        "test": "pushgateway_metrics",
        "url": f"{PUSHGATEWAY_URL}/metrics",
        "status": "UNKNOWN",
        "jobs_found": [],
        "metrics_count": 0,
        "sample_metrics": [],
        "error": None
    }
    
    try:
        response = requests.get(
            f"{PUSHGATEWAY_URL}/metrics",
            timeout=TIMEOUT,
            verify=True
        )
        
        if response.status_code == 200:
            metrics_text = response.text
            lines = metrics_text.split('\n')
            
            # Contar métricas (linhas que não são comentários ou vazias)
            metric_lines = [l for l in lines if l and not l.startswith('#')]
            result["metrics_count"] = len(metric_lines)
            
            # Procurar jobs conhecidos
            jobs_found = set()
            collector_metrics = []
            
            for line in lines:
                if not line or line.startswith('#'):
                    continue
                    
                # Identificar jobs nas labels
                for job in EXPECTED_JOBS:
                    if f'job="{job}"' in line:
                        jobs_found.add(job)
                        if job == "collector_api_wf001_usa" and len(collector_metrics) < 10:
                            collector_metrics.append(line[:150])
            
            result["jobs_found"] = list(jobs_found)
            result["sample_metrics"] = collector_metrics[:5]
            result["status"] = "✅ OK" if jobs_found else "⚠️ Sem métricas dos jobs esperados"
            
        else:
            result["status"] = f"❌ HTTP {response.status_code}"
            
    except Exception as e:
        result["status"] = "❌ ERRO"
        result["error"] = f"{type(e).__name__}: {str(e)}"
    
    return result


def get_prometheus_targets() -> Dict[str, Any]:
    """
    Lista targets ativos no Prometheus
    
    Returns:
        Dict com resultado
    """
    result = {
        "test": "prometheus_targets",
        "url": f"{PROMETHEUS_URL}/api/v1/targets",
        "status": "UNKNOWN",
        "active_targets": 0,
        "targets": [],
        "error": None
    }
    
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/targets",
            timeout=TIMEOUT,
            verify=True
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("status") == "success":
                active_targets = data.get("data", {}).get("activeTargets", [])
                result["active_targets"] = len(active_targets)
                
                # Filtrar targets do pushgateway
                pushgateway_targets = [
                    {
                        "job": t.get("labels", {}).get("job"),
                        "instance": t.get("labels", {}).get("instance"),
                        "health": t.get("health"),
                        "lastScrape": t.get("lastScrape"),
                        "scrapeUrl": t.get("scrapeUrl")
                    }
                    for t in active_targets
                    if "pushgateway" in t.get("scrapeUrl", "").lower() or 
                       t.get("labels", {}).get("job") in EXPECTED_JOBS
                ]
                
                result["targets"] = pushgateway_targets
                result["status"] = "✅ OK"
            else:
                result["status"] = "⚠️ API retornou status diferente de success"
                
        else:
            result["status"] = f"❌ HTTP {response.status_code}"
            
    except Exception as e:
        result["status"] = "❌ ERRO"
        result["error"] = f"{type(e).__name__}: {str(e)}"
    
    return result


def query_prometheus_metrics(job_name: str) -> Dict[str, Any]:
    """
    Consulta métricas de um job específico no Prometheus
    
    Args:
        job_name: Nome do job a consultar
        
    Returns:
        Dict com resultado
    """
    result = {
        "test": f"prometheus_query_{job_name}",
        "job": job_name,
        "status": "UNKNOWN",
        "series_count": 0,
        "metrics": [],
        "last_values": {},
        "error": None
    }
    
    try:
        # Query para listar todas as séries do job
        query = f'{{job="{job_name}"}}'
        
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=TIMEOUT,
            verify=True
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("status") == "success":
                result_data = data.get("data", {}).get("result", [])
                result["series_count"] = len(result_data)
                
                # Extrair nomes das métricas e últimos valores
                for item in result_data[:10]:  # Limitar a 10 exemplos
                    metric_name = item.get("metric", {}).get("__name__", "unknown")
                    value = item.get("value", [None, None])
                    
                    if metric_name not in result["metrics"]:
                        result["metrics"].append(metric_name)
                    
                    # Pegar timestamp e valor
                    if len(value) == 2:
                        timestamp = datetime.fromtimestamp(value[0], tz=timezone.utc)
                        result["last_values"][metric_name] = {
                            "value": value[1],
                            "timestamp": timestamp.isoformat()
                        }
                
                result["status"] = "✅ OK" if result["series_count"] > 0 else "⚠️ Sem séries encontradas"
            else:
                result["status"] = "⚠️ Query falhou"
                result["error"] = data.get("error", "Unknown error")
        else:
            result["status"] = f"❌ HTTP {response.status_code}"
            
    except Exception as e:
        result["status"] = "❌ ERRO"
        result["error"] = f"{type(e).__name__}: {str(e)}"
    
    return result


def check_specific_metrics() -> Dict[str, Any]:
    """
    Verifica métricas específicas do collector-api
    
    Returns:
        Dict com resultado  
    """
    result = {
        "test": "specific_metrics_check",
        "status": "UNKNOWN",
        "metrics_found": {},
        "error": None
    }
    
    # Métricas esperadas do collector-api
    expected_metrics = [
        "api_requests_total",
        "api_request_duration_seconds",
        "database_health",
        "mysql_health",
        "postgres_health",
        "service_up"
    ]
    
    try:
        for metric_name in expected_metrics:
            query = f'{metric_name}{{job="collector_api_wf001_usa"}}'
            
            response = requests.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": query},
                timeout=TIMEOUT,
                verify=True
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    result_data = data.get("data", {}).get("result", [])
                    result["metrics_found"][metric_name] = {
                        "found": len(result_data) > 0,
                        "series_count": len(result_data),
                        "sample_value": result_data[0].get("value", [None, None])[1] if result_data else None
                    }
        
        found_count = sum(1 for m in result["metrics_found"].values() if m["found"])
        result["status"] = f"✅ {found_count}/{len(expected_metrics)} métricas encontradas"
        
    except Exception as e:
        result["status"] = "❌ ERRO"
        result["error"] = f"{type(e).__name__}: {str(e)}"
    
    return result


def print_result(result: Dict[str, Any]) -> None:
    """Imprime resultado formatado"""
    print(f"\n{'='*80}")
    print(f"Teste: {result.get('test', 'Unknown')}")
    if result.get('job'):
        print(f"Job: {result['job']}")
    if result.get('url'):
        print(f"URL: {result['url']}")
    print(f"Status: {result['status']}")
    
    if result.get('jobs_found'):
        print(f"\n📊 Jobs encontrados no Pushgateway:")
        for job in result['jobs_found']:
            print(f"   - {job}")
        
        if result.get('sample_metrics'):
            print(f"\n📝 Exemplos de métricas do collector-api:")
            for metric in result['sample_metrics']:
                print(f"   {metric}")
    
    if result.get('metrics_count'):
        print(f"\n📈 Total de linhas de métricas: {result['metrics_count']}")
    
    if result.get('active_targets') is not None:
        print(f"\n🎯 Targets ativos: {result['active_targets']}")
        
        if result.get('targets'):
            print(f"\n📍 Targets do Pushgateway:")
            for target in result['targets']:
                print(f"   Job: {target['job']}")
                print(f"   Instance: {target['instance']}")
                print(f"   Health: {target['health']}")
                print(f"   Last Scrape: {target['lastScrape']}")
                print(f"   URL: {target['scrapeUrl']}")
                print()
    
    if result.get('series_count') is not None:
        print(f"\n📊 Séries temporais encontradas: {result['series_count']}")
        
        if result.get('metrics'):
            print(f"\n📝 Métricas disponíveis:")
            for metric in result['metrics'][:10]:
                print(f"   - {metric}")
                if metric in result.get('last_values', {}):
                    val = result['last_values'][metric]
                    print(f"     Último valor: {val['value']} @ {val['timestamp']}")
    
    if result.get('metrics_found'):
        print(f"\n🔍 Verificação de métricas específicas:")
        for metric_name, info in result['metrics_found'].items():
            status_icon = "✅" if info['found'] else "❌"
            print(f"   {status_icon} {metric_name}")
            if info['found']:
                print(f"      Séries: {info['series_count']} | Valor: {info['sample_value']}")
    
    if result.get('error'):
        print(f"\n⚠️ Erro: {result['error']}")


def main():
    """Função principal"""
    print(f"{'='*80}")
    print("VERIFICAÇÃO DE POPULAÇÃO DE MÉTRICAS")
    print(f"Stack: enterprise-observability @ wfdb01.vya.digital")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*80}")
    
    # 1. Verificar métricas no Pushgateway
    print(f"\n🔍 Verificando métricas no Pushgateway...")
    pushgateway_result = get_pushgateway_metrics()
    print_result(pushgateway_result)
    
    # 2. Verificar targets do Prometheus
    print(f"\n\n🔍 Verificando targets no Prometheus...")
    targets_result = get_prometheus_targets()
    print_result(targets_result)
    
    # 3. Consultar métricas do collector-api
    print(f"\n\n🔍 Consultando métricas do collector-api...")
    collector_result = query_prometheus_metrics("collector_api_wf001_usa")
    print_result(collector_result)
    
    # 4. Verificar métricas específicas
    print(f"\n\n🔍 Verificando métricas específicas...")
    specific_result = check_specific_metrics()
    print_result(specific_result)
    
    # Resumo final
    print(f"\n{'='*80}")
    print("RESUMO")
    print(f"{'='*80}")
    
    all_ok = all([
        "✅" in pushgateway_result['status'],
        "✅" in targets_result['status'],
        "✅" in collector_result['status']
    ])
    
    if all_ok:
        print("✅ Sistema de métricas funcionando corretamente!")
        print(f"   - Pushgateway recebendo métricas")
        print(f"   - Prometheus com targets ativos")
        print(f"   - Métricas do collector-api disponíveis")
    else:
        print("⚠️ Alguns componentes apresentam problemas:")
        if "❌" in pushgateway_result['status']:
            print("   - Pushgateway não está recebendo métricas corretamente")
        if "❌" in targets_result['status']:
            print("   - Prometheus sem targets ativos")
        if "❌" in collector_result['status']:
            print("   - Métricas do collector-api não encontradas")
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    exit(main())
