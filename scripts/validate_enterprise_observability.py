#!/usr/bin/env python3
"""
Validação da Stack Enterprise Observability
Servidor: wfdb01.vya.digital (86.48.31.149)
Stack: enterprise-observability via Traefik
"""

import requests
import time
from datetime import datetime
from typing import Dict, Any, List
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# Configurações
BASE_DOMAIN = "vya.digital"
TIMEOUT = 10  # segundos

# URLs dos serviços (todos via HTTPS/Traefik)
SERVICES = {
    "grafana": {
        "url": f"https://grafana.{BASE_DOMAIN}",
        "endpoint": "/api/health",
        "expected_status": [200],
        "description": "Grafana - Interface de visualização"
    },
    "prometheus": {
        "url": f"https://prometheus.{BASE_DOMAIN}",
        "endpoint": "/-/healthy",
        "expected_status": [200],
        "description": "Prometheus - Coleta de métricas"
    },
    "loki": {
        "url": f"https://loki.{BASE_DOMAIN}",
        "endpoint": "/ready",
        "expected_status": [200],
        "description": "Loki - Agregação de logs"
    },
    "alertmanager": {
        "url": f"https://alertmanager.{BASE_DOMAIN}",
        "endpoint": "/-/healthy",
        "expected_status": [200],
        "description": "Alertmanager - Gerenciamento de alertas"
    },
    "pushgateway": {
        "url": f"https://prometheus.{BASE_DOMAIN}/pushgateway",
        "endpoint": "/metrics",
        "expected_status": [200],
        "description": "Pushgateway - Recebe métricas via push"
    }
}


def validate_service(service_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida conectividade e saúde de um serviço
    
    Args:
        service_name: Nome do serviço
        config: Configuração do serviço
    
    Returns:
        Dict com resultado da validação
    """
    result = {
        "service": service_name,
        "url": config["url"],
        "endpoint": config["endpoint"],
        "description": config["description"],
        "status": "UNKNOWN",
        "http_code": None,
        "response_time_ms": None,
        "ssl_valid": None,
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    full_url = f"{config['url']}{config['endpoint']}"
    
    try:
        start_time = time.perf_counter()
        response = requests.get(
            full_url,
            timeout=TIMEOUT,
            verify=True,  # Valida certificado SSL
            allow_redirects=True
        )
        response_time = (time.perf_counter() - start_time) * 1000
        
        result["http_code"] = response.status_code
        result["response_time_ms"] = round(response_time, 2)
        result["ssl_valid"] = True
        
        if response.status_code in config["expected_status"]:
            result["status"] = "✅ OK"
        else:
            result["status"] = "⚠️ WARNING"
            result["error"] = f"HTTP {response.status_code} (esperado {config['expected_status']})"
            
    except requests.exceptions.SSLError as e:
        result["status"] = "❌ ERRO SSL"
        result["ssl_valid"] = False
        result["error"] = f"Certificado SSL inválido: {str(e)[:100]}"
        
    except requests.exceptions.Timeout:
        result["status"] = "⏱️ TIMEOUT"
        result["error"] = f"Timeout após {TIMEOUT}s"
        
    except requests.exceptions.ConnectionError as e:
        result["status"] = "❌ CONEXÃO"
        result["error"] = f"Erro de conexão: {str(e)[:100]}"
        
    except Exception as e:
        result["status"] = "❌ ERRO"
        result["error"] = f"{type(e).__name__}: {str(e)[:100]}"
    
    return result


def test_pushgateway_push() -> Dict[str, Any]:
    """
    Testa envio de métricas para o Pushgateway
    
    Returns:
        Dict com resultado do teste
    """
    result = {
        "test": "pushgateway_push",
        "description": "Teste de envio de métricas",
        "status": "UNKNOWN",
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    pushgateway_url = f"https://prometheus.{BASE_DOMAIN}/pushgateway"
    
    try:
        # Criar métrica de teste
        registry = CollectorRegistry()
        test_metric = Gauge(
            'validation_test_metric',
            'Métrica de teste de validação',
            ['source'],
            registry=registry
        )
        test_metric.labels(source='validation_script').set(1)
        
        # Enviar para Pushgateway
        push_to_gateway(
            pushgateway_url,
            job='validation_test',
            registry=registry,
            timeout=TIMEOUT
        )
        
        result["status"] = "✅ OK"
        result["message"] = "Métricas enviadas com sucesso"
        
    except Exception as e:
        result["status"] = "❌ ERRO"
        result["error"] = f"{type(e).__name__}: {str(e)}"
    
    return result


def print_result(result: Dict[str, Any]) -> None:
    """Imprime resultado formatado"""
    print(f"\n{'='*80}")
    print(f"Serviço: {result.get('service', result.get('test'))}")
    print(f"Descrição: {result.get('description', 'N/A')}")
    print(f"URL: {result.get('url', 'N/A')}")
    print(f"Status: {result['status']}")
    
    if result.get('http_code'):
        print(f"HTTP Code: {result['http_code']}")
    
    if result.get('response_time_ms'):
        print(f"Tempo de Resposta: {result['response_time_ms']}ms")
    
    if result.get('ssl_valid') is not None:
        ssl_status = "✅ Válido" if result['ssl_valid'] else "❌ Inválido"
        print(f"Certificado SSL: {ssl_status}")
    
    if result.get('error'):
        print(f"⚠️ Erro: {result['error']}")
    
    if result.get('message'):
        print(f"📝 Mensagem: {result['message']}")


def generate_summary(results: List[Dict[str, Any]]) -> None:
    """Gera resumo da validação"""
    print(f"\n{'='*80}")
    print("RESUMO DA VALIDAÇÃO")
    print(f"{'='*80}")
    
    total = len(results)
    success = sum(1 for r in results if "✅ OK" in r['status'])
    warnings = sum(1 for r in results if "⚠️" in r['status'])
    errors = total - success - warnings
    
    print(f"Total de testes: {total}")
    print(f"✅ Sucesso: {success}")
    print(f"⚠️ Avisos: {warnings}")
    print(f"❌ Erros: {errors}")
    print(f"\nTaxa de sucesso: {(success/total)*100:.1f}%")
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")


def main():
    """Função principal"""
    print(f"{'='*80}")
    print("VALIDAÇÃO: Enterprise Observability Stack")
    print(f"Servidor: wfdb01.vya.digital (86.48.31.149)")
    print(f"Domínio: {BASE_DOMAIN}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    print(f"{'='*80}")
    
    results = []
    
    # Validar cada serviço
    for service_name, config in SERVICES.items():
        print(f"\n🔍 Validando {service_name}...", end=" ")
        result = validate_service(service_name, config)
        results.append(result)
        print(result['status'])
        print_result(result)
    
    # Testar push de métricas para Pushgateway
    print(f"\n\n🔍 Testando envio de métricas para Pushgateway...", end=" ")
    push_result = test_pushgateway_push()
    results.append(push_result)
    print(push_result['status'])
    print_result(push_result)
    
    # Gerar resumo
    generate_summary(results)
    
    # Exit code baseado em resultados
    errors = sum(1 for r in results if "❌" in r['status'])
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    exit(main())
