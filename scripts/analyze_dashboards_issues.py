#!/usr/bin/env python3
"""
Analisa todos os dashboards do Grafana para identificar problemas.
Data: 03/03/2026
"""

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List


def analyze_dashboard(dashboard_path: Path) -> Dict[str, Any]:
    """Analisa um dashboard e retorna informações sobre problemas."""

    with open(dashboard_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    issues = []
    datasource_uids = set()

    # Informações básicas
    dashboard_title = data.get('title', 'Unknown')
    total_panels = len(data.get('panels', []))

    # Analisar painéis
    panels_with_datasource = 0
    panels_without_datasource = 0
    panels_with_targets = 0
    panels_with_queries = 0

    for panel in data.get('panels', []):
        # Verificar se é row (container)
        if panel.get('type') == 'row':
            continue

        # Verificar datasource
        if 'datasource' in panel:
            panels_with_datasource += 1
            ds = panel['datasource']

            if isinstance(ds, dict):
                uid = ds.get('uid', '')
                datasource_uids.add(uid)

                if not uid:
                    issues.append(f"Panel '{panel.get('title', 'untitled')}': datasource sem UID")
            elif isinstance(ds, str):
                datasource_uids.add(ds)
        else:
            panels_without_datasource += 1
            issues.append(f"Panel '{panel.get('title', 'untitled')}': SEM datasource configurado")

        # Verificar targets/queries
        targets = panel.get('targets', [])
        if targets:
            panels_with_targets += 1
            for target in targets:
                if target.get('expr') or target.get('rawSql'):
                    panels_with_queries += 1
                    break

    # Verificar datasource no nível do dashboard
    dashboard_ds = data.get('__inputs', [])
    templating_vars = data.get('templating', {}).get('list', [])

    return {
        'file': dashboard_path.name,
        'title': dashboard_title,
        'total_panels': total_panels,
        'panels_with_datasource': panels_with_datasource,
        'panels_without_datasource': panels_without_datasource,
        'panels_with_targets': panels_with_targets,
        'panels_with_queries': panels_with_queries,
        'datasource_uids': sorted(list(datasource_uids)),
        'issues': issues,
        'has_inputs': len(dashboard_ds) > 0,
        'templating_vars': len(templating_vars)
    }

def main():
    """Analisa todos os dashboards."""

    # Buscar dashboards em várias localizações
    base_path = Path('/home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-analysis')

    dashboard_locations = [
        base_path / 'n8n-prometheus-wfdb01' / 'grafana' / 'dashboards',
        base_path / 'n8n-prometheus-wfdb01' / 'grafana_data' / 'dashboards',
        base_path / 'n8n-tuning' / 'docker' / 'grafana' / 'dashboards',
    ]

    all_dashboards = []

    for location in dashboard_locations:
        if location.exists():
            for dashboard_file in location.glob('*.json'):
                all_dashboards.append(dashboard_file)

    print("=" * 80)
    print("🔍 ANÁLISE DE DASHBOARDS DO GRAFANA")
    print(f"📅 Data: 03/03/2026")
    print(f"📁 Dashboards encontrados: {len(all_dashboards)}")
    print("=" * 80)
    print()

    results = []

    for dashboard_path in sorted(all_dashboards):
        try:
            result = analyze_dashboard(dashboard_path)
            results.append(result)
        except Exception as e:
            print(f"❌ Erro ao analisar {dashboard_path.name}: {e}")

    # Agrupar por tipo de problema
    dashboards_sem_datasource = []
    dashboards_uid_incorreto = []
    dashboards_ok = []

    print("\n" + "=" * 80)
    print("📊 RESUMO DETALHADO POR DASHBOARD")
    print("=" * 80)

    for result in results:
        print(f"\n📄 Dashboard: {result['title']}")
        print(f"   Arquivo: {result['file']}")
        print(f"   Painéis totais: {result['total_panels']}")
        print(f"   Painéis com datasource: {result['panels_with_datasource']}")
        print(f"   Painéis SEM datasource: {result['panels_without_datasource']}")
        print(f"   Painéis com queries: {result['panels_with_queries']}")
        print(f"   UIDs usados: {result['datasource_uids']}")

        if result['issues']:
            print(f"   ⚠️  Problemas encontrados: {len(result['issues'])}")
            for issue in result['issues'][:3]:  # Mostrar apenas 3 primeiros
                print(f"      - {issue}")
            if len(result['issues']) > 3:
                print(f"      ... e mais {len(result['issues']) - 3} problemas")
        else:
            print(f"   ✅ Nenhum problema detectado")

        # Classificar
        if result['panels_without_datasource'] > 0:
            dashboards_sem_datasource.append(result)
        elif result['datasource_uids'] and any(uid not in ['prometheus', 'victoriametrics'] for uid in result['datasource_uids']):
            dashboards_uid_incorreto.append(result)
        else:
            dashboards_ok.append(result)

    # Resumo final
    print("\n" + "=" * 80)
    print("📈 RESUMO GERAL")
    print("=" * 80)
    print(f"\n✅ Dashboards OK: {len(dashboards_ok)}")
    for d in dashboards_ok:
        print(f"   - {d['title']}")

    print(f"\n⚠️  Dashboards SEM datasource configurado: {len(dashboards_sem_datasource)}")
    for d in dashboards_sem_datasource:
        print(f"   - {d['title']} ({d['panels_without_datasource']} painéis)")

    print(f"\n❌ Dashboards com UID incorreto: {len(dashboards_uid_incorreto)}")
    for d in dashboards_uid_incorreto:
        print(f"   - {d['title']}: {d['datasource_uids']}")

    # UIDs únicos encontrados
    all_uids = set()
    for result in results:
        all_uids.update(result['datasource_uids'])

    print(f"\n🔑 UIDs únicos encontrados: {sorted(all_uids)}")

    print("\n" + "=" * 80)
    print("📝 DATASOURCE PROVISIONADO NO SERVIDOR")
    print("=" * 80)
    print("Nome: VictoriaMetrics")
    print("Tipo: prometheus")
    print("UID: (não definido - gerado automaticamente pelo Grafana)")
    print("⚠️  PROBLEMA: Sem UID explícito, cada restart pode gerar UID diferente")

    print("\n" + "=" * 80)

    return results

if __name__ == '__main__':
    results = main()
