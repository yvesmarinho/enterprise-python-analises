"""
Workflow Analyzer
Analisa workflows exportados do N8N para identificar padrões e oportunidades de otimização
"""

import json
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Tuple
import sys


class WorkflowAnalyzer:
    """Analisador de workflows do N8N"""
    
    def __init__(self, data_dir: str = "./data/workflows"):
        """
        Inicializa o analisador
        
        Args:
            data_dir: Diretório com os workflows exportados
        """
        self.data_dir = Path(data_dir)
        self.workflows = []
    
    def load_workflows(self) -> List[Dict]:
        """
        Carrega todos os workflows do diretório
        
        Returns:
            Lista de workflows
        """
        print(f"📂 Carregando workflows de {self.data_dir}...")
        
        workflow_files = list(self.data_dir.glob("workflow_*.json"))
        workflow_files.extend(self.data_dir.glob("workflows_*.json"))
        
        for file in workflow_files:
            try:
                with open(file) as f:
                    data = json.load(f)
                    
                    # Se for array de workflows
                    if isinstance(data, list):
                        self.workflows.extend(data)
                    # Se for um único workflow
                    elif isinstance(data, dict):
                        # Verificar se tem 'data' (resposta da API)
                        if 'data' in data and isinstance(data['data'], list):
                            self.workflows.extend(data['data'])
                        else:
                            self.workflows.append(data)
            except Exception as e:
                print(f"⚠️  Erro ao carregar {file}: {e}")
        
        print(f"✅ {len(self.workflows)} workflows carregados\n")
        return self.workflows
    
    def analyze_nodes(self) -> Dict:
        """
        Analisa os nodes utilizados nos workflows
        
        Returns:
            Estatísticas de nodes
        """
        print("🔍 Analisando nodes...\n")
        
        all_nodes = []
        workflows_by_node = defaultdict(list)
        
        for wf in self.workflows:
            wf_name = wf.get('name', 'Unknown')
            nodes = wf.get('nodes', [])
            
            for node in nodes:
                node_type = node.get('type', 'Unknown')
                all_nodes.append(node_type)
                workflows_by_node[node_type].append(wf_name)
        
        node_counts = Counter(all_nodes)
        
        # Top nodes
        print("📊 Top 15 Nodes Mais Utilizados:")
        print("-" * 60)
        for node, count in node_counts.most_common(15):
            percentage = (count / len(all_nodes)) * 100
            print(f"  {node:40s} {count:4d} ({percentage:5.1f}%)")
        
        print(f"\nTotal de nodes: {len(all_nodes)}")
        print(f"Tipos únicos de nodes: {len(node_counts)}")
        
        return {
            'total_nodes': len(all_nodes),
            'unique_types': len(node_counts),
            'node_counts': dict(node_counts),
            'workflows_by_node': dict(workflows_by_node)
        }
    
    def analyze_complexity(self) -> Dict:
        """
        Analisa a complexidade dos workflows
        
        Returns:
            Estatísticas de complexidade
        """
        print("\n🔍 Analisando complexidade...\n")
        
        complexities = []
        complex_workflows = []
        
        for wf in self.workflows:
            nodes_count = len(wf.get('nodes', []))
            connections = wf.get('connections', {})
            connections_count = sum(len(conns) for conns in connections.values())
            
            complexity = {
                'name': wf.get('name', 'Unknown'),
                'id': wf.get('id'),
                'nodes': nodes_count,
                'connections': connections_count,
                'active': wf.get('active', False)
            }
            
            complexities.append(complexity)
            
            # Workflows complexos (> 20 nodes)
            if nodes_count > 20:
                complex_workflows.append(complexity)
        
        # Ordenar por número de nodes
        complexities.sort(key=lambda x: x['nodes'], reverse=True)
        
        # Estatísticas
        total_nodes = sum(c['nodes'] for c in complexities)
        avg_nodes = total_nodes / len(complexities) if complexities else 0
        
        print("📊 Estatísticas de Complexidade:")
        print("-" * 60)
        print(f"  Média de nodes por workflow: {avg_nodes:.1f}")
        print(f"  Workflow mais complexo: {complexities[0]['nodes']} nodes ({complexities[0]['name']})")
        print(f"  Workflow mais simples: {complexities[-1]['nodes']} nodes ({complexities[-1]['name']})")
        print(f"  Workflows complexos (>20 nodes): {len(complex_workflows)}")
        
        print("\n📋 Top 10 Workflows Mais Complexos:")
        print("-" * 60)
        for i, wf in enumerate(complexities[:10], 1):
            status = "🟢" if wf['active'] else "⚫"
            print(f"  {i:2d}. {status} {wf['name']:40s} {wf['nodes']:3d} nodes")
        
        return {
            'average_nodes': avg_nodes,
            'max_nodes': complexities[0]['nodes'] if complexities else 0,
            'min_nodes': complexities[-1]['nodes'] if complexities else 0,
            'complex_workflows': complex_workflows,
            'all_complexities': complexities
        }
    
    def analyze_active_status(self) -> Dict:
        """
        Analisa status de ativação dos workflows
        
        Returns:
            Estatísticas de status
        """
        print("\n🔍 Analisando status de ativação...\n")
        
        active_count = sum(1 for wf in self.workflows if wf.get('active', False))
        inactive_count = len(self.workflows) - active_count
        
        print("📊 Status dos Workflows:")
        print("-" * 60)
        print(f"  ✅ Ativos: {active_count} ({active_count/len(self.workflows)*100:.1f}%)")
        print(f"  ❌ Inativos: {inactive_count} ({inactive_count/len(self.workflows)*100:.1f}%)")
        
        return {
            'active': active_count,
            'inactive': inactive_count,
            'active_percentage': (active_count / len(self.workflows) * 100) if self.workflows else 0
        }
    
    def identify_optimization_opportunities(self) -> List[Dict]:
        """
        Identifica oportunidades de otimização
        
        Returns:
            Lista de oportunidades
        """
        print("\n🎯 Identificando oportunidades de otimização...\n")
        
        opportunities = []
        
        for wf in self.workflows:
            wf_name = wf.get('name', 'Unknown')
            nodes = wf.get('nodes', [])
            
            # Oportunidade 1: Workflows muito complexos
            if len(nodes) > 30:
                opportunities.append({
                    'workflow': wf_name,
                    'type': 'Complexidade Alta',
                    'description': f'Workflow com {len(nodes)} nodes - considerar modularização',
                    'priority': 'ALTA',
                    'nodes_count': len(nodes)
                })
            
            # Oportunidade 2: Múltiplos HTTP Request nodes (possível batching)
            http_nodes = [n for n in nodes if n.get('type') == 'n8n-nodes-base.httpRequest']
            if len(http_nodes) > 5:
                opportunities.append({
                    'workflow': wf_name,
                    'type': 'HTTP Requests',
                    'description': f'{len(http_nodes)} HTTP requests - considerar batching ou otimização',
                    'priority': 'MÉDIA',
                    'http_count': len(http_nodes)
                })
            
            # Oportunidade 3: Uso de Wait nodes (possível otimização de timing)
            wait_nodes = [n for n in nodes if 'wait' in n.get('type', '').lower()]
            if len(wait_nodes) > 2:
                opportunities.append({
                    'workflow': wf_name,
                    'type': 'Wait Nodes',
                    'description': f'{len(wait_nodes)} wait nodes - revisar necessidade',
                    'priority': 'BAIXA',
                    'wait_count': len(wait_nodes)
                })
            
            # Oportunidade 4: Múltiplos Function nodes (lógica complexa)
            function_nodes = [n for n in nodes if 'function' in n.get('type', '').lower()]
            if len(function_nodes) > 3:
                opportunities.append({
                    'workflow': wf_name,
                    'type': 'Function Nodes',
                    'description': f'{len(function_nodes)} function nodes - possível otimização de código',
                    'priority': 'MÉDIA',
                    'function_count': len(function_nodes)
                })
        
        # Ordenar por prioridade
        priority_order = {'ALTA': 0, 'MÉDIA': 1, 'BAIXA': 2}
        opportunities.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        print("📋 Oportunidades Identificadas:")
        print("-" * 80)
        for opp in opportunities[:15]:  # Top 15
            priority_emoji = {'ALTA': '🔴', 'MÉDIA': '🟡', 'BAIXA': '🟢'}.get(opp['priority'], '⚪')
            print(f"  {priority_emoji} [{opp['priority']:5s}] {opp['workflow']:30s} | {opp['type']:20s}")
            print(f"     → {opp['description']}")
        
        print(f"\nTotal de oportunidades: {len(opportunities)}")
        
        return opportunities
    
    def generate_report(self, output_file: str = "./reports/workflow_analysis.md"):
        """
        Gera relatório completo de análise
        
        Args:
            output_file: Caminho do arquivo de saída
        """
        print(f"\n📄 Gerando relatório em {output_file}...\n")
        
        # Executar todas as análises
        nodes_stats = self.analyze_nodes()
        complexity_stats = self.analyze_complexity()
        status_stats = self.analyze_active_status()
        opportunities = self.identify_optimization_opportunities()
        
        # Criar relatório
        report = []
        report.append("# 📊 Análise de Workflows N8N\n\n")
        report.append(f"**Data**: {Path().resolve()}\n\n")
        report.append("---\n\n")
        
        # Resumo geral
        report.append("## 📋 Resumo Geral\n\n")
        report.append(f"- **Total de Workflows**: {len(self.workflows)}\n")
        report.append(f"- **Workflows Ativos**: {status_stats['active']} ({status_stats['active_percentage']:.1f}%)\n")
        report.append(f"- **Total de Nodes**: {nodes_stats['total_nodes']}\n")
        report.append(f"- **Média de Nodes/Workflow**: {complexity_stats['average_nodes']:.1f}\n")
        report.append(f"- **Tipos de Nodes Únicos**: {nodes_stats['unique_types']}\n\n")
        
        # Top nodes
        report.append("## 🔧 Nodes Mais Utilizados\n\n")
        report.append("| Node | Uso | Percentual |\n")
        report.append("|------|-----|------------|\n")
        for node, count in sorted(nodes_stats['node_counts'].items(), key=lambda x: x[1], reverse=True)[:10]:
            pct = (count / nodes_stats['total_nodes']) * 100
            report.append(f"| {node} | {count} | {pct:.1f}% |\n")
        report.append("\n")
        
        # Workflows complexos
        report.append("## 🎯 Workflows Mais Complexos\n\n")
        report.append("| # | Nome | Nodes | Status |\n")
        report.append("|---|------|-------|--------|\n")
        for i, wf in enumerate(complexity_stats['all_complexities'][:10], 1):
            status = "✅ Ativo" if wf['active'] else "❌ Inativo"
            report.append(f"| {i} | {wf['name']} | {wf['nodes']} | {status} |\n")
        report.append("\n")
        
        # Oportunidades
        report.append("## 💡 Oportunidades de Otimização\n\n")
        for priority in ['ALTA', 'MÉDIA', 'BAIXA']:
            priority_opps = [o for o in opportunities if o['priority'] == priority]
            if priority_opps:
                report.append(f"### Prioridade {priority}\n\n")
                for opp in priority_opps[:5]:
                    report.append(f"**{opp['workflow']}** - {opp['type']}\n")
                    report.append(f"- {opp['description']}\n\n")
        
        # Salvar relatório
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.writelines(report)
        
        print(f"✅ Relatório salvo em {output_path}")


def main():
    """Função principal"""
    print("🚀 N8N Workflow Analyzer\n")
    
    # Diretório de dados
    data_dir = "./data/workflows" if len(sys.argv) < 2 else sys.argv[1]
    
    # Inicializar analisador
    analyzer = WorkflowAnalyzer(data_dir)
    
    # Carregar workflows
    workflows = analyzer.load_workflows()
    
    if not workflows:
        print("❌ Nenhum workflow encontrado!")
        print(f"   Verifique se há arquivos em {data_dir}")
        return
    
    # Gerar relatório
    analyzer.generate_report()


if __name__ == "__main__":
    main()
