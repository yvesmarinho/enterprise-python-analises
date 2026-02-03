#!/usr/bin/env python3
"""
Script para investigar métricas atômicas por node no banco PostgreSQL do N8N
Conecta diretamente no banco para inspecionar estrutura das tabelas de execução
"""

import psycopg2
import json
import sys
from pathlib import Path
from typing import Dict

# Adicionar o diretório scripts ao path
sys.path.insert(0, str(Path(__file__).parent))

from credentials_helper import CredentialsManager


def investigate_database_structure():
    """Investiga estrutura do banco de dados do N8N para encontrar métricas por node"""
    
    creds = CredentialsManager()
    pg_config = creds.get_postgresql_config()
    
    try:
        # Conectar ao banco
        print("🔌 Conectando ao PostgreSQL...")
        conn = psycopg2.connect(
            host=pg_config['host'],
            port=pg_config['port'],
            database=pg_config['database'],
            user=pg_config['user'],
            password=pg_config['password']
        )
        cur = conn.cursor()
        print("✅ Conectado ao banco de dados")
        
        # Listar todas as tabelas
        print("\n" + "="*60)
        print("TABELAS DISPONÍVEIS NO BANCO")
        print("="*60)
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = cur.fetchall()
        for table in tables:
            print(f"  📊 {table[0]}")
        
        # Investigar estrutura da tabela execution_entity
        print("\n" + "="*60)
        print("ESTRUTURA DA TABELA: execution_entity")
        print("="*60)
        cur.execute("""
            SELECT 
                column_name, 
                data_type, 
                character_maximum_length,
                is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'execution_entity'
            ORDER BY ordinal_position
        """)
        columns = cur.fetchall()
        for col in columns:
            nullable = "NULL" if col[3] == "YES" else "NOT NULL"
            max_len = f"({col[2]})" if col[2] else ""
            print(f"  📌 {col[0]:<30} {col[1]}{max_len:<20} {nullable}")
        
        # Investigar estrutura da tabela execution_data
        print("\n" + "="*60)
        print("ESTRUTURA DA TABELA: execution_data")
        print("="*60)
        cur.execute("""
            SELECT 
                column_name, 
                data_type, 
                character_maximum_length,
                is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'execution_data'
            ORDER BY ordinal_position
        """)
        columns = cur.fetchall()
        for col in columns:
            nullable = "NULL" if col[3] == "YES" else "NOT NULL"
            max_len = f"({col[2]})" if col[2] else ""
            print(f"  📌 {col[0]:<30} {col[1]}{max_len:<20} {nullable}")
        
        # Buscar uma execução de exemplo para ver os dados
        print("\n" + "="*60)
        print("EXEMPLO DE EXECUÇÃO (1 registro recente)")
        print("="*60)
        cur.execute("""
            SELECT 
                e.id,
                e."workflowId",
                e.status,
                e.mode,
                e."startedAt",
                e."stoppedAt",
                EXTRACT(EPOCH FROM (e."stoppedAt" - e."startedAt")) * 1000 as duration_ms,
                ed.data
            FROM execution_entity e
            LEFT JOIN execution_data ed ON e.id = ed."executionId"
            WHERE e.status = 'success'
              AND e."stoppedAt" IS NOT NULL
              AND ed.data IS NOT NULL
            ORDER BY e."startedAt" DESC
            LIMIT 1
        """)
        
        execution = cur.fetchone()
        if execution:
            exec_id, workflow_id, status, mode, started, stopped, duration, data = execution
            
            print(f"ID: {exec_id}")
            print(f"Workflow ID: {workflow_id}")
            print(f"Status: {status}")
            print(f"Mode: {mode}")
            print(f"Started: {started}")
            print(f"Stopped: {stopped}")
            print(f"Duration: {duration:.2f}ms")
            print(f"\nTipo do campo 'data': {type(data)}")
            
            # Se data for JSON, inspecionar estrutura
            if data:
                if isinstance(data, str):
                    data_list = json.loads(data)
                else:
                    data_list = data
                
                print(f"\n📊 Tipo de 'data' após parse: {type(data_list)}")
                
                # Salvar lista completa ANTES de processar
                output_file = Path(__file__).parent.parent / 'data' / 'logs' / 'execution_db_sample_full.json'
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_file, 'w') as f:
                    json.dump(data_list, f, indent=2, default=str)
                
                print(f"💾 Lista completa salva em: {output_file}")
                
                if isinstance(data_list, list):
                    print(f"📊 'data' é uma lista com {len(data_list)} elementos")
                    if not data_list:
                        print("⚠️  Lista vazia")
                        return
                    
                    # Primeiro elemento contém os índices
                    first = data_list[0]
                    print(f"📊 Tipo do primeiro elemento: {type(first)}")
                    if isinstance(first, dict):
                        print(f"📊 Keys no primeiro elemento: {list(first.keys())}")
                        
                        # O N8N usa uma estrutura especial onde os valores são índices da lista
                        # Ex: {"resultData": "2"} significa data_list[2] contém o resultData
                        if 'resultData' in first:
                            result_idx = first['resultData']
                            print(f"\n📊 Índice do resultData: {result_idx}")
                            
                            if isinstance(result_idx, str) and result_idx.isdigit():
                                result_idx = int(result_idx)
                                if result_idx < len(data_list):
                                    result_data = data_list[result_idx]
                                    print(f"📊 Tipo do resultData (elemento {result_idx}): {type(result_data)}")
                                    
                                    if isinstance(result_data, dict):
                                        print(f"📊 Keys em resultData: {list(result_data.keys())}")
                                        data = {"index_map": first, "resultData": result_data}
                                    else:
                                        print(f"⚠️  resultData não é dict: {result_data}")
                                        data = None
                                else:
                                    print(f"⚠️  Índice {result_idx} fora do range da lista")
                                    data = None
                            else:
                                print(f"⚠️  Valor de resultData não é um índice válido: {result_idx}")
                                data = None
                        else:
                            print("⚠️  Key 'resultData' não encontrada")
                            data = None
                    else:
                        print(f"⚠️  Primeiro elemento não é um dict: {first}")
                        data = None
                elif isinstance(data_list, dict):
                    print(f"📊 Keys em 'data': {list(data_list.keys())}")
                    data = data_list
                else:
                    print(f"⚠️  Tipo inesperado de 'data': {type(data_list)}")
                    data = None
                
                if not data:
                    print("\n⚠️  Não foi possível extrair estrutura de dados")
                    return
                
                print(f"\n📊 Analisando estrutura processada de 'data'...")
                print(f"Keys disponíveis: {list(data.keys())}")
                
                if 'resultData' in data:
                    result_data = data['resultData']
                    if isinstance(result_data, str):
                        result_data = json.loads(result_data)
                    print(f"Keys em 'resultData': {list(result_data.keys())}")
                    
                    if 'runData' in result_data:
                        run_data = result_data['runData']
                        print(f"\n🎯 NODES EXECUTADOS (runData): {len(run_data)} nodes")
                        
                        total_node_time = 0
                        node_metrics = []
                        
                        for node_name, node_executions in run_data.items():
                            if not node_executions:
                                continue
                            
                            # Cada node pode ter múltiplas execuções
                            for node_exec in node_executions:
                                if 'executionTime' in node_exec:
                                    exec_time = node_exec['executionTime']
                                    start_time = node_exec.get('startTime', 0)
                                    
                                    node_metrics.append({
                                        'node': node_name,
                                        'execution_time': exec_time,
                                        'start_time': start_time
                                    })
                                    total_node_time += exec_time
                        
                        if node_metrics:
                            print(f"\n⏱️  Tempo total dos nodes: {total_node_time}ms")
                            print(f"⏱️  Duração total da execução: {duration:.2f}ms")
                            print(f"📊 Overhead (rede/coordenação): {duration - total_node_time:.2f}ms")
                            
                            # Ordenar por tempo de execução
                            node_metrics.sort(key=lambda x: x['execution_time'], reverse=True)
                            
                            print(f"\n🔥 TOP NODES MAIS LENTOS NESTA EXECUÇÃO:")
                            for idx, metric in enumerate(node_metrics[:10], 1):
                                percentage = (metric['execution_time'] / total_node_time * 100) if total_node_time > 0 else 0
                                print(f"   {idx}. {metric['node']}: {metric['execution_time']}ms ({percentage:.1f}%)")
                            
                            print(f"\n✅ CONCLUSÃO:")
                            print(f"   ✅ O banco PostgreSQL contém métricas atômicas por node!")
                            print(f"   ✅ Campo 'data' -> 'resultData' -> 'runData' contém performance detalhada")
                            print(f"   ✅ Cada node tem 'executionTime' e 'startTime'")
                            print(f"   💡 Possível criar dashboard com gargalos por componente/node")
                        else:
                            print("\n⚠️  Não foi possível extrair métricas de tempo dos nodes")
                    else:
                        print("\n⚠️  Campo 'runData' não encontrado em 'resultData'")
                else:
                    print("\n⚠️  Campo 'resultData' não encontrado em 'data'")
                
                # Salvar exemplo completo
                output_file = Path(__file__).parent.parent / 'data' / 'logs' / 'execution_db_sample.json'
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_file, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                
                print(f"\n💾 Exemplo completo salvo em: {output_file}")
        else:
            print("⚠️  Nenhuma execução encontrada com dados")
        
        # Contar quantas execuções têm dados detalhados
        print("\n" + "="*60)
        print("ESTATÍSTICAS DE DADOS DISPONÍVEIS")
        print("="*60)
        cur.execute("""
            SELECT 
                COUNT(*) as total_executions,
                SUM(CASE WHEN ed.data IS NOT NULL THEN 1 ELSE 0 END) as with_data,
                SUM(CASE WHEN ed.data IS NULL THEN 1 ELSE 0 END) as without_data
            FROM execution_entity e
            LEFT JOIN execution_data ed ON e.id = ed."executionId"
            WHERE e."stoppedAt" > NOW() - INTERVAL '7 days'
        """)
        stats = cur.fetchone()
        print(f"📊 Últimos 7 dias:")
        print(f"   Total de execuções: {stats[0]}")
        print(f"   Com dados detalhados: {stats[1]} ({stats[1]/stats[0]*100:.1f}%)")
        print(f"   Sem dados: {stats[2]} ({stats[2]/stats[0]*100:.1f}%)")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    investigate_database_structure()
