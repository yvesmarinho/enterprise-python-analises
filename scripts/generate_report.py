#!/usr/bin/env python3
"""
Gera relatório sintético dos servidores candidatos a desligamento.
"""

import json
from pathlib import Path
from datetime import datetime


def generate_server_report(servers_to_analyze=['wf005.vya.digital', 'wf006.vya.digital']):
    """Gera relatório markdown dos servidores especificados."""
    
    data_path = Path("data/docker_collector")
    report_lines = []
    
    # Cabeçalho
    report_lines.append("# 📋 Relatório de Servidores - Candidatos a Desligamento\n")
    report_lines.append(f"**Data de Análise:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    report_lines.append("---\n")
    
    for server_name in servers_to_analyze:
        json_files = list(data_path.glob(f"{server_name}_docker_stats_*.json"))
        
        if not json_files:
            report_lines.append(f"⚠️ Dados não encontrados para {server_name}\n\n")
            continue
        
        # Carrega o arquivo mais recente
        json_file = sorted(json_files)[-1]
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Informações do servidor
        report_lines.append(f"## 🖥️ {server_name}\n")
        report_lines.append(f"**Timestamp:** {data.get('timestamp', 'N/A')}\n\n")
        
        # Resumo
        total_containers = data.get('total_containers', 0)
        containers = data.get('containers', [])
        
        total_cpu = sum(c['cpu']['percent'] for c in containers)
        total_memory_mb = sum(c['memory']['usage_mb'] for c in containers)
        total_memory_gb = total_memory_mb / 1024
        
        report_lines.append("### 📊 Resumo de Recursos\n")
        report_lines.append(f"- **Total de Containers:** {total_containers}\n")
        report_lines.append(f"- **CPU Total:** {total_cpu:.2f}%\n")
        report_lines.append(f"- **Memória Total:** {total_memory_gb:.2f} GB ({total_memory_mb:.2f} MB)\n")
        report_lines.append(f"- **Memória Média por Container:** {total_memory_mb/total_containers:.2f} MB\n\n")
        
        # Lista de containers
        report_lines.append("### 📦 Containers\n")
        report_lines.append("| # | Nome | Imagem | CPU % | Memória | Portas | Volumes |\n")
        report_lines.append("|---|------|--------|-------|---------|--------|----------|\n")
        
        # Ordena por uso de memória
        containers_sorted = sorted(containers, key=lambda x: x['memory']['usage_mb'], reverse=True)
        
        for idx, container in enumerate(containers_sorted, 1):
            name = container['name']
            image = container['image'].split(':')[0].split('/')[-1]  # Nome simplificado
            cpu = container['cpu']['percent']
            memory_mb = container['memory']['usage_mb']
            memory_gb = memory_mb / 1024
            
            # Portas
            ports = container.get('ports', {})
            port_list = []
            for port, mapping in ports.items():
                if mapping:
                    for m in mapping:
                        port_list.append(f"{m['HostPort']}→{port.split('/')[0]}")
            ports_str = ', '.join(port_list) if port_list else '-'
            
            # Volumes
            volumes = container.get('volumes', [])
            vol_count = len(volumes)
            vol_usage_mb = sum(v.get('usage', {}).get('mb', 0) for v in volumes)
            
            if vol_usage_mb > 0:
                vol_str = f"{vol_count} ({vol_usage_mb:.0f}MB)"
            elif vol_count > 0:
                vol_str = f"{vol_count}"
            else:
                vol_str = "-"
            
            # Formata memória
            if memory_gb >= 1:
                mem_str = f"{memory_gb:.2f} GB"
            else:
                mem_str = f"{memory_mb:.0f} MB"
            
            report_lines.append(f"| {idx} | `{name}` | {image} | {cpu:.2f} | {mem_str} | {ports_str} | {vol_str} |\n")
        
        # Detalhes importantes
        report_lines.append("\n### 🔍 Observações\n")
        
        # Containers com alto uso
        high_cpu = [c for c in containers if c['cpu']['percent'] > 5]
        high_memory = [c for c in containers if c['memory']['usage_mb'] > 500]
        
        if high_cpu:
            report_lines.append(f"- **Alto uso de CPU (>5%):** {len(high_cpu)} container(s)\n")
            for c in high_cpu:
                report_lines.append(f"  - `{c['name']}`: {c['cpu']['percent']:.2f}%\n")
        
        if high_memory:
            report_lines.append(f"- **Alto uso de Memória (>500MB):** {len(high_memory)} container(s)\n")
            for c in high_memory:
                mem_gb = c['memory']['usage_mb'] / 1024
                report_lines.append(f"  - `{c['name']}`: {mem_gb:.2f} GB\n")
        
        # Redes
        networks = set()
        for c in containers:
            networks.update(c.get('networks', []))
        report_lines.append(f"- **Redes utilizadas:** {', '.join(sorted(networks))}\n")
        
        # Volumes críticos
        critical_volumes = []
        for c in containers:
            for vol in c.get('volumes', []):
                if vol.get('usage', {}).get('mb', 0) > 100:  # Mais de 100MB
                    critical_volumes.append({
                        'container': c['name'],
                        'source': vol.get('source', 'N/A'),
                        'size_mb': vol['usage']['mb']
                    })
        
        if critical_volumes:
            report_lines.append(f"\n- **Volumes com dados significativos (>100MB):**\n")
            for vol in sorted(critical_volumes, key=lambda x: x['size_mb'], reverse=True):
                report_lines.append(f"  - `{vol['container']}`: {vol['source']} ({vol['size_mb']:.2f} MB)\n")
        
        report_lines.append("\n---\n\n")
    
    # Rodapé
    report_lines.append("## 📌 Próximas Ações\n\n")
    report_lines.append("### ✅ Checklist de Migração\n\n")
    report_lines.append("- [ ] Backup de todos os volumes com dados\n")
    report_lines.append("- [ ] Documentar configurações de rede\n")
    report_lines.append("- [ ] Verificar dependências entre containers\n")
    report_lines.append("- [ ] Testar conectividade de portas nos servidores destino\n")
    report_lines.append("- [ ] Planejar janela de manutenção\n")
    report_lines.append("- [ ] Atualizar DNS/Proxy reverso\n")
    report_lines.append("- [ ] Validar funcionamento após migração\n\n")
    
    # Salva relatório
    report_path = Path("servidores_desligamento_report.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.writelines(report_lines)
    
    print(f"✅ Relatório gerado: {report_path.absolute()}")
    return report_path


if __name__ == "__main__":
    generate_server_report()
