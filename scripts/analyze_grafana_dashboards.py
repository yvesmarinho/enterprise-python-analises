#!/usr/bin/env python3
"""
Script para analisar dashboards Grafana e identificar problemas com datasources
"""

import json
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set

def analyze_dashboard(dashboard_path: Path) -> Dict:
    """Analisa um dashboard e extrai informações sobre datasources"""

    with open(dashboard_path, 'r', encoding='utf-8') as f:
        dashboard = json.load(f)

    datasource_uids = set()
    datasource_types = set()
    panels_total = 0
    panels_with_queries = 0

    # Analisar painéis
    panels = dashboard.get('panels', [])

    def process_panel(panel):
        nonlocal panels_total, panels_with_queries

        if panel.get('type') == 'row':
            # Rows podem ter painéis aninhados
            for sub_panel in panel.get('panels', []):
                process_panel(sub_panel)
            return

        panels_total += 1

        # Extrair datasource do painel
        datasource = panel.get('datasource')
        if datasource:
            if isinstance(datasource, dict):
                uid = datasource.get('uid')
                ds_type = datasource.get('type')
                if uid:
                    datasource_uids.add(uid)
                if ds_type:
                    datasource_types.add(ds_type)

        # Verificar targets/queries
        targets = panel.get('targets', [])
        if targets:
            panels_with_queries += 1
            for target in targets:
                if isinstance(target, dict):
                    target_ds = target.get('datasource')
                    if target_ds and isinstance(target_ds, dict):
                        uid = target_ds.get('uid')
                        ds_type = target_ds.get('type')
                        if uid:
                            datasource_uids.add(uid)
                        if ds_type:
                            datasource_types.add(ds_type)

    for panel in panels:
        process_panel(panel)

    # Analisar templating/variables
    templating_datasources = set()
    templating = dashboard.get('templating', {})
    for var in templating.get('list', []):
        if var.get('type') == 'datasource':
            query = var.get('query', '')
            if query:
                templating_datasources.add(query)

    return {
        'name': dashboard.get('title', 'Unknown'),
        'id': dashboard.get('id', 'N/A'),
        'uid': dashboard.get('uid', 'N/A'),
        'datasource_uids': list(datasource_uids),
        'datasource_types': list(datasource_types),
        'templating_datasources': list(templating_datasources),
        'panels_total': panels_total,
        'panels_with_queries': panels_with_queries,
        'editable': dashboard.get('editable', False),
    }

