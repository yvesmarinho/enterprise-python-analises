#!/bin/bash
# Script para organizar dashboards em pastas
# Data: 03/03/2026

set -e

DASHBOARD_DIR="/home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-analysis/n8n-prometheus-wfdb01/grafana/dashboards"

echo "📁 Organizando dashboards em pastas..."
cd "$DASHBOARD_DIR"

# Criar pastas
mkdir -p N8N MySQL PostgreSQL Docker

# Mover dashboards N8N
echo "  📊 Movendo dashboards N8N..."
mv n8n-*.json N8N/ 2>/dev/null || true

# Mover dashboards MySQL
echo "  🗄️  Movendo dashboards MySQL..."
mv *MySQL*.json MySQL/ 2>/dev/null || true
mv *mysql*.json MySQL/ 2>/dev/null || true

# Mover dashboards PostgreSQL
echo "  🐘 Movendo dashboards PostgreSQL..."
mv *PostgreSQL*.json PostgreSQL/ 2>/dev/null || true
mv *postgres*.json PostgreSQL/ 2>/dev/null || true

# Mover dashboards Docker
echo "  🐳 Movendo dashboards Docker..."
mv wf008*.json Docker/ 2>/dev/null || true
mv *Docker*.json Docker/ 2>/dev/null || true

echo "✅ Organização concluída!"
echo ""
echo "Estrutura final:"
find . -maxdepth 2 -name "*.json" | sort

