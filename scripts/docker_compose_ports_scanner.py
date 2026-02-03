#!/usr/bin/env python3
"""
Docker Compose Port Scanner
Encontra todos os arquivos docker-compose e lista as portas em uso.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple
from collections import defaultdict


def find_docker_compose_files(root_path: str = ".") -> List[Path]:
    """Encontra todos os arquivos docker-compose recursivamente."""
    compose_files = []
    root = Path(root_path).resolve()
    
    patterns = [
        "**/docker-compose.yml",
        "**/docker-compose.yaml",
        "**/compose.yml",
        "**/compose.yaml"
    ]
    
    for pattern in patterns:
        compose_files.extend(root.glob(pattern))
    
    return sorted(set(compose_files))


def extract_ports_from_compose(file_path: Path) -> List[Dict[str, str]]:
    """Extrai portas de um arquivo docker-compose sem usar PyYAML."""
    ports_info = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        current_service = None
        in_ports_section = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Detecta nome do serviço
            if re.match(r'^[a-zA-Z0-9_-]+:', stripped) and not stripped.startswith('-'):
                # Verifica se não está dentro de ports ou outras seções
                indent = len(line) - len(line.lstrip())
                if indent <= 2:  # Serviço no nível raiz
                    current_service = stripped.rstrip(':')
                    in_ports_section = False
            
            # Detecta seção de ports
            if stripped == 'ports:' and current_service:
                in_ports_section = True
                continue
            
            # Se encontrou outra seção, sai da seção ports
            if in_ports_section and re.match(r'^[a-zA-Z_]+:', stripped):
                in_ports_section = False
            
            # Extrai portas
            if in_ports_section and current_service:
                # Formato: - "8080:80" ou - 8080:80 ou - "8080:80/tcp"
                port_match = re.search(r'["\']?(\d+):(\d+)(?:/\w+)?["\']?', stripped)
                if port_match:
                    host_port = port_match.group(1)
                    container_port = port_match.group(2)
                    
                    ports_info.append({
                        'service': current_service,
                        'host_port': host_port,
                        'container_port': container_port,
                        'mapping': f"{host_port}→{container_port}"
                    })
    
    except Exception as e:
        print(f"⚠️  Erro ao ler {file_path}: {e}")
    
    return ports_info


def scan_ports(root_path: str = "~") -> Dict[str, List[Dict]]:
    """Escaneia todos os docker-compose e retorna portas organizadas."""
    root = Path(root_path).expanduser()
    
    print(f"🔍 Procurando arquivos docker-compose em: {root}\n")
    
    compose_files = find_docker_compose_files(root)
    
    if not compose_files:
        print("❌ Nenhum arquivo docker-compose encontrado!")
        return {}
    
    print(f"📁 Encontrados {len(compose_files)} arquivo(s) docker-compose\n")
    
    all_ports = {}
    port_conflicts = defaultdict(list)
    
    for compose_file in compose_files:
        relative_path = compose_file.relative_to(root) if compose_file.is_relative_to(root) else compose_file
        ports = extract_ports_from_compose(compose_file)
        
        if ports:
            all_ports[str(relative_path)] = ports
            
            # Detecta conflitos de portas
            for port_info in ports:
                host_port = port_info['host_port']
                port_conflicts[host_port].append({
                    'file': str(relative_path),
                    'service': port_info['service']
                })
    
    return all_ports, port_conflicts


def print_ports_report(all_ports: Dict, port_conflicts: Dict):
    """Imprime relatório de portas."""
    print("="*80)
    print("🔌 PORTAS EM USO - DOCKER COMPOSE")
    print("="*80 + "\n")
    
    if not all_ports:
        print("Nenhuma porta encontrada nos arquivos docker-compose.")
        return
    
    # Relatório por arquivo
    total_ports = 0
    for file_path, ports in sorted(all_ports.items()):
        print(f"📄 {file_path}")
        
        for port in sorted(ports, key=lambda x: int(x['host_port'])):
            print(f"   └─ {port['service']:30} | Porta: {port['host_port']:5} → {port['container_port']:5}")
            total_ports += 1
        
        print()
    
    # Resumo de portas
    print("="*80)
    print("📊 RESUMO")
    print("="*80 + "\n")
    print(f"Total de arquivos: {len(all_ports)}")
    print(f"Total de portas mapeadas: {total_ports}\n")
    
    # Lista todas as portas do host em uso
    all_host_ports = set()
    for ports in all_ports.values():
        for port in ports:
            all_host_ports.add(int(port['host_port']))
    
    print(f"Portas do host em uso: {sorted(all_host_ports)}\n")
    
    # Detecta conflitos
    conflicts = {port: files for port, files in port_conflicts.items() if len(files) > 1}
    
    if conflicts:
        print("⚠️  CONFLITOS DE PORTA DETECTADOS:\n")
        for port, usages in sorted(conflicts.items(), key=lambda x: int(x[0])):
            print(f"   Porta {port} usada em {len(usages)} lugares:")
            for usage in usages:
                print(f"      - {usage['file']} (serviço: {usage['service']})")
            print()
    else:
        print("✅ Nenhum conflito de porta detectado!\n")


def export_ports_csv(all_ports: Dict, output_file: str = "docker_ports.csv"):
    """Exporta portas para CSV."""
    import csv
    
    rows = []
    for file_path, ports in all_ports.items():
        for port in ports:
            rows.append({
                'Arquivo': file_path,
                'Serviço': port['service'],
                'Porta Host': port['host_port'],
                'Porta Container': port['container_port'],
                'Mapeamento': port['mapping']
            })
    
    if rows:
        output_path = Path(output_file)
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['Arquivo', 'Serviço', 'Porta Host', 'Porta Container', 'Mapeamento'])
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"💾 Relatório CSV exportado para: {output_path.absolute()}\n")


def main():
    """Função principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Escaneia arquivos docker-compose e lista portas em uso')
    parser.add_argument('path', nargs='?', default=os.getcwd(), 
                       help='Caminho para escanear (padrão: diretório atual)')
    parser.add_argument('--csv', action='store_true', 
                       help='Exporta resultados para CSV')
    
    args = parser.parse_args()
    
    all_ports, port_conflicts = scan_ports(args.path)
    print_ports_report(all_ports, port_conflicts)
    
    if args.csv and all_ports:
        export_ports_csv(all_ports)


if __name__ == "__main__":
    main()
