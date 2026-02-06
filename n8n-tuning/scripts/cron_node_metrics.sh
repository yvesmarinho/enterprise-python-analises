#!/bin/bash
#
# Cron job para coletar métricas atômicas por node do N8N
# Executar a cada 5 minutos
#

# Diretório do projeto
PROJECT_DIR="/home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-analysis/n8n-tuning"

# Ambiente virtual Python
PYTHON_VENV="$PROJECT_DIR/.venv/bin/python"

# Log timestamp
echo "=== $(date '+%Y-%m-%d %H:%M:%S') - Iniciando coleta de métricas por node ===" >> "$PROJECT_DIR/logs/cron_node_metrics.log" 2>&1

# Ir para o diretório do projeto
cd "$PROJECT_DIR" || exit 1

# Executar coletor (últimas 6 horas, 500 execuções para ser mais leve)
"$PYTHON_VENV" scripts/n8n_node_metrics_exporter.py --backend prometheus >> "$PROJECT_DIR/logs/cron_node_metrics.log" 2>&1

# Status
if [ $? -eq 0 ]; then
    echo "✅ Coleta concluída com sucesso" >> "$PROJECT_DIR/logs/cron_node_metrics.log" 2>&1
else
    echo "❌ Erro na coleta" >> "$PROJECT_DIR/logs/cron_node_metrics.log" 2>&1
fi

echo "" >> "$PROJECT_DIR/logs/cron_node_metrics.log" 2>&1
