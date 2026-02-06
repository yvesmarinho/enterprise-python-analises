#!/usr/bin/env python3
"""
N8N Node Metrics Exporter para Victoria Metrics
Coleta métricas atômicas por node/componente do banco PostgreSQL do N8N
"""

import psycopg2
import json
import time
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

# Adicionar o diretório scripts ao path
sys.path.insert(0, str(Path(__file__).parent))

from credentials_helper import CredentialsManager


class N8NNodeMetricsExporter:
    """Exportador de métricas atômicas por node do N8N"""
    
    def __init__(self, pg_config: Dict, vm_url: str = "http://localhost:8428",
                 prometheus_pushgateway: str = None,
                 prometheus_job: str = "n8n_node_metrics",
                 backend: str = "victoria_metrics"):
        """
        Inicializa o exportador
        
        Args:
            pg_config: Configuração do PostgreSQL
            vm_url: URL do Victoria Metrics
            prometheus_pushgateway: URL do Prometheus Pushgateway
            prometheus_job: Nome do job no Prometheus
            backend: 'victoria_metrics' ou 'prometheus'
        """
        self.pg_config = pg_config
        self.vm_url = vm_url.rstrip('/')
        self.prometheus_pushgateway = prometheus_pushgateway.rstrip('/') if prometheus_pushgateway else None
        self.prometheus_job = prometheus_job
        self.backend = backend
        self.conn = None
    
    def connect_db(self):
        """Conecta ao banco PostgreSQL"""
        if self.conn:
            return
        
        print("🔌 Conectando ao PostgreSQL...")
        self.conn = psycopg2.connect(
            host=self.pg_config['host'],
            port=self.pg_config['port'],
            database=self.pg_config['database'],
            user=self.pg_config['user'],
            password=self.pg_config['password']
        )
        print("✅ Conectado ao banco de dados")
    
    def parse_execution_data(self, data_json: str) -> Dict:
        """
        Parseia o campo 'data' da tabela execution_data
        
        O N8N usa uma estrutura compactada onde:
        - data é uma lista
        - Elemento [0] contém mapa de índices
        - Outros elementos são referenciados pelos índices
        
        Args:
            data_json: String JSON do campo data
            
        Returns:
            Dict com runData parseado ou None
        """
        try:
            data_list = json.loads(data_json)
            
            if not isinstance(data_list, list) or len(data_list) == 0:
                return None
            
            # Elemento 0 tem o mapa de índices
            index_map = data_list[0]
            if not isinstance(index_map, dict) or 'resultData' not in index_map:
                return None
            
            # Buscar resultData
            result_idx = index_map['resultData']
            if not isinstance(result_idx, str) or not result_idx.isdigit():
                return None
            
            result_idx = int(result_idx)
            if result_idx >= len(data_list):
                return None
            
            result_data = data_list[result_idx]
            if not isinstance(result_data, dict) or 'runData' not in result_data:
                return None
            
            # Buscar runData
            run_data_idx = result_data['runData']
            if not isinstance(run_data_idx, str) or not run_data_idx.isdigit():
                return None
            
            run_data_idx = int(run_data_idx)
            if run_data_idx >= len(data_list):
                return None
            
            run_data = data_list[run_data_idx]
            if not isinstance(run_data, dict):
                return None
            
            # Desempacotar nodes
            node_metrics = {}
            for node_name, node_idx in run_data.items():
                if not isinstance(node_idx, str) or not node_idx.isdigit():
                    continue
                
                node_idx = int(node_idx)
                if node_idx >= len(data_list):
                    continue
                
                node_executions = data_list[node_idx]
                if not isinstance(node_executions, list):
                    continue
                
                # Processar execuções do node
                node_times = []
                for exec_ref in node_executions:
                    # Pode ser índice ou dados diretos
                    if isinstance(exec_ref, str) and exec_ref.isdigit():
                        exec_idx = int(exec_ref)
                        if exec_idx < len(data_list):
                            exec_data = data_list[exec_idx]
                        else:
                            continue
                    else:
                        exec_data = exec_ref
                    
                    if isinstance(exec_data, dict):
                        exec_time = exec_data.get('executionTime')
                        if exec_time is not None:
                            node_times.append({
                                'execution_time': exec_time,
                                'start_time': exec_data.get('startTime'),
                                'status': exec_data.get('executionStatus', 'success')
                            })
                
                if node_times:
                    node_metrics[node_name] = node_times
            
            return node_metrics if node_metrics else None
            
        except Exception as e:
            # Silenciosamente ignorar erros de parse
            return None
    
    def collect_node_metrics(self, hours_back: int = 24, limit: int = 1000) -> List[Dict]:
        """
        Coleta métricas de nodes das últimas N horas
        
        Args:
            hours_back: Quantas horas atrás buscar
            limit: Máximo de execuções a processar
            
        Returns:
            Lista de dicts com métricas por node
        """
        self.connect_db()
        cur = self.conn.cursor()
        
        print(f"📊 Coletando métricas de nodes (últimas {hours_back}h, limite {limit})...")
        
        # Buscar execuções recentes com dados
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        cur.execute("""
            SELECT 
                e.id,
                e."workflowId",
                w.name as workflow_name,
                e.status,
                e."startedAt",
                e."stoppedAt",
                EXTRACT(EPOCH FROM (e."stoppedAt" - e."startedAt")) * 1000 as duration_ms,
                ed.data
            FROM execution_entity e
            INNER JOIN workflow_entity w ON e."workflowId" = w.id
            LEFT JOIN execution_data ed ON e.id = ed."executionId"
            WHERE e.status = 'success'
              AND e."stoppedAt" IS NOT NULL
              AND e."startedAt" > %s
              AND ed.data IS NOT NULL
            ORDER BY e."startedAt" DESC
            LIMIT %s
        """, (cutoff_time, limit))
        
        results = []
        processed = 0
        with_node_data = 0
        
        for row in cur.fetchall():
            exec_id, wf_id, wf_name, status, started, stopped, duration, data_json = row
            processed += 1
            
            if processed % 100 == 0:
                print(f"   📄 Processadas {processed} execuções...")
            
            # Parsear dados do node
            node_metrics = self.parse_execution_data(data_json)
            
            if node_metrics:
                with_node_data += 1
                results.append({
                    'execution_id': exec_id,
                    'workflow_id': wf_id,
                    'workflow_name': wf_name,
                    'started_at': started,
                    'stopped_at': stopped,
                    'total_duration': duration,
                    'nodes': node_metrics
                })
        
        cur.close()
        
        print(f"✅ {processed} execuções processadas")
        print(f"✅ {with_node_data} com dados de nodes ({with_node_data/processed*100:.1f}%)")
        
        return results
    
    def aggregate_node_metrics(self, executions: List[Dict]) -> Dict:
        """
        Agrega métricas por workflow e por node
        
        Returns:
            Dict com métricas agregadas
        """
        print("📈 Agregando métricas por node...")
        
        # Estrutura: workflow_name -> node_name -> [execution_times]
        workflow_nodes = defaultdict(lambda: defaultdict(list))
        
        # Estrutura: node_type -> [execution_times] (para análise por tipo)
        node_types = defaultdict(list)
        
        for exec_data in executions:
            wf_name = exec_data['workflow_name']
            
            for node_name, node_execs in exec_data['nodes'].items():
                for node_exec in node_execs:
                    exec_time = node_exec['execution_time']
                    workflow_nodes[wf_name][node_name].append(exec_time)
                    
                    # Tentar identificar tipo de node (heurística simples)
                    node_type = self._guess_node_type(node_name)
                    node_types[node_type].append(exec_time)
        
        # Calcular estatísticas
        aggregated = {
            'by_workflow_and_node': {},
            'by_node_type': {},
            'top_slowest_nodes': []
        }
        
        # Por workflow e node
        all_nodes_stats = []
        
        for wf_name, nodes in workflow_nodes.items():
            if wf_name not in aggregated['by_workflow_and_node']:
                aggregated['by_workflow_and_node'][wf_name] = {}
            
            for node_name, times in nodes.items():
                stats = {
                    'count': len(times),
                    'avg': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times),
                    'total': sum(times)
                }
                aggregated['by_workflow_and_node'][wf_name][node_name] = stats
                
                # Para ranking global
                all_nodes_stats.append({
                    'workflow': wf_name,
                    'node': node_name,
                    **stats
                })
        
        # Por tipo de node
        for node_type, times in node_types.items():
            aggregated['by_node_type'][node_type] = {
                'count': len(times),
                'avg': sum(times) / len(times) if times else 0,
                'total': sum(times)
            }
        
        # Top nodes mais lentos (por tempo médio)
        all_nodes_stats.sort(key=lambda x: x['avg'], reverse=True)
        aggregated['top_slowest_nodes'] = all_nodes_stats[:20]
        
        print(f"✅ {len(all_nodes_stats)} nodes únicos analisados")
        
        return aggregated
    
    def _guess_node_type(self, node_name: str) -> str:
        """Tenta identificar o tipo de node baseado no nome"""
        node_name_lower = node_name.lower()
        
        if 'http' in node_name_lower or 'request' in node_name_lower:
            return 'HTTP Request'
        elif 'postgres' in node_name_lower or 'mysql' in node_name_lower or 'database' in node_name_lower:
            return 'Database'
        elif 'code' in node_name_lower or 'function' in node_name_lower:
            return 'Code'
        elif 'set' in node_name_lower or 'item' in node_name_lower:
            return 'Data Transform'
        elif 'schedule' in node_name_lower or 'trigger' in node_name_lower or 'webhook' in node_name_lower:
            return 'Trigger'
        elif 'if' in node_name_lower or 'switch' in node_name_lower:
            return 'Logic'
        else:
            return 'Other'
    
    def generate_prometheus_metrics(self, aggregated: Dict) -> str:
        """Gera métricas em formato Prometheus"""
        lines = []
        timestamp = int(time.time() * 1000)
        
        # Métricas por workflow e node
        lines.append("# HELP n8n_node_execution_time_ms Average execution time per node in milliseconds")
        lines.append("# TYPE n8n_node_execution_time_ms gauge")
        
        for wf_name, nodes in aggregated['by_workflow_and_node'].items():
            wf_name_clean = wf_name.replace('"', '\\"').replace('\n', ' ')
            for node_name, stats in nodes.items():
                node_name_clean = node_name.replace('"', '\\"').replace('\n', ' ')
                lines.append(
                    f'n8n_node_execution_time_ms{{workflow_name="{wf_name_clean}",node_name="{node_name_clean}"}} '
                    f'{stats["avg"]:.2f} {timestamp}'
                )
        
        # Contagem de execuções por node
        lines.append("# HELP n8n_node_executions_total Total executions per node")
        lines.append("# TYPE n8n_node_executions_total gauge")
        
        for wf_name, nodes in aggregated['by_workflow_and_node'].items():
            wf_name_clean = wf_name.replace('"', '\\"').replace('\n', ' ')
            for node_name, stats in nodes.items():
                node_name_clean = node_name.replace('"', '\\"').replace('\n', ' ')
                lines.append(
                    f'n8n_node_executions_total{{workflow_name="{wf_name_clean}",node_name="{node_name_clean}"}} '
                    f'{stats["count"]} {timestamp}'
                )
        
        # Tempo máximo por node
        lines.append("# HELP n8n_node_execution_time_max_ms Maximum execution time per node in milliseconds")
        lines.append("# TYPE n8n_node_execution_time_max_ms gauge")
        
        for wf_name, nodes in aggregated['by_workflow_and_node'].items():
            wf_name_clean = wf_name.replace('"', '\\"').replace('\n', ' ')
            for node_name, stats in nodes.items():
                node_name_clean = node_name.replace('"', '\\"').replace('\n', ' ')
                lines.append(
                    f'n8n_node_execution_time_max_ms{{workflow_name="{wf_name_clean}",node_name="{node_name_clean}"}} '
                    f'{stats["max"]:.2f} {timestamp}'
                )
        
        # Métricas por tipo de node
        lines.append("# HELP n8n_node_type_avg_time_ms Average execution time by node type")
        lines.append("# TYPE n8n_node_type_avg_time_ms gauge")
        
        for node_type, stats in aggregated['by_node_type'].items():
            node_type_clean = node_type.replace('"', '\\"')
            lines.append(
                f'n8n_node_type_avg_time_ms{{node_type="{node_type_clean}"}} '
                f'{stats["avg"]:.2f} {timestamp}'
            )
        
        lines.append("# HELP n8n_node_type_executions_total Total executions by node type")
        lines.append("# TYPE n8n_node_type_executions_total gauge")
        
        for node_type, stats in aggregated['by_node_type'].items():
            node_type_clean = node_type.replace('"', '\\"')
            lines.append(
                f'n8n_node_type_executions_total{{node_type="{node_type_clean}"}} '
                f'{stats["count"]} {timestamp}'
            )
        
        return '\n'.join(lines) + '\n'
    
    def push_to_victoria_metrics(self, metrics: str) -> bool:
        """Envia métricas para Victoria Metrics"""
        import requests
        
        url = f"{self.vm_url}/api/v1/import/prometheus"
        
        try:
            response = requests.post(url, data=metrics, timeout=10)
            response.raise_for_status()
            print("✅ Métricas enviadas para Victoria Metrics")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao enviar métricas: {e}")
            return False
    
    def push_to_prometheus_pushgateway(self, metrics: str) -> bool:
        """Envia métricas para Prometheus Pushgateway"""
        import requests
        
        if not self.prometheus_pushgateway:
            print("❌ URL do Prometheus Pushgateway não configurado")
            return False
        
        url = f"{self.prometheus_pushgateway}/metrics/job/{self.prometheus_job}"
        
        try:
            response = requests.post(url, data=metrics, timeout=10)
            response.raise_for_status()
            print(f"✅ Métricas enviadas para Prometheus Pushgateway")
            print(f"   Job: {self.prometheus_job}")
            print(f"   URL: {self.prometheus_pushgateway}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao enviar métricas para Prometheus: {e}")
            print(f"   Verifique se o Pushgateway está rodando em: {self.prometheus_pushgateway}")
            return False
    
    def push_metrics(self, metrics: str) -> bool:
        """Envia métricas para o backend configurado"""
        if self.backend == "prometheus":
            return self.push_to_prometheus_pushgateway(metrics)
        else:
            return self.push_to_victoria_metrics(metrics)
    
    def collect_and_push(self, hours_back: int = 24, limit: int = 1000) -> bool:
        """Pipeline completo de coleta e envio"""
        print("=" * 60)
        print("🚀 N8N Node Metrics Exporter")
        print("=" * 60)
        print()
        
        try:
            # Coletar dados
            executions = self.collect_node_metrics(hours_back=hours_back, limit=limit)
            
            if not executions:
                print("⚠️  Nenhuma execução com dados de nodes encontrada")
                return False
            
            print()
            
            # Agregar
            aggregated = self.aggregate_node_metrics(executions)
            
            print()
            print("📊 Top 10 nodes mais lentos (tempo médio):")
            for idx, node in enumerate(aggregated['top_slowest_nodes'][:10], 1):
                print(f"   {idx}. {node['node']} ({node['workflow']}): {node['avg']:.2f}ms (n={node['count']})")
            
            print()
            print("📈 Gerando métricas Prometheus...")
            metrics = self.generate_prometheus_metrics(aggregated)
            
            lines = metrics.split('\n')
            metric_lines = [l for l in lines if l and not l.startswith('#')]
            print(f"✅ {len(metric_lines)} métricas geradas")
            
            print()
            print("📤 Enviando métricas...")
            success = self.push_metrics(metrics)
            
            print()
            print("=" * 60)
            if success:
                print("✅ Coleta e exportação concluídas!")
                print()
                print("🔍 Verificar métricas:")
                if self.backend == "prometheus":
                    print(f"   Prometheus Pushgateway: {self.prometheus_pushgateway}")
                    print(f"   Job name: {self.prometheus_job}")
                else:
                    print(f"   Victoria Metrics: {self.vm_url}")
                    print(f"   Grafana: http://localhost:3100")
            else:
                print("❌ Falha na exportação")
            print("=" * 60)
            
            return success
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if self.conn:
                self.conn.close()


