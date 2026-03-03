#!/usr/bin/env python3
"""
Script para corrigir dashboards Grafana com datasources ausentes ou incorretos.
Data: 03/03/2026
Autor: Enterprise DevOps Team
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Datasource correto para usar
CORRECT_DATASOURCE = {
    "type": "prometheus",
    "uid": "prometheus"
}

# UID incorreto que deve ser substituído
INCORRECT_UID = "P4169E866C3094E38"


def fix_panel_datasource(panel: Dict[str, Any]) -> bool:
    """
    Corrige o datasource de um painel.
    Retorna True se o painel foi modificado.
    """
    modified = False

    # Skip rows (containers)
    if panel.get('type') == 'row':
        return False

    # Verificar se o painel tem datasource
    current_ds = panel.get('datasource')

    # Caso 1: Sem datasource
    if not current_ds:
        panel['datasource'] = CORRECT_DATASOURCE.copy()
        modified = True
        print(f"  ✅ Painel '{panel.get('title', 'untitled')}': datasource adicionado")

    # Caso 2: Datasource é dict
    elif isinstance(current_ds, dict):
        uid = current_ds.get('uid', '')

        # Corrigir UID incorreto
        if uid == INCORRECT_UID:
            current_ds['uid'] = 'prometheus'
            current_ds['type'] = 'prometheus'
            modified = True
            print(f"  ✅ Painel '{panel.get('title', 'untitled')}': UID corrigido de {INCORRECT_UID} para prometheus")

        # Garantir que tem type
        elif not current_ds.get('type'):
            current_ds['type'] = 'prometheus'
            modified = True

    # Caso 3: Datasource é string
    elif isinstance(current_ds, str):
        if current_ds == INCORRECT_UID:
            panel['datasource'] = CORRECT_DATASOURCE.copy()
            modified = True
            print(f"  ✅ Painel '{panel.get('title', 'untitled')}': UID string corrigido")

    return modified


def fix_dashboard(dashboard_path: Path, dry_run: bool = False) -> Tuple[bool, int]:
    """
    Corrige datasources em um dashboard.
    Retorna (modificado, numero_de_paineis_corrigidos).
    """
    print(f"\n📄 Processando: {dashboard_path.name}")

    try:
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"  ❌ Erro ao ler arquivo: {e}")
        return False, 0

    dashboard_title = data.get('title', 'Unknown')
    print(f"  Título: {dashboard_title}")

    panels_fixed = 0
    total_panels = 0

    # Processar painéis
    for panel in data.get('panels', []):
        total_panels += 1
        if fix_panel_datasource(panel):
            panels_fixed += 1

        # Processar sub-painéis (se existirem)
        for sub_panel in panel.get('panels', []):
            total_panels += 1
            if fix_panel_datasource(sub_panel):
                panels_fixed += 1

    # Mostrar resultado
    if panels_fixed > 0:
        print(f"  📊 Painéis corrigidos: {panels_fixed}/{total_panels}")

        if not dry_run:
            # Salvar dashboard corrigido
            try:
                with open(dashboard_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"  💾 Arquivo salvo com sucesso")
                return True, panels_fixed
            except Exception as e:
                print(f"  ❌ Erro ao salvar arquivo: {e}")
                return False, 0
        else:
            print(f"  ⚠️  DRY RUN - Mudanças não salvas")
            return True, panels_fixed
    else:
        print(f"  ✅ Nenhuma correção necessária ({total_panels} painéis OK)")
        return False, 0


def main():
    """Função principal."""

    # Configuração
    dry_run = '--dry-run' in sys.argv

    base_path = Path('/home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-analysis')

    # Localizações de dashboards para corrigir
    dashboard_locations = [
        base_path / 'n8n-prometheus-wfdb01' / 'grafana' / 'dashboards',
        base_path / 'n8n-prometheus-wfdb01' / 'grafana_data' / 'dashboards',
        base_path / 'n8n-tuning' / 'docker' / 'grafana' / 'dashboards',
    ]

    # Dashboards N8N específicos para corrigir
    n8n_dashboard_names = [
        'n8n-performance-overview.json',
        'n8n-performance-detailed.json',
        'n8n-node-performance.json',
    ]

    print("=" * 80)
    print("🔧 CORREÇÃO DE DASHBOARDS GRAFANA")
    print(f"📅 Data: 03/03/2026")
    print(f"🎯 Modo: {'DRY RUN (simulação)' if dry_run else 'PRODUÇÃO (aplicar mudanças)'}")
    print("=" * 80)

    total_dashboards_found = 0
    total_dashboards_fixed = 0
    total_panels_fixed = 0

    # Processar cada localização
    for location in dashboard_locations:
        if not location.exists():
            print(f"\n⚠️  Localização não encontrada: {location}")
            continue

        print(f"\n📁 Localização: {location}")

        # Processar apenas dashboards N8N
        for dashboard_name in n8n_dashboard_names:
            dashboard_path = location / dashboard_name

            if dashboard_path.exists():
                total_dashboards_found += 1
                modified, panels_fixed = fix_dashboard(dashboard_path, dry_run)

                if modified:
                    total_dashboards_fixed += 1
                    total_panels_fixed += panels_fixed

    # Resumo final
    print("\n" + "=" * 80)
    print("📈 RESUMO FINAL")
    print("=" * 80)
    print(f"Dashboards encontrados: {total_dashboards_found}")
    print(f"Dashboards corrigidos: {total_dashboards_fixed}")
    print(f"Painéis corrigidos: {total_panels_fixed}")

    if dry_run:
        print("\n⚠️  Este foi um DRY RUN. Nenhuma mudança foi salva.")
        print("Execute sem --dry-run para aplicar as correções.")
    else:
        print(f"\n✅ Correções aplicadas com sucesso!")
        print(f"💾 {total_dashboards_fixed} arquivos modificados")

    print("=" * 80)

    return 0 if total_dashboards_fixed > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
