#!/usr/bin/env python3
"""Script simples para corrigir UIDs dos datasources nos dashboards"""

import json
from pathlib import Path

dashboards_dir = Path('/home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-analysis/n8n-prometheus-wfdb01/grafana_data/dashboards')

# Dashboards para corrigir
files_to_fix = {
    'wfdb02 - MySQL Dashboard-1770665439838.json': ('Prometheus', 'prometheus'),
    'n8n-node-performance.json': ('P4169E866C3094E38', 'prometheus'),
}

for filename, (old_uid, new_uid) in files_to_fix.items():
    filepath = dashboards_dir / filename

    if not filepath.exists():
        print(f"❌ Arquivo não encontrado: {filename}")
        continue

    print(f"🔧 Processando: {filename}")

    # Ler arquivo como texto
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Contar ocorrências
    old_pattern = f'"uid": "{old_uid}"'
    new_pattern = f'"uid": "{new_uid}"'
    count = content.count(old_pattern)

    if count == 0:
        print(f"   ⚠️  UID '{old_uid}' não encontrado")
        continue

    # Substituir
    new_content = content.replace(old_pattern, new_pattern)

    # Salvar
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"   ✅ Substituídas {count} ocorrências: '{old_uid}' → '{new_uid}'")

print("\n✅ Correção concluída!")
