"""
N8N Metrics Collector
Coleta métricas do N8N via API para análise de performance
"""

import requests
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class N8NMetricsCollector:
    """Coletor de métricas do N8N via API"""
    
    def __init__(self, base_url: str, api_key: str, output_dir: str = "./data/metrics"):
        """
        Inicializa o coletor de métricas
        
        Args:
            base_url: URL base do N8N (ex: https://n8n.example.com)
            api_key: API Key para autenticação
            output_dir: Diretório para salvar os dados coletados
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.headers = {
            "X-N8N-API-KEY": api_key,
            "Accept": "application/json"
        }
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Faz requisição à API do N8N
        
        Args:
            endpoint: Endpoint da API (ex: /api/v1/workflows)
            params: Parâmetros da query string
            
        Returns:
            Resposta da API em formato dict
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao fazer requisição para {endpoint}: {e}")
            return {}
    
    def collect_workflows(self) -> List[Dict]:
        """
        Coleta informações de todos os workflows
        
        Returns:
            Lista de workflows
        """
        print("📊 Coletando workflows...")
        data = self._make_request("/api/v1/workflows")
        workflows = data.get('data', [])
        
        # Salvar workflows
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"workflows_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(workflows, f, indent=2)
        
        print(f"✅ {len(workflows)} workflows coletados e salvos em {output_file}")
        
        # Estatísticas básicas
        active_count = sum(1 for wf in workflows if wf.get('active', False))
        print(f"   • Ativos: {active_count}/{len(workflows)}")
        
        return workflows
    
    def collect_executions(self, limit: int = 100, workflow_id: Optional[str] = None) -> List[Dict]:
        """
        Coleta histórico de execuções
        
        Args:
            limit: Número máximo de execuções a coletar
            workflow_id: ID do workflow específico (opcional)
            
        Returns:
            Lista de execuções
        """
        print(f"📊 Coletando execuções (limit={limit})...")
        
        params = {"limit": limit}
        if workflow_id:
            params["workflowId"] = workflow_id
        
        data = self._make_request("/api/v1/executions", params=params)
        executions = data.get('data', [])
        
        # Salvar execuções
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_workflow_{workflow_id}" if workflow_id else ""
        output_file = self.output_dir / f"executions{suffix}_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(executions, f, indent=2)
        
        print(f"✅ {len(executions)} execuções coletadas e salvas em {output_file}")
        
        # Estatísticas
        if executions:
            finished = sum(1 for ex in executions if ex.get('finished', False))
            success_rate = (finished / len(executions)) * 100 if executions else 0
            print(f"   • Finalizadas: {finished}/{len(executions)} ({success_rate:.1f}%)")
        
        return executions
    
    def collect_workflow_details(self, workflow_id: str) -> Dict:
        """
        Coleta detalhes de um workflow específico
        
        Args:
            workflow_id: ID do workflow
            
        Returns:
            Dados do workflow
        """
        print(f"📊 Coletando detalhes do workflow {workflow_id}...")
        workflow = self._make_request(f"/api/v1/workflows/{workflow_id}")
        
        # Salvar workflow
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"workflow_{workflow_id}_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(workflow, f, indent=2)
        
        name = workflow.get('name', 'Unknown')
        nodes_count = len(workflow.get('nodes', []))
        print(f"✅ Workflow '{name}' coletado ({nodes_count} nodes)")
        
        return workflow
    
    def analyze_execution_performance(self, executions: List[Dict]) -> Dict:
        """
        Analisa performance das execuções
        
        Args:
            executions: Lista de execuções
            
        Returns:
            Estatísticas de performance
        """
        if not executions:
            return {}
        
        durations = []
        statuses = {'success': 0, 'error': 0, 'waiting': 0, 'running': 0}
        
        for ex in executions:
            # Calcular duração
            started = ex.get('startedAt')
            stopped = ex.get('stoppedAt')
            
            if started and stopped:
                try:
                    start_dt = datetime.fromisoformat(started.replace('Z', '+00:00'))
                    stop_dt = datetime.fromisoformat(stopped.replace('Z', '+00:00'))
                    duration = (stop_dt - start_dt).total_seconds()
                    durations.append(duration)
                except:
                    pass
            
            # Contar status
            status = 'waiting'
            if ex.get('finished'):
                status = 'success'
            elif ex.get('stoppedAt'):
                status = 'error'
            elif ex.get('startedAt'):
                status = 'running'
            
            statuses[status] = statuses.get(status, 0) + 1
        
        # Estatísticas
        stats = {
            'total_executions': len(executions),
            'statuses': statuses,
            'success_rate': (statuses['success'] / len(executions) * 100) if executions else 0
        }
        
        if durations:
            durations.sort()
            stats['duration'] = {
                'mean': sum(durations) / len(durations),
                'median': durations[len(durations) // 2],
                'min': min(durations),
                'max': max(durations),
                'p95': durations[int(len(durations) * 0.95)],
                'p99': durations[int(len(durations) * 0.99)]
            }
        
        return stats
    
    def generate_summary_report(self, workflows: List[Dict], executions: List[Dict]) -> str:
        """
        Gera relatório resumido
        
        Args:
            workflows: Lista de workflows
            executions: Lista de execuções
            
        Returns:
            Relatório em formato markdown
        """
        report = ["# 📊 N8N Metrics Summary\n"]
        report.append(f"**Data**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append("---\n\n")
        
        # Workflows
        report.append("## 📋 Workflows\n")
        report.append(f"- Total: {len(workflows)}\n")
        active = sum(1 for wf in workflows if wf.get('active', False))
        report.append(f"- Ativos: {active}\n")
        report.append(f"- Inativos: {len(workflows) - active}\n\n")
        
        # Execuções
        report.append("## 🔄 Execuções\n")
        stats = self.analyze_execution_performance(executions)
        report.append(f"- Total: {stats.get('total_executions', 0)}\n")
        report.append(f"- Taxa de Sucesso: {stats.get('success_rate', 0):.1f}%\n")
        
        if 'duration' in stats:
            dur = stats['duration']
            report.append(f"\n### ⏱️ Duração\n")
            report.append(f"- Média: {dur['mean']:.2f}s\n")
            report.append(f"- Mediana: {dur['median']:.2f}s\n")
            report.append(f"- Mínimo: {dur['min']:.2f}s\n")
            report.append(f"- Máximo: {dur['max']:.2f}s\n")
            report.append(f"- P95: {dur['p95']:.2f}s\n")
            report.append(f"- P99: {dur['p99']:.2f}s\n")
        
        return ''.join(report)


def main():
    """Função principal"""
    # Configuração (via variáveis de ambiente)
    N8N_URL = os.getenv("N8N_URL", "https://n8n.example.com")
    N8N_API_KEY = os.getenv("N8N_API_KEY", "")
    
    if not N8N_API_KEY:
        print("❌ Erro: N8N_API_KEY não configurada")
        print("Configure: export N8N_API_KEY='sua-api-key'")
        return
    
    print("🚀 Iniciando coleta de métricas do N8N\n")
    print(f"URL: {N8N_URL}\n")
    
    # Inicializar coletor
    collector = N8NMetricsCollector(N8N_URL, N8N_API_KEY)
    
    # Coletar dados
    workflows = collector.collect_workflows()
    print()
    
    executions = collector.collect_executions(limit=500)
    print()
    
    # Gerar relatório
    report = collector.generate_summary_report(workflows, executions)
    
    # Salvar relatório
    report_file = collector.output_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"📄 Relatório salvo em {report_file}\n")
    print(report)


if __name__ == "__main__":
    main()
