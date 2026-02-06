#!/bin/bash
#
# N8N Metrics Collector - Executa coleta de métricas
# Para usar no cron: */3 * * * * /path/to/cron_executions.sh >> /path/to/logs/cron.log 2>&1
#

# Diretório base do projeto
PROJECT_DIR="/home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-analysis/n8n-tuning"
PYTHON_VENV="/home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-analysis/.venv/bin/python"

# Mudar para o diretório do projeto
cd "$PROJECT_DIR" || exit 1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🚀 Iniciando coleta de métricas..."

# 1. Executar o exporter de métricas gerais (workflows e execuções)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 📊 Coletando métricas gerais..."
"$PYTHON_VENV" "$PROJECT_DIR/scripts/n8n_metrics_exporter.py" --backend prometheus

# Verificar exit code
if [ $? -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ Métricas gerais coletadas com sucesso"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ Erro na coleta de métricas gerais"
fi

# 2. Executar o exporter de métricas atômicas por node (banco PostgreSQL)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🔍 Coletando métricas atômicas por node..."
"$PYTHON_VENV" "$PROJECT_DIR/scripts/n8n_node_metrics_exporter.py" --backend prometheus

# Verificar exit code
if [ $? -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ Métricas por node coletadas com sucesso"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ Erro na coleta de métricas por node"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ Coleta de métricas concluída"
