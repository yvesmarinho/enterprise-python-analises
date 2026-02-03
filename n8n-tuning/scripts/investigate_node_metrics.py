#!/usr/bin/env python3
"""
Script para investigar métricas atômicas por node/componente do N8N
Verifica se as execuções contêm dados detalhados de performance por node
"""

import requests
import json
import sys
from pathlib import Path

# Adicionar o diretório scripts ao path
sys.path.insert(0, str(Path(__file__).parent))

from credentials_helper import CredentialsManager


def investigate_execution_structure():
    """Investiga a estrutura de uma execução para identificar métricas por node"""
    
    creds = CredentialsManager()
    n8n_config = creds.get_n8n_config()
    
    headers = {
        'X-N8N-API-KEY': n8n_config['api_key'],
        'Accept': 'application/json'
    }
    
    # Pegar uma execução recente com todos os dados detalhados
    print("🔍 Buscando execução recente com dados detalhados...")
    
    # Primeiro buscar sem includeData para ver o que está disponível
    response = requests.get(
        f'{n8n_config["url"]}/api/v1/executions',
        headers=headers,
        params={'limit': 1}
    )
    
    if response.status_code != 200:
        print(f'❌ Erro ao buscar execuções: {response.status_code}')
        print(f'Response: {response.text}')
        return
    
    data = response.json()
    if not data.get('data'):
        print('❌ Nenhuma execução encontrada')
        return
    
    execution_id = data['data'][0]['id']
    print(f"📋 Encontrada execução ID: {execution_id}")
    
    # Buscar execução específica com dados detalhados
    print(f"🔍 Buscando detalhes da execução {execution_id}...")
    response = requests.get(
        f'{n8n_config["url"]}/api/v1/executions/{execution_id}',
        headers=headers
    )
    
    if response.status_code != 200:
        print(f'❌ Erro ao buscar execução {execution_id}: {response.status_code}')
        print(f'Response: {response.text}')
        return
    
    execution = response.json()
    
    print('\n' + '='*60)
    print('ESTRUTURA GERAL DA EXECUÇÃO')
    print('='*60)
    print(f"ID: {execution.get('id')}")
    print(f"Workflow ID: {execution.get('workflowId')}")
    print(f"Status: {execution.get('status')}")
    print(f"Modo: {execution.get('mode')}")
    print(f"Started: {execution.get('startedAt')}")
    print(f"Stopped: {execution.get('stoppedAt')}")
    print(f"\nCampos disponíveis no root: {list(execution.keys())}")
    
    # Verificar se há dados de execução detalhados
    if 'data' not in execution or not execution['data']:
        print('\n⚠️  Campo "data" não disponível - adicione ?includeData=true')
        return
    
    exec_data = execution['data']
    print('\n' + '='*60)
    print('DADOS DE EXECUÇÃO (execution.data)')
    print('='*60)
    print(f"Keys em execution.data: {list(exec_data.keys())}")
    
    if 'resultData' not in exec_data:
        print('\n⚠️  Campo "resultData" não disponível')
        return
    
    result_data = exec_data['resultData']
    print(f"\nKeys em resultData: {list(result_data.keys())}")
    
    if 'runData' not in result_data:
        print('\n⚠️  Campo "runData" não disponível')
        return
    
    run_data = result_data['runData']
    
    print('\n' + '='*60)
    print('MÉTRICAS POR NODE (runData)')
    print('='*60)
    print(f"\n✅ Total de nodes executados: {len(run_data)}")
    
    total_execution_time = 0
    node_metrics = []
    
    for node_name, node_runs in run_data.items():
        print(f"\n📌 Node: {node_name}")
        print(f"   Número de execuções do node: {len(node_runs)}")
        
        if not node_runs:
            continue
            
        first_run = node_runs[0]
        print(f"   Keys disponíveis: {list(first_run.keys())}")
        
        # Coletar métricas de tempo
        if 'startTime' in first_run:
            print(f"   ⏱️  startTime: {first_run.get('startTime')}")
        
        if 'executionTime' in first_run:
            exec_time = first_run.get('executionTime')
            print(f"   ⏱️  executionTime: {exec_time}ms")
            total_execution_time += exec_time
            
            node_metrics.append({
                'node': node_name,
                'execution_time': exec_time,
                'runs': len(node_runs)
            })
        
        # Verificar outros dados úteis
        if 'data' in first_run:
            data_info = first_run['data']
            if 'main' in data_info:
                items_count = len(data_info['main'][0]) if data_info['main'] else 0
                print(f"   📊 Items processados: {items_count}")
    
    # Análise consolidada
    if node_metrics:
        print('\n' + '='*60)
        print('ANÁLISE CONSOLIDADA')
        print('='*60)
        print(f"\n⏱️  Tempo total de execução (soma dos nodes): {total_execution_time}ms")
        
        # Ordenar por tempo de execução
        node_metrics.sort(key=lambda x: x['execution_time'], reverse=True)
        
        print(f"\n🔥 TOP 5 NODES MAIS LENTOS:")
        for idx, metric in enumerate(node_metrics[:5], 1):
            percentage = (metric['execution_time'] / total_execution_time * 100) if total_execution_time > 0 else 0
            print(f"   {idx}. {metric['node']}: {metric['execution_time']}ms ({percentage:.1f}%)")
        
        print(f"\n💡 CONCLUSÃO:")
        print(f"   ✅ A API do N8N fornece métricas atômicas por node!")
        print(f"   ✅ Campo 'executionTime' disponível para cada node")
        print(f"   ✅ Possível identificar gargalos específicos no workflow")
        print(f"   📌 Endpoint: /api/v1/executions?includeData=true")
    else:
        print('\n⚠️  Não foi possível coletar métricas de tempo dos nodes')
    
    # Salvar exemplo completo para análise
    output_file = Path(__file__).parent.parent / 'data' / 'logs' / 'execution_sample.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(execution, f, indent=2)
    
    print(f"\n💾 Exemplo completo salvo em: {output_file}")


if __name__ == '__main__':
    investigate_execution_structure()