def main():
    dashboards_dir = Path('/home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-analysis/n8n-prometheus-wfdb01/grafana_data/dashboards')

    if not dashboards_dir.exists():
        print(f"❌ Diretório não encontrado: {dashboards_dir}")
        return

    print("=" * 80)
    print("📊 ANÁLISE DE DASHBOARDS GRAFANA")
    print("=" * 80)
    print(f"Diretório: {dashboards_dir}")
    print()

    # Analisar todos os dashboards
    dashboards = []
    all_datasource_uids = set()

    for json_file in sorted(dashboards_dir.glob('*.json')):
        try:
            result = analyze_dashboard(json_file)
            result['file'] = json_file.name
            dashboards.append(result)
            all_datasource_uids.update(result['datasource_uids'])
        except Exception as e:
            print(f"❌ Erro ao analisar {json_file.name}: {e}")

    print(f"📋 Total de dashboards encontrados: {len(dashboards)}")
    print()

    # Resumo de datasources utilizados
    print("=" * 80)
    print("🔌 DATASOURCES UTILIZADOS NOS DASHBOARDS")
    print("=" * 80)
    print()

    uid_usage = defaultdict(list)
    for dash in dashboards:
        for uid in dash['datasource_uids']:
            uid_usage[uid].append(dash['name'])

    if uid_usage:
        for uid in sorted(uid_usage.keys()):
            dashboards_using = uid_usage[uid]
            print(f"UID: \"{uid}\"")
            print(f"   Usado em {len(dashboards_using)} dashboard(s):")
            for dash_name in dashboards_using[:5]:
                print(f"      • {dash_name}")
            if len(dashboards_using) > 5:
                print(f"      ... e mais {len(dashboards_using) - 5}")
            print()
    else:
        print("⚠️  Nenhum datasource UID encontrado!")
        print()

    # Análise detalhada por dashboard
    print("=" * 80)
    print("📂 DASHBOARDS INDIVIDUAIS")
    print("=" * 80)
    print()

    for dash in dashboards:
        print(f"📊 {dash['name']}")
        print(f"   Arquivo: {dash['file']}")
        print(f"   ID: {dash['id']} | UID: {dash['uid']}")
        print(f"   Painéis: {dash['panels_total']} ({dash['panels_with_queries']} com queries)")
        print(f"   Editável: {'✅ Sim' if dash['editable'] else '❌ Não'}")

        if dash['datasource_uids']:
            print(f"   Datasources UIDs:")
            for uid in sorted(set(dash['datasource_uids'])):
                print(f"      • \"{uid}\"")
        else:
            print(f"   ⚠️  Nenhum datasource UID configurado")

        if dash['datasource_types']:
            print(f"   Tipos de datasource:")
            for ds_type in sorted(set(dash['datasource_types'])):
                print(f"      • {ds_type}")

        if dash['templating_datasources']:
            print(f"   Variables de datasource:")
            for ds in dash['templating_datasources']:
                print(f"      • {ds}")

        print()

    # Problemas identificados
    print("=" * 80)
    print("⚠️  PROBLEMAS IDENTIFICADOS")
    print("=" * 80)
    print()

    problems = []

    # Problema 1: Múltiplos UIDs diferentes (case-sensitive)
    lowercase_uids = {uid.lower() for uid in all_datasource_uids}
    if len(lowercase_uids) < len(all_datasource_uids):
        problems.append({
            'type': 'case_sensitivity',
            'description': 'UIDs com diferentes capitalizações',
            'uids': list(all_datasource_uids),
        })

    # Problema 2: Dashboards sem queries
    dashboards_no_queries = [d for d in dashboards if d['panels_with_queries'] == 0 and d['panels_total'] > 0]
    if dashboards_no_queries:
        problems.append({
            'type': 'no_queries',
            'description': 'Dashboards com painéis mas sem queries',
            'dashboards': [d['name'] for d in dashboards_no_queries],
        })

    # Problema 3: Dashboards sem datasource configurado
    dashboards_no_ds = [d for d in dashboards if not d['datasource_uids'] and d['panels_total'] > 0]
    if dashboards_no_ds:
        problems.append({
            'type': 'no_datasource',
            'description': 'Dashboards sem datasource configurado',
            'dashboards': [d['name'] for d in dashboards_no_ds],
        })

    if problems:
        for i, problem in enumerate(problems, 1):
            print(f"{i}. ⚠️  {problem['description']}")

            if problem['type'] == 'case_sensitivity':
                print(f"   UIDs encontrados:")
                for uid in problem['uids']:
                    print(f"      • \"{uid}\"")
                print()
                print(f"   💡 Solução: Padronizar todos os UIDs (recomendado: minúsculas)")

            elif problem['type'] == 'no_queries':
                print(f"   Dashboards afetados:")
                for dash_name in problem['dashboards']:
                    print(f"      • {dash_name}")
                print()
                print(f"   💡 Solução: Verificar se os painéis têm queries configuradas")

            elif problem['type'] == 'no_datasource':
                print(f"   Dashboards afetados:")
                for dash_name in problem['dashboards']:
                    print(f"      • {dash_name}")
                print()
                print(f"   💡 Solução: Configurar datasource nos painéis")

            print()
    else:
        print("✅ Nenhum problema óbvio identificado na estrutura dos dashboards")
        print()

    # Recomendações
    print("=" * 80)
    print("💡 RECOMENDAÇÕES")
    print("=" * 80)
    print()

    print("1. **Verificar Datasource no Grafana**")
    print("   - Acessar: https://grafana.vya.digital/datasources")
    print("   - Verificar qual é o UID correto do Prometheus datasource")
    print("   - Comparar com os UIDs encontrados nos dashboards")
    print()

    print("2. **Padronizar UIDs nos Dashboards**")
    print("   - Use o UID correto do datasource configurado no Grafana")
    print("   - Recomendado: usar minúsculas (\"prometheus\")")
    print("   - Evitar variações: \"prometheus\", \"Prometheus\", \"PROMETHEUS\"")
    print()

    print("3. **Verificar Conectividade do Prometheus**")
    print("   - Testar: https://prometheus.vya.digital/api/v1/query?query=up")
    print("   - Verificar se o Grafana consegue acessar o Prometheus")
    print()

    print("4. **Verificar Time Range**")
    print("   - Dashboards precisam de dados no período selecionado")
    print("   - Testar com \"Last 24 hours\" ou \"Last 7 days\"")
    print()

    # Comando para corrigir UIDs
    if 'prometheus' in all_datasource_uids or 'Prometheus' in all_datasource_uids:
        print("=" * 80)
        print("🔧 SCRIPT DE CORREÇÃO")
        print("=" * 80)
        print()
        print("Para padronizar os UIDs, você pode criar um script que substitua:")
        print()

        unique_uids = sorted(all_datasource_uids)
        if len(unique_uids) > 1:
            print("Substituições recomendadas:")
            target_uid = "prometheus"  # UID alvo
            for uid in unique_uids:
                if uid != target_uid:
                    print(f'   sed -i \'s/"uid": "{uid}"/"uid": "{target_uid}"/g\' *.json')
        print()

if __name__ == "__main__":
    main()
