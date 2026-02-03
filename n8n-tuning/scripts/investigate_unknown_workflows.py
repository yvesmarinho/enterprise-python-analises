#!/usr/bin/env python3
"""
Investiga workflows "unknown" para identificar sua origem
"""

import json
import requests
from pathlib import Path
from typing import Dict, List

def load_credentials() -> Dict:
    """Carrega credenciais do N8N"""
    creds_file = Path(__file__).parent.parent / '.secrets' / 'credentials.json'
    with open(creds_file) as f:
        return json.load(f)['n8n']

def investigate_unknown_workflows():
    """Investiga execuções com workflow 'unknown'"""
    
    print("=" * 80)
    print("🔍 INVESTIGAÇÃO DE WORKFLOWS 'UNKNOWN'")
    print("=" * 80)
    print()
    
    # Carregar credenciais
    n8n_config = load_credentials()
    headers = {'X-N8N-API-KEY': n8n_config['api_key']}
    
    # Coletar todos os workflows
    print("📊 Coletando lista de workflows...")
    workflows_resp = requests.get(
        f"{n8n_config['url']}/api/v1/workflows",
        headers=headers
    )
    workflows = workflows_resp.json()['data']
    workflow_map = {wf['id']: wf['name'] for wf in workflows}
    print(f"✅ {len(workflows)} workflows encontrados")
    print()
    
    # Coletar execuções
    print("📊 Coletando execuções (últimas 1000)...")
    all_executions = []
    cursor = None
    
    while len(all_executions) < 1000:
        params = {"limit": 250}
        if cursor:
            params["cursor"] = cursor
        
        resp = requests.get(
            f"{n8n_config['url']}/api/v1/executions",
            headers=headers,
            params=params
        )
        
        data = resp.json()
        page_execs = data.get('data', [])
        if not page_execs:
            break
        
        all_executions.extend(page_execs)
        cursor = data.get('nextCursor')
        if not cursor:
            break
    
    print(f"✅ {len(all_executions)} execuções coletadas")
    print()
    
    # Analisar execuções "unknown"
    print("=" * 80)
    print("🔎 ANÁLISE DE EXECUÇÕES 'UNKNOWN'")
    print("=" * 80)
    print()
    
    unknown_workflows = {}
    
    for execution in all_executions:
        workflow_id = execution.get('workflowId')
        
        # Verificar se o workflow existe na lista atual
        if workflow_id and workflow_id not in workflow_map:
            # Este é um workflow deletado ou órfão
            if workflow_id not in unknown_workflows:
                unknown_workflows[workflow_id] = {
                    'id': workflow_id,
                    'executions': [],
                    'last_execution_date': None,
                    'status': 'DELETED/ORPHAN'
                }
            
            unknown_workflows[workflow_id]['executions'].append({
                'id': execution.get('id'),
                'finished': execution.get('finished'),
                'startedAt': execution.get('startedAt'),
                'stoppedAt': execution.get('stoppedAt'),
                'mode': execution.get('mode'),
                'status': execution.get('status')
            })
            
            # Atualizar última execução
            started_at = execution.get('startedAt')
            if started_at:
                if not unknown_workflows[workflow_id]['last_execution_date'] or \
                   started_at > unknown_workflows[workflow_id]['last_execution_date']:
                    unknown_workflows[workflow_id]['last_execution_date'] = started_at
    
    # Exibir resultados
    if not unknown_workflows:
        print("✅ Nenhuma execução 'unknown' encontrada!")
        print("   Todos os workflows foram identificados corretamente.")
    else:
        print(f"⚠️  {len(unknown_workflows)} workflow(s) 'unknown' identificado(s)")
        print()
        
        for wf_id, info in unknown_workflows.items():
            print(f"📍 Workflow ID: {wf_id}")
            print(f"   Status: {info['status']}")
            print(f"   Execuções encontradas: {len(info['executions'])}")
            print(f"   Última execução: {info['last_execution_date']}")
            print()
            
            # Tentar obter informações do workflow deletado
            print(f"   🔍 Tentando recuperar informações...")
            try:
                wf_resp = requests.get(
                    f"{n8n_config['url']}/api/v1/workflows/{wf_id}",
                    headers=headers
                )
                
                if wf_resp.status_code == 200:
                    wf_data = wf_resp.json()
                    print(f"   ✅ Workflow encontrado:")
                    print(f"      Nome: {wf_data.get('name', 'N/A')}")
                    print(f"      Ativo: {wf_data.get('active', False)}")
                    print(f"      Tags: {wf_data.get('tags', [])}")
                elif wf_resp.status_code == 404:
                    print(f"   ❌ Workflow foi DELETADO")
                else:
                    print(f"   ⚠️  Erro {wf_resp.status_code}: {wf_resp.text[:100]}")
            except Exception as e:
                print(f"   ❌ Erro ao consultar: {e}")
            
            print()
            print(f"   📋 Últimas 3 execuções:")
            for i, exec_info in enumerate(info['executions'][:3], 1):
                print(f"      {i}. ID: {exec_info['id']} | "
                      f"Status: {exec_info.get('status', 'N/A')} | "
                      f"Started: {exec_info['startedAt']}")
            
            print()
            print("-" * 80)
            print()
    
    # Recomendações
    print("=" * 80)
    print("💡 RECOMENDAÇÕES")
    print("=" * 80)
    print()
    
    if unknown_workflows:
        print("1. 🧹 Limpar execuções antigas:")
        print("   - Workflows deletados deixam execuções órfãs")
        print("   - Considere limpar execuções com mais de X dias")
        print()
        print("2. 🔄 Atualizar o exporter:")
        print("   - Modificar para buscar nome do workflow diretamente da execução")
        print("   - Adicionar fallback para workflows deletados")
        print()
        print("3. 📊 Excluir da análise:")
        print("   - Filtrar execuções de workflows inexistentes")
        print("   - Focar apenas em workflows ativos")
    else:
        print("✅ Não há workflows 'unknown' no momento!")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    try:
        investigate_unknown_workflows()
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
