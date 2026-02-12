#!/usr/bin/env python3
"""
Script para corrigir datasource UIDs nos dashboards Grafana
"""

import json
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

def backup_dashboard(dashboard_path: Path, backup_dir: Path) -> Path:
    """Cria backup de um dashboard"""
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / dashboard_path.name
    shutil.copy2(dashboard_path, backup_path)
    return backup_path

def fix_datasource_uid(obj, old_uids: List[str], new_uid: str, changes: List[str]) -> int:
    """
    Recursivamente procura e substitui datasource UIDs em um objeto JSON
    Retorna o número de substituições feitas
    """
    count = 0

    if isinstance(obj, dict):
        # Verificar se é um datasource object
        if 'uid' in obj and 'type' in obj:
            old_uid = obj['uid']
            if old_uid in old_uids:
                obj['uid'] = new_uid
                changes.append(f"   Substituído: \"{old_uid}\" → \"{new_uid}\"")
                count += 1

        # Verificar datasource em nivel superior
        if 'datasource' in obj:
            ds = obj['datasource']
            if isinstance(ds, dict) and 'uid' in ds:
                old_uid = ds['uid']
                if old_uid in old_uids:
                    ds['uid'] = new_uid
                    changes.append(f"   Datasource object: \"{old_uid}\" → \"{new_uid}\"")
                    count += 1

        # Recursão em todos os valores
        for key, value in obj.items():
            count += fix_datasource_uid(value, old_uids, new_uid, changes)

    elif isinstance(obj, list):
        for item in obj:
            count += fix_datasource_uid(item, old_uids, new_uid, changes)

    return count

def set_datasource_if_missing(obj, default_uid: str, changes: List[str]) -> int:
    """
    Adiciona datasource aos painéis que não têm nenhum configurado
    Retorna o número de adições feitas
    """
    count = 0

    if isinstance(obj, dict):
        # Se é um painel (tem 'type' mas não é 'row')
        if 'type' in obj and obj['type'] != 'row':
            # Verificar se tem datasource
            if 'datasource' not in obj or obj['datasource'] is None:
                obj['datasource'] = {
                    'type': 'prometheus',
                    'uid': default_uid
                }
                panel_title = obj.get('title', 'Sem título')
                changes.append(f"   Adicionado datasource ao painel: \"{panel_title}\"")
                count += 1

            # Verificar targets
            if 'targets' in obj:
                for target in obj['targets']:
                    if isinstance(target, dict):
                        if 'datasource' not in target or target['datasource'] is None:
                            target['datasource'] = {
                                'type': 'prometheus',
                                'uid': default_uid
                            }
                            changes.append(f"   Adicionado datasource a target (painel: {panel_title})")
                            count += 1

        # Recursão
        for value in obj.values():
            count += set_datasource_if_missing(value, default_uid, changes)

    elif isinstance(obj, list):
        for item in obj:
            count += set_datasource_if_missing(item, default_uid, changes)

    return count

def fix_dashboard(dashboard_path: Path, target_uid: str, backup_dir: Path) -> Tuple[bool, str, List[str]]:
    """
    Corrige um dashboard individual
    Retorna (sucesso, mensagem, lista de mudanças)
    """
    changes = []

    try:
        # Ler dashboard
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            dashboard = json.load(f)

        dashboard_name = dashboard.get('title', dashboard_path.stem)

        # UIDs antigos conhecidos
        old_uids = [
            'prometheus',
            'Prometheus',
            'PROMETHEUS',
            'P4169E866C3094E38',
            'P8E9F73CDBD1F4933',
        ]

        # Remover o UID alvo da lista de antigos (caso seja o mesmo)
        if target_uid in old_uids:
            old_uids.remove(target_uid)

        # Backup ANTES de modificar
        backup_path = backup_dashboard(dashboard_path, backup_dir)
        changes.append(f"   Backup criado: {backup_path.name}")

        # Aplicar correções
        replacements = fix_datasource_uid(dashboard, old_uids, target_uid, changes)
        additions = set_datasource_if_missing(dashboard, target_uid, changes)

        total_changes = replacements + additions

        if total_changes > 0:
            # Salvar dashboard corrigido
            with open(dashboard_path, 'w', encoding='utf-8') as f:
                json.dump(dashboard, f, indent=2, ensure_ascii=False)

            return (True, f"✅ Corrigido: {total_changes} mudança(s)", changes)
        else:
            return (True, f"✅ Já estava correto", changes)

    except Exception as e:
        return (False, f"❌ Erro: {str(e)}", changes)

