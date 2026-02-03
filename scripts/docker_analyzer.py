#!/usr/bin/env python3
"""
Docker Container Resource Analyzer
Analisa dados de containers Docker de múltiplos servidores para reorganização e redução de custos.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import statistics


@dataclass
class ContainerInfo:
    """Informações de um container."""
    name: str
    id: str
    image: str
    status: str
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    memory_limit_mb: float
    volumes: List[Dict[str, Any]]
    networks: List[str]
    ports: Dict[str, Any]
    server: str
    
    @property
    def volume_usage_mb(self) -> float:
        """Calcula uso total de volumes em MB."""
        total = 0
        for vol in self.volumes:
            if 'usage' in vol and 'mb' in vol['usage']:
                total += vol['usage']['mb']
        return total


@dataclass
class ServerStats:
    """Estatísticas agregadas de um servidor."""
    name: str
    total_containers: int
    total_cpu_percent: float
    total_memory_mb: float
    avg_memory_percent: float
    containers: List[ContainerInfo] = field(default_factory=list)
    timestamp: str = ""
    
    def add_container(self, container: ContainerInfo):
        """Adiciona um container às estatísticas."""
        self.containers.append(container)


class DockerAnalyzer:
    """Analisa dados de containers Docker para reorganização."""
    
    def __init__(self, data_path: str = "data/docker_collector"):
        self.data_path = Path(data_path)
        self.servers: Dict[str, ServerStats] = {}
        
    def load_data(self) -> None:
        """Carrega todos os arquivos JSON da pasta de dados."""
        json_files = list(self.data_path.glob("*.json"))
        
        if not json_files:
            print(f"⚠️  Nenhum arquivo JSON encontrado em {self.data_path}")
            return
        
        print(f"📁 Encontrados {len(json_files)} arquivos JSON\n")
        
        for json_file in sorted(json_files):
            self._load_server_data(json_file)
    
    def _load_server_data(self, file_path: Path) -> None:
        """Carrega dados de um servidor específico."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extrai nome do servidor do nome do arquivo
            server_name = file_path.stem.split('_docker_stats')[0]
            
            server_stats = ServerStats(
                name=server_name,
                total_containers=data.get('total_containers', 0),
                total_cpu_percent=0,
                total_memory_mb=0,
                avg_memory_percent=0,
                timestamp=data.get('timestamp', '')
            )
            
            for container_data in data.get('containers', []):
                container = ContainerInfo(
                    name=container_data['name'],
                    id=container_data['id'],
                    image=container_data['image'],
                    status=container_data['status'],
                    cpu_percent=container_data['cpu']['percent'],
                    memory_mb=container_data['memory']['usage_mb'],
                    memory_percent=container_data['memory']['percent'],
                    memory_limit_mb=container_data['memory']['limit_mb'],
                    volumes=container_data.get('volumes', []),
                    networks=container_data.get('networks', []),
                    ports=container_data.get('ports', {}),
                    server=server_name
                )
                server_stats.add_container(container)
                server_stats.total_cpu_percent += container.cpu_percent
                server_stats.total_memory_mb += container.memory_mb
            
            if server_stats.containers:
                server_stats.avg_memory_percent = statistics.mean(
                    [c.memory_percent for c in server_stats.containers]
                )
            
            self.servers[server_name] = server_stats
            print(f"✅ Carregado: {server_name} - {server_stats.total_containers} containers")
            
        except Exception as e:
            print(f"❌ Erro ao carregar {file_path}: {e}")
    
    def print_summary(self) -> None:
        """Imprime resumo dos servidores."""
        print("\n" + "="*80)
        print("📊 RESUMO DOS SERVIDORES")
        print("="*80 + "\n")
        
        for server_name, stats in sorted(self.servers.items()):
            print(f"🖥️  Servidor: {server_name}")
            print(f"   Containers: {stats.total_containers}")
            print(f"   CPU Total: {stats.total_cpu_percent:.2f}%")
            print(f"   Memória Total: {stats.total_memory_mb:.2f} MB ({stats.total_memory_mb/1024:.2f} GB)")
            print(f"   Memória Média: {stats.avg_memory_percent:.2f}%")
            print(f"   Timestamp: {stats.timestamp}")
            print()
    
    def analyze_reorganization(self) -> Dict[str, Any]:
        """Analisa e sugere reorganização dos containers."""
        print("\n" + "="*80)
        print("🔍 ANÁLISE DE REORGANIZAÇÃO")
        print("="*80 + "\n")
        
        if len(self.servers) < 2:
            print("⚠️  É necessário pelo menos 2 servidores para análise de reorganização")
            return {}
        
        # Ordena servidores por uso de recursos (menor para maior)
        servers_by_usage = sorted(
            self.servers.items(),
            key=lambda x: (x[1].total_cpu_percent + x[1].avg_memory_percent)
        )
        
        # Servidor candidato a desligar (menor uso)
        source_server_name, source_stats = servers_by_usage[0]
        
        # Servidores de destino (outros servidores)
        target_servers = servers_by_usage[1:]
        
        print(f"🎯 Servidor candidato a DESLIGAR: {source_server_name}")
        print(f"   - Containers: {source_stats.total_containers}")
        print(f"   - CPU: {source_stats.total_cpu_percent:.2f}%")
        print(f"   - Memória: {source_stats.total_memory_mb/1024:.2f} GB\n")
        
        print("📦 Containers a serem migrados:\n")
        
        migration_plan = {
            "source_server": source_server_name,
            "target_servers": [],
            "containers": [],
            "total_containers": source_stats.total_containers,
            "total_memory_mb": source_stats.total_memory_mb,
            "total_cpu_percent": source_stats.total_cpu_percent
        }
        
        # Lista containers ordenados por uso de recursos
        containers_sorted = sorted(
            source_stats.containers,
            key=lambda c: (c.memory_mb + c.cpu_percent),
            reverse=True
        )
        
        for idx, container in enumerate(containers_sorted, 1):
            print(f"   {idx}. {container.name}")
            print(f"      - Imagem: {container.image}")
            print(f"      - CPU: {container.cpu_percent:.2f}%")
            print(f"      - Memória: {container.memory_mb:.2f} MB ({container.memory_percent:.2f}%)")
            print(f"      - Volumes: {container.volume_usage_mb:.2f} MB")
            print(f"      - Redes: {', '.join(container.networks)}")
            
            if container.ports:
                ports_info = []
                for port, mapping in container.ports.items():
                    if mapping:
                        for m in mapping:
                            ports_info.append(f"{m['HostPort']}→{port}")
                if ports_info:
                    print(f"      - Portas: {', '.join(ports_info)}")
            print()
            
            migration_plan["containers"].append({
                "name": container.name,
                "image": container.image,
                "cpu_percent": container.cpu_percent,
                "memory_mb": container.memory_mb,
                "memory_percent": container.memory_percent,
                "volumes": len(container.volumes),
                "networks": container.networks,
                "ports": container.ports
            })
        
        # Sugere distribuição nos servidores alvo
        print("\n💡 SUGESTÃO DE DISTRIBUIÇÃO:\n")
        
        for target_name, target_stats in target_servers:
            capacity_cpu = 100 - target_stats.total_cpu_percent
            capacity_memory_percent = 100 - target_stats.avg_memory_percent
            
            print(f"🖥️  {target_name}")
            print(f"   Uso atual:")
            print(f"   - CPU: {target_stats.total_cpu_percent:.2f}% (capacidade livre: {capacity_cpu:.2f}%)")
            print(f"   - Memória: {target_stats.avg_memory_percent:.2f}% (capacidade livre: {capacity_memory_percent:.2f}%)")
            print(f"   - Containers: {target_stats.total_containers}")
            print()
            
            migration_plan["target_servers"].append({
                "name": target_name,
                "current_containers": target_stats.total_containers,
                "cpu_usage": target_stats.total_cpu_percent,
                "memory_usage": target_stats.avg_memory_percent,
                "cpu_capacity": capacity_cpu,
                "memory_capacity": capacity_memory_percent
            })
        
        return migration_plan
    
    def generate_recommendations(self) -> None:
        """Gera recomendações específicas."""
        print("\n" + "="*80)
        print("💡 RECOMENDAÇÕES")
        print("="*80 + "\n")
        
        recommendations = []
        
        # Identifica containers com alto uso de recursos
        all_containers = []
        for server_stats in self.servers.values():
            all_containers.extend(server_stats.containers)
        
        high_cpu = [c for c in all_containers if c.cpu_percent > 5.0]
        high_memory = [c for c in all_containers if c.memory_mb > 500]
        
        if high_cpu:
            print("⚠️  Containers com alto uso de CPU (>5%):")
            for c in sorted(high_cpu, key=lambda x: x.cpu_percent, reverse=True):
                print(f"   - {c.name} ({c.server}): {c.cpu_percent:.2f}%")
            print()
        
        if high_memory:
            print("⚠️  Containers com alto uso de Memória (>500MB):")
            for c in sorted(high_memory, key=lambda x: x.memory_mb, reverse=True):
                print(f"   - {c.name} ({c.server}): {c.memory_mb:.2f} MB ({c.memory_percent:.2f}%)")
            print()
        
        # Identifica containers por aplicação (n8n, evolution-api, etc)
        print("📋 Agrupamento por aplicação:")
        app_groups = {}
        for container in all_containers:
            app_name = container.name.split('-')[0].split('_')[0]
            if app_name not in app_groups:
                app_groups[app_name] = []
            app_groups[app_name].append(container)
        
        for app_name, containers in sorted(app_groups.items()):
            if len(containers) > 1:
                total_memory = sum(c.memory_mb for c in containers)
                total_cpu = sum(c.cpu_percent for c in containers)
                servers = set(c.server for c in containers)
                print(f"\n   {app_name}: {len(containers)} containers")
                print(f"   - Servidores: {', '.join(servers)}")
                print(f"   - CPU Total: {total_cpu:.2f}%")
                print(f"   - Memória Total: {total_memory:.2f} MB ({total_memory/1024:.2f} GB)")
        
        print("\n" + "-"*80)
        print("\n✅ PRÓXIMOS PASSOS:")
        print("   1. Revisar a lista de containers do servidor a desligar")
        print("   2. Verificar dependências entre containers (redes, volumes)")
        print("   3. Planejar janela de manutenção para migração")
        print("   4. Fazer backup dos volumes antes da migração")
        print("   5. Testar containers no servidor destino antes de desligar origem")
        print("   6. Atualizar documentação e configurações de DNS/proxy")
    
    def export_migration_plan(self, output_file: str = "migration_plan.json") -> None:
        """Exporta plano de migração para JSON."""
        plan = self.analyze_reorganization()
        
        if plan:
            output_path = Path(output_file)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(plan, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Plano de migração exportado para: {output_path.absolute()}")


def main():
    """Função principal."""
    print("\n" + "="*80)
    print("🐳 DOCKER CONTAINER RESOURCE ANALYZER")
    print("="*80 + "\n")
    
    analyzer = DockerAnalyzer()
    analyzer.load_data()
    
    if not analyzer.servers:
        print("❌ Nenhum dado carregado. Verifique a pasta data/docker_collector")
        return
    
    analyzer.print_summary()
    analyzer.analyze_reorganization()
    analyzer.generate_recommendations()
    analyzer.export_migration_plan()
    
    print("\n" + "="*80)
    print("✅ Análise concluída!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
