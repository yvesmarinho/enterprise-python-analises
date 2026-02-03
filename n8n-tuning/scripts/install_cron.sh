#!/bin/bash
#
# Instala cron job para coleta de métricas N8N a cada 3 minutos
#

SCRIPT_PATH="/home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-analysis/n8n-tuning/scripts/cron_executions.sh"
LOG_PATH="/home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-analysis/n8n-tuning/logs/cron.log"

# Criar diretório de logs se não existir
mkdir -p "$(dirname "$LOG_PATH")"

# Linha do cron (a cada 3 minutos)
CRON_LINE="*/3 * * * * $SCRIPT_PATH >> $LOG_PATH 2>&1"

# Verificar se já existe
if crontab -l 2>/dev/null | grep -q "$SCRIPT_PATH"; then
    echo "⚠️  Cron job já existe!"
    echo "Para remover: crontab -l | grep -v 'cron_executions.sh' | crontab -"
else
    # Adicionar ao crontab
    (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
    echo "✅ Cron job instalado com sucesso!"
    echo "   Executará a cada 3 minutos"
    echo "   Logs em: $LOG_PATH"
    echo ""
    echo "Para verificar: crontab -l"
    echo "Para remover: crontab -l | grep -v 'cron_executions.sh' | crontab -"
fi
