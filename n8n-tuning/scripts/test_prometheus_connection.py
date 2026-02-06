#!/usr/bin/env python3
"""
Script para testar conexão com Prometheus Pushgateway
"""

import sys
import requests
from pathlib import Path

# Adicionar o diretório scripts ao path
sys.path.insert(0, str(Path(__file__).parent))

from credentials_helper import CredentialsManager


def test_pushgateway_connection(url: str) -> bool:
    """
    Testa conexão com Prometheus Pushgateway
    
    Args:
        url: URL do Pushgateway
        
    Returns:
        True se conectado, False caso contrário
    """
    print(f"🔍 Testando conexão com Pushgateway: {url}")
    
    try:
        # Tentar acessar a página principal
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        print(f"✅ Pushgateway está acessível!")
        print(f"   Status: {response.status_code}")
        return True
    except requests.exceptions.Timeout:
        print(f"❌ Timeout ao conectar com {url}")
        print(f"   Verifique se o servidor está acessível")
        return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Erro de conexão com {url}")
        print(f"   Verifique se o Pushgateway está rodando")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro: {e}")
        return False


def test_push_sample_metric(url: str, job_name: str = "test") -> bool:
    """
    Testa envio de uma métrica de exemplo
    
    Args:
        url: URL do Pushgateway
        job_name: Nome do job
        
    Returns:
        True se sucesso, False caso contrário
    """
    print(f"\n📤 Testando envio de métrica de exemplo...")
    
    # Métrica simples de teste
    metrics = """# HELP test_metric Metric de teste
# TYPE test_metric gauge
test_metric{instance="test"} 42
"""
    
    endpoint = f"{url}/metrics/job/{job_name}"
    
    try:
        response = requests.post(endpoint, data=metrics, timeout=5)
        response.raise_for_status()
        print(f"✅ Métrica enviada com sucesso!")
        print(f"   Endpoint: {endpoint}")
        print(f"   Status: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao enviar métrica: {e}")
        return False


def check_metrics(url: str, job_name: str = "test") -> bool:
    """
    Verifica métricas armazenadas no Pushgateway
    
    Args:
        url: URL do Pushgateway
        job_name: Nome do job
        
    Returns:
        True se encontrou métricas, False caso contrário
    """
    print(f"\n🔍 Verificando métricas no Pushgateway...")
    
    # Endpoint para ver todas as métricas
    endpoint = f"{url}/metrics"
    
    try:
        response = requests.get(endpoint, timeout=5)
        response.raise_for_status()
        
        metrics_text = response.text
        lines = metrics_text.split('\n')
        
        # Contar métricas (linhas que não são comentários ou vazias)
        metric_lines = [l for l in lines if l and not l.startswith('#')]
        
        print(f"✅ Métricas encontradas: {len(metric_lines)}")
        
        # Buscar por métricas do job de teste
        test_metrics = [l for l in metric_lines if f'job="{job_name}"' in l]
        if test_metrics:
            print(f"   Métricas do job '{job_name}': {len(test_metrics)}")
            if test_metrics:
                print(f"   Exemplo: {test_metrics[0][:100]}...")
        
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao verificar métricas: {e}")
        return False


def delete_test_metrics(url: str, job_name: str = "test") -> bool:
    """
    Remove métricas de teste
    
    Args:
        url: URL do Pushgateway
        job_name: Nome do job
        
    Returns:
        True se sucesso, False caso contrário
    """
    print(f"\n🗑️  Removendo métricas de teste...")
    
    endpoint = f"{url}/metrics/job/{job_name}"
    
    try:
        response = requests.delete(endpoint, timeout=5)
        response.raise_for_status()
        print(f"✅ Métricas de teste removidas!")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao remover métricas: {e}")
        return False


def main():
    """Função principal"""
    print("=" * 60)
    print("🚀 Teste de Conexão com Prometheus Pushgateway")
    print("=" * 60)
    print()
    
    try:
        # Carregar configuração
        print("🔍 Carregando configuração...")
        creds = CredentialsManager()
        prom_config = creds.get_prometheus_config()
        
        pushgateway_url = prom_config.get('pushgateway_url')
        
        if not pushgateway_url:
            print("❌ URL do Pushgateway não configurada")
            print("   Configure em .secrets/credentials.json")
            sys.exit(1)
        
        print(f"✅ URL configurada: {pushgateway_url}")
        print()
        
        # Executar testes
        print("=" * 60)
        print("📋 TESTES")
        print("=" * 60)
        
        # Teste 1: Conectividade
        test1 = test_pushgateway_connection(pushgateway_url)
        
        if not test1:
            print("\n❌ Falha no teste de conectividade")
            print("\n💡 Dicas:")
            print("   1. Verifique se o Pushgateway está rodando:")
            print("      systemctl status prometheus-pushgateway")
            print("   2. Verifique o firewall:")
            print("      sudo ufw status")
            print("   3. Teste localmente no servidor:")
            print(f"      curl {pushgateway_url}")
            sys.exit(1)
        
        # Teste 2: Enviar métrica
        test2 = test_push_sample_metric(pushgateway_url, "n8n_test")
        
        if not test2:
            print("\n❌ Falha ao enviar métrica de teste")
            sys.exit(1)
        
        # Teste 3: Verificar métricas
        test3 = check_metrics(pushgateway_url, "n8n_test")
        
        # Limpar métricas de teste
        delete_test_metrics(pushgateway_url, "n8n_test")
        
        # Resumo
        print()
        print("=" * 60)
        print("📊 RESUMO DOS TESTES")
        print("=" * 60)
        print(f"   Conectividade: {'✅' if test1 else '❌'}")
        print(f"   Envio de métricas: {'✅' if test2 else '❌'}")
        print(f"   Verificação de métricas: {'✅' if test3 else '❌'}")
        print()
        
        if test1 and test2 and test3:
            print("✅ Todos os testes passaram!")
            print("\n🎯 Próximos passos:")
            print("   1. Execute o exporter de métricas:")
            print("      python scripts/n8n_metrics_exporter.py --backend prometheus")
            print("   2. Execute o exporter de nodes:")
            print("      python scripts/n8n_node_metrics_exporter.py --backend prometheus")
            print("   3. Configure os crons para coleta automática")
            sys.exit(0)
        else:
            print("❌ Alguns testes falharam")
            sys.exit(1)
        
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
