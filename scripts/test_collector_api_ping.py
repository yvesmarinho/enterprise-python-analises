#!/usr/bin/env python3
"""
Teste de Endpoint /api/ping do Collector API
Envia requisições de ping e valida resposta e métricas
Servidor: wf001.vya.digital
"""

import requests
import time
from datetime import datetime, timezone
from typing import Dict, Any

# Configurações
COLLECTOR_API_URL = "http://wf001.vya.digital:5001"  # Porta 5001 exposta
API_KEY = "YOUR_API_KEY_HERE"  # Substituir pela chave real
TIMEOUT = 10

def send_ping_request(ping_id: str) -> Dict[str, Any]:
    """
    Envia uma requisição de ping para o Collector API
    
    Args:
        ping_id: ID único do ping
        
    Returns:
        Dict com resultado
    """
    result = {
        "test": "ping_request",
        "ping_id": ping_id,
        "status": "UNKNOWN",
        "error": None,
        "response_data": None,
        "metrics": {}
    }
    
    # Preparar dados do ping
    timestamp_start = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    payload = {
        "ping_id": ping_id,
        "timestamp_start": timestamp_start,
        "source": {
            "location": "test-local",
            "datacenter": "test-dc",
            "country": "BR"
        }
    }
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        start_time = time.perf_counter()
        
        response = requests.post(
            f"{COLLECTOR_API_URL}/api/ping",
            json=payload,
            headers=headers,
            timeout=TIMEOUT
        )
        
        request_duration = (time.perf_counter() - start_time) * 1000
        
        result["metrics"]["request_duration_ms"] = round(request_duration, 2)
        
        if response.status_code == 200:
            response_data = response.json()
            result["status"] = "✅ OK"
            result["response_data"] = response_data
            
            # Extrair métricas da resposta
            result["metrics"]["processing_time_ms"] = response_data.get("processing_time_ms")
            result["metrics"]["network_rtt_ms"] = response_data.get("network_rtt_ms")
            result["metrics"]["timestamp_received"] = response_data.get("timestamp_received")
            result["metrics"]["timestamp_processed"] = response_data.get("timestamp_processed")
            
        elif response.status_code == 401:
            result["status"] = "❌ UNAUTHORIZED"
            result["error"] = "API Key inválida ou ausente"
            
        else:
            result["status"] = f"❌ HTTP {response.status_code}"
            result["error"] = response.text[:200]
            
    except requests.exceptions.Timeout:
        result["status"] = "⏱️ TIMEOUT"
        result["error"] = f"Timeout após {TIMEOUT}s"
        
    except requests.exceptions.ConnectionError as e:
        result["status"] = "❌ CONEXÃO"
        result["error"] = f"Erro de conexão: {str(e)[:100]}"
        
    except Exception as e:
        result["status"] = "❌ ERRO"
        result["error"] = f"{type(e).__name__}: {str(e)}"
    
    return result


def query_ping_metrics(job_name: str = "collector_api_wf001_usa") -> Dict[str, Any]:
    """
    Consulta métricas de ping no Prometheus
    
    Args:
        job_name: Nome do job
        
    Returns:
        Dict com resultado
    """
    result = {
        "test": "query_ping_metrics",
        "status": "UNKNOWN",
        "api_requests_total": None,
        "api_request_duration": None,
        "network_rtt": None,
        "error": None
    }
    
    prometheus_url = "https://prometheus.vya.digital"
    
    try:
        # Query 1: Total de requests
        response = requests.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": f'api_requests_total{{job="{job_name}",endpoint="/api/ping"}}'},
            timeout=10,
            verify=True
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                results = data.get("data", {}).get("result", [])
                if results:
                    result["api_requests_total"] = results[0].get("value", [None, None])[1]
        
        # Query 2: Duração média das requests (último minuto)
        response = requests.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": f'rate(api_request_duration_seconds_sum{{job="{job_name}",endpoint="/api/ping"}}[1m]) / rate(api_request_duration_seconds_count{{job="{job_name}",endpoint="/api/ping"}}[1m])'},
            timeout=10,
            verify=True
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                results = data.get("data", {}).get("result", [])
                if results:
                    avg_duration = float(results[0].get("value", [None, None])[1])
                    result["api_request_duration"] = round(avg_duration * 1000, 2)  # Converter para ms
        
        # Query 3: Network RTT médio (se disponível)
        response = requests.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": f'avg(network_latency_rtt_seconds{{job="{job_name}"}})'},
            timeout=10,
            verify=True
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                results = data.get("data", {}).get("result", [])
                if results:
                    avg_rtt = float(results[0].get("value", [None, None])[1])
                    result["network_rtt"] = round(avg_rtt * 1000, 2)  # Converter para ms
        
        result["status"] = "✅ OK"
        
    except Exception as e:
        result["status"] = "❌ ERRO"
        result["error"] = f"{type(e).__name__}: {str(e)}"
    
    return result