def main():
    # Configurações
    dashboards_dir = Path('/home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-analysis/n8n-prometheus-wfdb01/grafana_data/dashboards')
    backup_dir = dashboards_dir.parent / f"dashboards-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    target_uid = 'prometheus'  # UID padrão

    print("=" * 80)
    print("🔧 CORREÇÃO AUTOMÁTICA DE DASHBOARDS GRAFANA")
    print("=" * 80)
    print()
    print(f"📂 Diretório: {dashboards_dir}")
    print(f"💾 Backup: {backup_dir}")
    print(f"🎯 UID alvo: \"{target_uid}\"")
    print()

    # Confirmar antes de continuar
    print("⚠️  Este script irá:")
    print("   1. Criar backup de todos os dashboards")
    print("   2. Substituir datasource UIDs incorretos")
    print("   3. Adicionar datasource onde estiver faltando")
    print()

    response = input("Continuar? [s/N]: ").strip().lower()
    if response not in ['s', 'sim', 'y', 'yes']:
        print("❌ Operação cancelada pelo usuário")
        return

    print()
    print("=" * 80)
    print("🚀 INICIANDO CORREÇÕES")
    print("=" * 80)
    print()

    # Processar cada dashboard
    dashboards = sorted(dashboards_dir.glob('*.json'))
    results = []

    for i, dashboard_path in enumerate(dashboards, 1):
        print(f"[{i}/{len(dashboards)}] 📊 {dashboard_path.name}")

        success, message, changes = fix_dashboard(dashboard_path, target_uid, backup_dir)
        results.append((dashboard_path.name, success, message))

        print(f"      {message}")
        if changes:
            for change in changes[:5]:  # Mostrar até 5 mudanças
                print(change)
            if len(changes) > 5:
                print(f"      ... e mais {len(changes) - 5} mudança(s)")
        print()

    # Resumo
    print("=" * 80)
    print("📊 RESUMO DAS CORREÇÕES")
    print("=" * 80)
    print()

    successful = sum(1 for _, success, _ in results if success)
    failed = len(results) - successful

    print(f"✅ Sucesso: {successful}/{len(results)}")
    print(f"❌ Falhas: {failed}/{len(results)}")
    print()

    if successful > 0:
        print("✅ Dashboards corrigidos:")
        for name, success, message in results:
            if success and "Já estava correto" not in message:
                print(f"   • {name}")
        print()

    if failed > 0:
        print("❌ Dashboards com erro:")
        for name, success, message in results:
            if not success:
                print(f"   • {name}: {message}")
        print()

    # Próximos passos
    print("=" * 80)
    print("📋 PRÓXIMOS PASSOS")
    print("=" * 80)
    print()
    print("1. **Atualizar configuração do datasource:**")
    print("   Editar: n8n-prometheus-wfdb01/infrastructure/grafana/provisioning/datasources/victoria-metrics.yml")
    print("   Adicionar linha: uid: prometheus")
    print()
    print("2. **Reiniciar Grafana:**")
    print("   cd n8n-prometheus-wfdb01")
    print("   docker-compose restart grafana")
    print()
    print("3. **Validar no Grafana:**")
    print("   - Acessar: https://grafana.vya.digital")
    print("   - Verificar cada dashboard")
    print("   - Confirmar que dados são exibidos")
    print()
    print("4. **Se algo der errado:**")
    print(f"   Restaurar backup de: {backup_dir}")
    print()

    print("=" * 80)
    print("✅ SCRIPT CONCLUÍDO")
    print("=" * 80)

if __name__ == "__main__":
    main()