def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='N8N Node Metrics Exporter')
    parser.add_argument('--backend', choices=['victoria_metrics', 'prometheus'], 
                        default='prometheus',
                        help='Backend para enviar métricas (default: prometheus)')
    parser.add_argument('--hours', type=int, default=6,
                        help='Horas atrás para coletar (default: 6)')
    parser.add_argument('--limit', type=int, default=500,
                        help='Número de execuções a processar (default: 500)')
    args = parser.parse_args()
    
    print("🔍 Carregando credenciais...")
    
    try:
        creds = CredentialsManager()
        pg_config = creds.get_postgresql_config()
        
        if not all(k in pg_config for k in ['host', 'port', 'database', 'user', 'password']):
            print("❌ Configuração PostgreSQL incompleta")
            sys.exit(1)
        
        print(f"✅ PostgreSQL: {pg_config['host']}:{pg_config['port']}/{pg_config['database']}")
        print(f"✅ Backend: {args.backend}")
        print()
        
        # Configurar backend
        if args.backend == "prometheus":
            prom_config = creds.get_prometheus_config()
            pushgateway_url = prom_config.get('pushgateway_url', 'http://wfdb01.vya.digital:9091')
            job_name = prom_config.get('job_name', 'n8n_node_metrics')
            
            print(f"✅ Prometheus Pushgateway: {pushgateway_url}")
            print(f"✅ Job name: {job_name}")
            print()
            
            exporter = N8NNodeMetricsExporter(
                pg_config=pg_config,
                prometheus_pushgateway=pushgateway_url,
                prometheus_job=job_name,
                backend="prometheus"
            )
        else:
            # Victoria Metrics
            exporter = N8NNodeMetricsExporter(
                pg_config=pg_config,
                vm_url="http://localhost:8428",
                backend="victoria_metrics"
            )
        
        # Coletar e exportar
        success = exporter.collect_and_push(hours_back=args.hours, limit=args.limit)
        
        sys.exit(0 if success else 1)
        
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
