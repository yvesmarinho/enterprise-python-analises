#!/usr/bin/env python3
"""
Script para verificar métricas do collector-api no VictoriaMetrics
Consulta via API do VictoriaMetrics para confirmar recepção de dados
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Configuração
VICTORIAMETRICS_URL = "http://wfdb01.vya.digital:8428"  # URL interna do VictoriaMetrics
# Para acesso via Prometheus (que faz remote_write):
PROMETHEUS_URL = "https://prometheus.vya.digital"
# VictoriaMetrics acessível via proxy reverso (Traefik)
VICTORIA_PUBLIC_URL = "https://prometheus.vya.digital"  # Mesmo endpoint do Prometheus

def query_victoriametrics(query: str, base_url: str = PROMETHEUS_URL) -> Dict[str, Any]:
    """Executa query no VictoriaMetrics usando API compatível com Prometheus"""
    try:
        url = f"{base_url}/api/v1/query"
        params = {"query": query}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Erro ao consultar VictoriaMetrics: {e}")
        return {"status": "error", "error": str(e)}

def query_range(query: str, hours_back: int = 24, base_url: str = PROMETHEUS_URL) -> Dict[str, Any]:
    """Executa range query no VictoriaMetrics"""
    try:
        url = f"{base_url}/api/v1/query_range"
        end = datetime.now()
        start = end - timedelta(hours=hours_back)

        params = {
            "query": query,
            "start": int(start.timestamp()),
            "end": int(end.timestamp()),
            "step": "60s"  # 1 minuto de resolução
        }

        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Erro ao consultar range: {e}")
        return {"status": "error", "error": str(e)}

def get_series_info(metric_name: str = "", base_url: str = PROMETHEUS_URL) -> Dict[str, Any]:
    """Lista todas as séries temporais para um padrão de métrica"""
    try:
        url = f"{base_url}/api/v1/series"
        params = {}
        if metric_name:
            params["match[]"] = f"{{{metric_name}}}"
        else:
            # Buscar todas relacionadas a collector_api
            params["match[]"] = "{job=~\".*collector.*\"}"

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Erro ao listar séries: {e}")
        return {"status": "error", "error": str(e)}

def check_collector_api_metrics():
    """Verifica métricas específicas do collector-api no VictoriaMetrics"""

    print("=" * 80)
    print("🔍 VERIFICAÇÃO DE MÉTRICAS NO VICTORIAMETRICS VIA PROMETHEUS")
    print("=" * 80)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} BRT")
    print(f"Prometheus URL: {PROMETHEUS_URL}")
    print(f"Nota: Prometheus faz remote_write para VictoriaMetrics interno")
    print()

    # 1. Verificar se há métricas do job pushgateway
    print("📊 1. Verificando métricas do Pushgateway...")
    print("-" * 80)

    result = query_victoriametrics('up{job="pushgateway"}')
    if result.get("status") == "success":
        data = result.get("data", {}).get("result", [])
        if data:
            print(f"✅ Pushgateway status: UP")
            for item in data:
                metric = item.get("metric", {})
                value = item.get("value", [None, None])[1]
                print(f"   Instance: {metric.get('instance', 'N/A')}")
                print(f"   Value: {value}")
        else:
            print("⚠️  Nenhuma métrica 'up' encontrada para pushgateway")
    print()

    # 2. Buscar métricas específicas do collector-api via pushgateway
    print("📊 2. Buscando métricas do collector_api...")
    print("-" * 80)

    queries_to_check = [
        ('collector_api_up', 'Status do Collector API'),
        ('api_requests_total{job=~".*collector.*"}', 'Total de requisições API'),
        ('push_time_seconds{job=~".*collector.*"}', 'Timestamp da última push'),
        ('process_resident_memory_bytes{job=~".*collector.*"}', 'Uso de memória'),
        ('process_cpu_seconds_total{job=~".*collector.*"}', 'CPU total usado'),
    ]

    metrics_found = []
    for query, description in queries_to_check:
        result = query_victoriametrics(query)
        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            if data:
                print(f"✅ {description}")
                for item in data:
                    metric = item.get("metric", {})
                    value = item.get("value", [None, None])[1]
                    job = metric.get("job", "N/A")
                    instance = metric.get("instance", "N/A")
                    print(f"   Job: {job}")
                    print(f"   Instance: {instance}")
                    print(f"   Valor: {value}")

                    # Adicionar à lista de métricas encontradas
                    metrics_found.append({
                        "metric": query.split("{")[0],
                        "job": job,
                        "instance": instance,
                        "value": value
                    })
                print()
            else:
                print(f"❌ {description}: Nenhum dado encontrado")
                print()
        else:
            print(f"❌ {description}: Erro na query")
            print()

    # 3. Listar todas as séries do collector-api
    print("📊 3. Listando todas as séries temporais do collector-api...")
    print("-" * 80)

    series_result = get_series_info()
    if series_result.get("status") == "success":
        series = series_result.get("data", [])

        # Filtrar apenas séries relacionadas ao collector-api
        collector_series = [s for s in series if "collector" in str(s).lower()]

        if collector_series:
            print(f"✅ Encontradas {len(collector_series)} séries temporais do collector-api\n")

            # Agrupar por job
            jobs = {}
            for s in collector_series:
                job = s.get("job", "unknown")
                if job not in jobs:
                    jobs[job] = []
                jobs[job].append(s.get("__name__", "unnamed_metric"))

            for job, metric_names in jobs.items():
                print(f"📌 Job: {job}")
                print(f"   Métricas: {len(metric_names)}")
                # Mostrar apenas as primeiras 10 para não poluir
                for idx, metric in enumerate(sorted(set(metric_names))[:10], 1):
                    print(f"   {idx}. {metric}")
                if len(metric_names) > 10:
                    print(f"   ... e mais {len(metric_names) - 10} métricas")
                print()
        else:
            print("❌ Nenhuma série temporal encontrada para collector-api")
    print()

    # 4. Verificar dados nas últimas 24h
    print("📊 4. Verificando dados das últimas 24 horas...")
    print("-" * 80)

    range_query = 'collector_api_up'
    range_result = query_range(range_query, hours_back=24)

    if range_result.get("status") == "success":
        data = range_result.get("data", {}).get("result", [])
        if data:
            for series in data:
                metric = series.get("metric", {})
                values = series.get("values", [])

                print(f"✅ Série encontrada:")
                print(f"   Job: {metric.get('job', 'N/A')}")
                print(f"   Instance: {metric.get('instance', 'N/A')}")
                print(f"   Pontos de dados (24h): {len(values)}")

                if values:
                    # Mostrar primeiro e último valor
                    first_ts, first_val = values[0]
                    last_ts, last_val = values[-1]

                    first_time = datetime.fromtimestamp(first_ts)
                    last_time = datetime.fromtimestamp(last_ts)

                    print(f"   Primeiro dado: {first_time.strftime('%Y-%m-%d %H:%M:%S')} = {first_val}")
                    print(f"   Último dado: {last_time.strftime('%Y-%m-%d %H:%M:%S')} = {last_val}")
                print()
        else:
            print("❌ Nenhum dado encontrado nas últimas 24h")
    else:
        print(f"❌ Erro ao buscar dados: {range_result.get('error', 'Unknown')}")
    print()

    # 5. Resumo final
    print("=" * 80)
    print("📊 RESUMO DA ANÁLISE")
    print("=" * 80)

    if metrics_found:
        print(f"✅ VictoriaMetrics ESTÁ recebendo dados do collector-api")
        print(f"✅ Total de métricas ativas encontradas: {len(metrics_found)}")
        print()
        print("📋 Métricas principais:")
        for m in metrics_found:
            print(f"   • {m['metric']} (job={m['job']}): {m['value']}")
    else:
        print("⚠️  ATENÇÃO: Nenhuma métrica do collector-api encontrada no VictoriaMetrics")
        print()
        print("Possíveis causas:")
        print("   1. Prometheus não está fazendo remote_write para VictoriaMetrics")
        print("   2. Pushgateway não está sendo scrapado pelo Prometheus")
        print("   3. Collector-api não está enviando métricas para o Pushgateway")
        print("   4. VictoriaMetrics não está acessível na URL configurada")

    print("=" * 80)

if __name__ == "__main__":
    try:
        check_collector_api_metrics()
    except KeyboardInterrupt:
        print("\n\n⚠️  Verificação interrompida pelo usuário")
    except Exception as e:
        print(f"\n\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
