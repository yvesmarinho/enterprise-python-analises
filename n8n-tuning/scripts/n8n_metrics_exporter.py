#!/usr/bin/env python3
"""
N8N Metrics Exporter para Victoria Metrics
Coleta métricas do N8N via API e exporta para Victoria Metrics em formato Prometheus
"""

import requests
import json
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

# Adicionar o diretório scripts ao path
sys.path.insert(0, str(Path(__file__).parent))

from credentials_helper import CredentialsManager


class N8NMetricsExporter:
    """Exportador de métricas do N8N para Victoria Metrics ou Prometheus"""
    
    def __init__(self, n8n_url: str, n8n_api_key: str, 
                 vm_url: str = "http://localhost:8428",
                 prometheus_pushgateway: str = None,
                 prometheus_job: str = "n8n_metrics",
                 backend: str = "victoria_metrics"):
        """
        Inicializa o exportador
        
        Args:
            n8n_url: URL do N8N
            n8n_api_key: API Key do N8N
            vm_url: URL do Victoria Metrics
            prometheus_pushgateway: URL do Prometheus Pushgateway (ex: http://wfdb01.vya.digital:9091)
            prometheus_job: Nome do job no Prometheus
            backend: 'victoria_metrics' ou 'prometheus'
        """
        self.n8n_url = n8n_url.rstrip('/')
        self.n8n_api_key = n8n_api_key
        self.vm_url = vm_url.rstrip('/')
        self.prometheus_pushgateway = prometheus_pushgateway.rstrip('/') if prometheus_pushgateway else None
        self.prometheus_job = prometheus_job
        self.backend = backend
        
        self.headers = {
            "X-N8N-API-KEY": n8n_api_key,
            "Accept": "application/json"
        }
    
    def _make_n8n_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Faz requisição à API do N8N"""
        url = f"{self.n8n_url}{endpoint}"
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao fazer requisição para {endpoint}: {e}")
            return {}
    
    def collect_workflows(self) -> List[Dict]:
        """Coleta informações de workflows"""
        print("📊 Coletando workflows...")
        data = self._make_n8n_request("/api/v1/workflows")
        workflows = data.get('data', [])
        print(f"✅ {len(workflows)} workflows coletados")
        return workflows
    
    def collect_executions(self, total_limit: int = 1000) -> List[Dict]:
        """
        Coleta execuções recentes com paginação
        
        Args:
            total_limit: Número máximo total de execuções a coletar
            
        Returns:
            Lista de execuções (API limita 250 por requisição)
        """
        print(f"📊 Coletando execuções (até {total_limit} registros)...")
        
        all_executions = []
        cursor = None
        max_per_page = 250  # Limite da API N8N
        
        while len(all_executions) < total_limit:
            # Calcular quantos registros pegar nesta página
            remaining = total_limit - len(all_executions)
            page_limit = min(remaining, max_per_page)
            
            # Montar parâmetros
            params = {"limit": page_limit}
            if cursor:
                params["cursor"] = cursor
            
            # Fazer requisição
            data = self._make_n8n_request("/api/v1/executions", params=params)
            page_executions = data.get('data', [])
            
            if not page_executions:
                break  # Sem mais dados
            
            all_executions.extend(page_executions)
            print(f"   📄 Página coletada: {len(page_executions)} registros (total: {len(all_executions)})")
            
            # Verificar se há próxima página
            cursor = data.get('nextCursor')
            if not cursor:
                break  # Não há mais páginas
        
        print(f"✅ {len(all_executions)} execuções coletadas")
        return all_executions
    
    def generate_prometheus_metrics(self, workflows: List[Dict], executions: List[Dict]) -> str:
        """
        Gera métricas em formato Prometheus
        
        Returns:
            String com métricas em formato Prometheus
        """
        lines = []
        timestamp = int(time.time() * 1000)  # Timestamp em milissegundos
        
        # Métricas de Workflows
        lines.append("# HELP n8n_workflows_total Total number of workflows")
        lines.append("# TYPE n8n_workflows_total gauge")
        lines.append(f"n8n_workflows_total {len(workflows)} {timestamp}")
        
        active_workflows = sum(1 for wf in workflows if wf.get('active', False))
        lines.append("# HELP n8n_workflows_active Number of active workflows")
        lines.append("# TYPE n8n_workflows_active gauge")
        lines.append(f"n8n_workflows_active {active_workflows} {timestamp}")
        
        # Métricas por workflow individual
        lines.append("# HELP n8n_workflow_info Workflow information")
        lines.append("# TYPE n8n_workflow_info gauge")
        
        for wf in workflows:
            wf_id = wf.get('id', 'unknown')
            wf_name = wf.get('name', 'unknown').replace('"', '\\"')
            active = 1 if wf.get('active', False) else 0
            nodes_count = len(wf.get('nodes', []))
            
            lines.append(
                f'n8n_workflow_info{{workflow_id="{wf_id}",workflow_name="{wf_name}",active="{active}"}} '
                f'{nodes_count} {timestamp}'
            )
        
        # Métricas de Execuções
        lines.append("# HELP n8n_executions_total Total number of executions")
        lines.append("# TYPE n8n_executions_total gauge")
        lines.append(f"n8n_executions_total {len(executions)} {timestamp}")
        
        # Criar mapa de workflow IDs para nomes
        workflow_names = {wf.get('id'): wf.get('name', 'unknown') for wf in workflows}
        
        # Filtrar apenas execuções de workflows que ainda existem
        valid_executions = [
            exec for exec in executions 
            if exec.get('workflowId') in workflow_names
        ]
        
        # Log de execuções filtradas
        filtered_count = len(executions) - len(valid_executions)
        if filtered_count > 0:
            print(f"   ⚠️  {filtered_count} execuções de workflows deletados foram filtradas")
        
        # Agregar execuções por workflow
        workflow_executions = defaultdict(lambda: {'total': 0, 'success': 0, 'failed': 0, 'duration': [], 'name': 'unknown'})
        
        for exec in valid_executions:
            wf_id = exec.get('workflowId')
            finished = exec.get('finished', False)
            stopped_at = exec.get('stoppedAt')
            started_at = exec.get('startedAt')
            
            # Usar o nome do workflow do mapa criado
            workflow_executions[wf_id]['name'] = workflow_names[wf_id]
            
            workflow_executions[wf_id]['total'] += 1
            
            # Determinar sucesso/falha
            if finished:
                if stopped_at and not exec.get('data', {}).get('resultData', {}).get('error'):
                    workflow_executions[wf_id]['success'] += 1
                else:
                    workflow_executions[wf_id]['failed'] += 1
            
            # Calcular duração
            if started_at and stopped_at:
                try:
                    start = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    stop = datetime.fromisoformat(stopped_at.replace('Z', '+00:00'))
                    duration = (stop - start).total_seconds()
                    workflow_executions[wf_id]['duration'].append(duration)
                except:
                    pass
        
        # Métricas por workflow
        lines.append("# HELP n8n_workflow_executions_total Total executions per workflow")
        lines.append("# TYPE n8n_workflow_executions_total gauge")
        
        for wf_id, data in workflow_executions.items():
            wf_name = data['name'].replace('"', '\\"')
            lines.append(
                f'n8n_workflow_executions_total{{workflow_id="{wf_id}",workflow_name="{wf_name}"}} '
                f'{data["total"]} {timestamp}'
            )
        
        lines.append("# HELP n8n_workflow_executions_success Successful executions per workflow")
        lines.append("# TYPE n8n_workflow_executions_success gauge")
        
        for wf_id, data in workflow_executions.items():
            wf_name = data['name'].replace('"', '\\"')
            lines.append(
                f'n8n_workflow_executions_success{{workflow_id="{wf_id}",workflow_name="{wf_name}"}} '
                f'{data["success"]} {timestamp}'
            )
        
        lines.append("# HELP n8n_workflow_executions_failed Failed executions per workflow")
        lines.append("# TYPE n8n_workflow_executions_failed gauge")
        
        for wf_id, data in workflow_executions.items():
            wf_name = data['name'].replace('"', '\\"')
            lines.append(
                f'n8n_workflow_executions_failed{{workflow_id="{wf_id}",workflow_name="{wf_name}"}} '
                f'{data["failed"]} {timestamp}'
            )
        
        # Duração média por workflow
        lines.append("# HELP n8n_workflow_execution_duration_seconds Average execution duration per workflow")
        lines.append("# TYPE n8n_workflow_execution_duration_seconds gauge")
        
        for wf_id, data in workflow_executions.items():
            if data['duration']:
                avg_duration = sum(data['duration']) / len(data['duration'])
                wf_name = data['name'].replace('"', '\\"')
                lines.append(
                    f'n8n_workflow_execution_duration_seconds{{workflow_id="{wf_id}",workflow_name="{wf_name}"}} '
                    f'{avg_duration:.2f} {timestamp}'
                )
        
        # Taxa de sucesso global
        total_finished = sum(d['success'] + d['failed'] for d in workflow_executions.values())
        total_success = sum(d['success'] for d in workflow_executions.values())
        
        if total_finished > 0:
            success_rate = (total_success / total_finished) * 100
            lines.append("# HELP n8n_success_rate_percent Overall success rate percentage")
            lines.append("# TYPE n8n_success_rate_percent gauge")
            lines.append(f"n8n_success_rate_percent {success_rate:.2f} {timestamp}")
        
        return '\n'.join(lines) + '\n'
    
    def push_to_victoria_metrics(self, metrics: str) -> bool:
        """
        Envia métricas para Victoria Metrics
        
        Args:
            metrics: String com métricas em formato Prometheus
            
        Returns:
            True se sucesso, False caso contrário
        """
        url = f"{self.vm_url}/api/v1/import/prometheus"
        
        try:
            response = requests.post(url, data=metrics, timeout=10)
            response.raise_for_status()
            print("✅ Métricas enviadas para Victoria Metrics com sucesso")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao enviar métricas para Victoria Metrics: {e}")
            return False
    
    def push_to_prometheus_pushgateway(self, metrics: str) -> bool:
        """
        Envia métricas para Prometheus Pushgateway
        
        Args:
            metrics: String com métricas em formato Prometheus
            
        Returns:
            True se sucesso, False caso contrário
        """
        if not self.prometheus_pushgateway:
            print("❌ URL do Prometheus Pushgateway não configurado")
            return False
        
        url = f"{self.prometheus_pushgateway}/metrics/job/{self.prometheus_job}"
        
        try:
            response = requests.post(url, data=metrics, timeout=10)
            response.raise_for_status()
            print(f"✅ Métricas enviadas para Prometheus Pushgateway com sucesso")
            print(f"   Job: {self.prometheus_job}")
            print(f"   URL: {self.prometheus_pushgateway}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao enviar métricas para Prometheus: {e}")
            print(f"   Verifique se o Pushgateway está rodando em: {self.prometheus_pushgateway}")
            return False
    
    def push_metrics(self, metrics: str) -> bool:
        """
        Envia métricas para o backend configurado
        
        Args:
            metrics: String com métricas em formato Prometheus
            
        Returns:
            True se sucesso, False caso contrário
        """
        if self.backend == "prometheus":
            return self.push_to_prometheus_pushgateway(metrics)
        else:
            return self.push_to_victoria_metrics(metrics)
    
    def collect_and_push(self, executions_limit: int = 100) -> bool:
        """
        Coleta métricas do N8N e envia para Victoria Metrics
        
        Args:
            executions_limit: Número de execuções para analisar
            
        Returns:
            True se sucesso, False caso contrário
        """
        print("=" * 60)
        print("🚀 N8N Metrics Exporter")
        print("=" * 60)
        print()
        
        # Coletar dados
        workflows = self.collect_workflows()
        executions = self.collect_executions(total_limit=executions_limit)
        
        if not workflows and not executions:
            print("⚠️  Nenhum dado coletado")
            return False
        
        print()
        print("📈 Gerando métricas Prometheus...")
        metrics = self.generate_prometheus_metrics(workflows, executions)
        
        # Mostrar preview
        lines = metrics.split('\n')
        metric_lines = [l for l in lines if l and not l.startswith('#')]
        print(f"✅ {len(metric_lines)} métricas geradas")
        
        print()
        print("📤 Enviando para Victoria Metrics...")
        success = self.push_metrics(metrics)
        
        print()
        print("=" * 60)
        if success:
            print("✅ Coleta e exportação concluídas com sucesso!")
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


def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='N8N Metrics Exporter')
    parser.add_argument('--backend', choices=['victoria_metrics', 'prometheus'], 
                        default='prometheus',
                        help='Backend para enviar métricas (default: prometheus)')
    parser.add_argument('--limit', type=int, default=1000,
                        help='Número de execuções a coletar (default: 1000)')
    args = parser.parse_args()
    
    print("🔍 Carregando credenciais...")
    
    try:
        creds = CredentialsManager()
        n8n_config = creds.get_n8n_config()
        
        n8n_url = n8n_config.get('url')
        api_key = n8n_config.get('api_key')
        
        if not n8n_url or not api_key:
            print("❌ URL ou API Key do N8N não encontrados")
            sys.exit(1)
        
        print(f"✅ N8N URL: {n8n_url}")
        print(f"✅ Backend: {args.backend}")
        print()
        
        # Configurar backend
        if args.backend == "prometheus":
            prom_config = creds.get_prometheus_config()
            pushgateway_url = prom_config.get('pushgateway_url', 'http://wfdb01.vya.digital:9091')
            job_name = prom_config.get('job_name', 'n8n_metrics')
            
            print(f"✅ Prometheus Pushgateway: {pushgateway_url}")
            print(f"✅ Job name: {job_name}")
            print()
            
            exporter = N8NMetricsExporter(
                n8n_url=n8n_url,
                n8n_api_key=api_key,
                prometheus_pushgateway=pushgateway_url,
                prometheus_job=job_name,
                backend="prometheus"
            )
        else:
            # Victoria Metrics
            exporter = N8NMetricsExporter(
                n8n_url=n8n_url,
                n8n_api_key=api_key,
                vm_url="http://localhost:8428",
                backend="victoria_metrics"
            )
        
        # Coletar e exportar
        success = exporter.collect_and_push(executions_limit=args.limit)
        
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