def print_result(result: Dict[str, Any]) -> None:
    """Imprime resultado formatado"""
    print(f"\n{'='*80}")
    print(f"Teste: {result.get('test', 'Unknown')}")
    
    if result.get('ping_id'):
        print(f"Ping ID: {result['ping_id']}")
    
    print(f"Status: {result['status']}")
    
    if result.get('metrics'):
        print(f"\n📊 Métricas:")
        for key, value in result['metrics'].items():
            if value is not None:
                print(f"   {key}: {value}")
    
    if result.get('response_data'):
        print(f"\n📝 Resposta:")
        resp = result['response_data']
        print(f"   Mensagem: {resp.get('message')}")
        print(f"   Status: {resp.get('status')}")
    
    if result.get('api_requests_total'):
        print(f"\n📈 Métricas no Prometheus:")
        print(f"   Total de requests: {result['api_requests_total']}")
        
    if result.get('api_request_duration'):
        print(f"   Duração média (1m): {result['api_request_duration']}ms")
        
    if result.get('network_rtt'):
        print(f"   Network RTT médio: {result['network_rtt']}ms")
    
    if result.get('error'):
        print(f"\n⚠️ Erro: {result['error']}")


def main():
    """Função principal"""
    print(f"{'='*80}")
    print("TESTE DE ENDPOINT /api/ping - Collector API")
    print(f"Servidor: wf001.vya.digital:5001")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*80}")
    
    # Verificar API Key
    if API_KEY == "YOUR_API_KEY_HERE":
        print("\n⚠️ ATENÇÃO: Configure a API_KEY antes de executar!")
        print("   Edite a variável API_KEY no script com a chave real.")
        print("\n💡 Para obter a API Key:")
        print("   1. Verifique o arquivo .env no servidor wf001")
        print("   2. Procure pela variável COLLECTOR_API_KEY")
        return 1
    
    # Teste 1: Enviar requisição de ping
    ping_id = f"test-{int(time.time())}"
    print(f"\n🔍 Enviando requisição de ping (ID: {ping_id})...")
    ping_result = send_ping_request(ping_id)
    print_result(ping_result)
    
    if "✅" not in ping_result['status']:
        print(f"\n❌ Falha ao enviar ping. Verifique:")
        print(f"   - API Key está correta")
        print(f"   - Servidor wf001.vya.digital:5001 está acessível")
        print(f"   - Container collector-api está rodando")
        return 1
    
    # Aguardar métricas serem processadas
    print(f"\n⏳ Aguardando 5s para métricas serem processadas...")
    time.sleep(5)
    
    # Teste 2: Consultar métricas no Prometheus
    print(f"\n🔍 Consultando métricas no Prometheus...")
    metrics_result = query_ping_metrics()
    print_result(metrics_result)
    
    # Resumo
    print(f"\n{'='*80}")
    print("RESUMO")
    print(f"{'='*80}")
    
    all_ok = "✅" in ping_result['status'] and "✅" in metrics_result['status']
    
    if all_ok:
        print("✅ Endpoint /api/ping funcionando corretamente!")
        print(f"   - Requisição processada com sucesso")
        print(f"   - Métricas disponíveis no Prometheus")
        print(f"   - RTT calculado: {ping_result['metrics'].get('network_rtt_ms', 'N/A')}ms")
        print(f"   - Processamento: {ping_result['metrics'].get('processing_time_ms', 'N/A')}ms")
    else:
        print("⚠️ Alguns problemas encontrados:")
        if "❌" in ping_result['status']:
            print("   - Falha ao enviar requisição de ping")
        if "❌" in metrics_result['status']:
            print("   - Falha ao consultar métricas no Prometheus")
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    exit(main())
