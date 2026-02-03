#!/usr/bin/env python3
"""
Teste Rápido da API do N8N
Valida conexão e coleta informações básicas
"""

import sys
from pathlib import Path

# Adicionar o diretório scripts ao path
sys.path.insert(0, str(Path(__file__).parent))

from credentials_helper import CredentialsManager
from n8n_metrics_collector import N8NMetricsCollector


def test_n8n_connection():
    """Testa conexão com a API do N8N"""
    
    print("🔍 Carregando credenciais...")
    try:
        creds = CredentialsManager()
        n8n_config = creds.get_n8n_config()
        
        url = n8n_config.get('url')
        api_key = n8n_config.get('api_key')
        
        if not url or not api_key:
            print("❌ Erro: URL ou API Key não encontrados nas credenciais")
            return False
        
        print(f"✅ URL: {url}")
        print(f"✅ API Key: {api_key[:20]}...")
        
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return False
    except Exception as e:
        print(f"❌ Erro ao carregar credenciais: {e}")
        return False
    
    print("\n🚀 Testando conexão com N8N API...")
    try:
        collector = N8NMetricsCollector(url, api_key)
        
        # Teste 1: Coletar workflows
        print("\n📋 Teste 1: Listando workflows")
        print("-" * 60)
        workflows = collector.collect_workflows()
        
        if workflows:
            print(f"\n✅ Sucesso! {len(workflows)} workflows encontrados\n")
            
            # Mostrar primeiros 5 workflows
            print("📌 Primeiros workflows:")
            for i, wf in enumerate(workflows[:5], 1):
                name = wf.get('name', 'Sem nome')
                wf_id = wf.get('id', 'N/A')
                active = "✅ Ativo" if wf.get('active', False) else "⏸️ Inativo"
                nodes = len(wf.get('nodes', []))
                print(f"   {i}. {name}")
                print(f"      ID: {wf_id} | {active} | {nodes} nodes")
        
        # Teste 2: Coletar execuções recentes
        print("\n📋 Teste 2: Coletando execuções recentes (últimas 20)")
        print("-" * 60)
        executions = collector.collect_executions(limit=20)
        
        if executions:
            print(f"\n✅ Sucesso! {len(executions)} execuções coletadas\n")
            
            # Estatísticas
            finished = [ex for ex in executions if ex.get('finished', False)]
            success = [ex for ex in executions if ex.get('finished') and not ex.get('stoppedAt')]
            
            print("📊 Estatísticas das execuções:")
            print(f"   • Total: {len(executions)}")
            print(f"   • Finalizadas: {len(finished)}")
            print(f"   • Bem-sucedidas: {len(success)}")
            
            if finished:
                success_rate = (len(success) / len(finished)) * 100
                print(f"   • Taxa de sucesso: {success_rate:.1f}%")
        
        print("\n" + "=" * 60)
        print("✅ TODOS OS TESTES PASSARAM!")
        print("=" * 60)
        print("\n📁 Dados salvos em: n8n-tuning/data/metrics/")
        print("\n💡 Próximos passos:")
        print("   1. Analisar workflows com: python scripts/workflow_analyzer.py")
        print("   2. Ver relatórios em: n8n-tuning/reports/")
        print("   3. Consultar docs/ANALYSIS_GUIDE.md para análise detalhada")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro durante os testes: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TESTE DE CONEXÃO N8N API")
    print("=" * 60)
    print()
    
    success = test_n8n_connection()
    
    sys.exit(0 if success else 1)
