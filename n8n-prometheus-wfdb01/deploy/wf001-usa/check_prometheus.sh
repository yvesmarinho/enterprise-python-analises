#!/bin/bash
#
# Script para verificar integração do Collector API com Prometheus
# Servidor: wf001-usa
#

set -e

echo "============================================"
echo "🔍 Verificação Prometheus - wf001-usa"
echo "============================================"
echo ""

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configurações
PUSHGATEWAY_URL="https://prometheus.vya.digital/pushgateway"
JOB_NAME="collector_api_wf001_usa"
CONTAINER_NAME="prod-collector-api"

# Função para verificar status
check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ OK${NC}"
        return 0
    else
        echo -e "${RED}❌ FALHOU${NC}"
        return 1
    fi
}

# 1. Verificar se container está rodando
echo -n "1. Container collector-api rodando... "
docker ps --filter "name=${CONTAINER_NAME}" --format "{{.Names}}" | grep -q "${CONTAINER_NAME}"
check_status

# 2. Verificar conectividade com Pushgateway
echo -n "2. Conectividade com Pushgateway... "
curl -s -o /dev/null -w "%{http_code}" "${PUSHGATEWAY_URL}" | grep -q "200"
check_status

# 3. Verificar variáveis de ambiente
echo ""
echo "3. Variáveis de Ambiente do Container:"
docker exec ${CONTAINER_NAME} env | grep PROMETHEUS || echo -e "${YELLOW}⚠️  Variáveis PROMETHEUS não encontradas${NC}"

# 4. Verificar logs do Prometheus Pusher
echo ""
echo "4. Logs recentes (últimas 10 linhas com 'prometheus'):"
docker logs ${CONTAINER_NAME} 2>&1 | grep -i prometheus | tail -10 || echo -e "${YELLOW}⚠️  Nenhum log de prometheus encontrado${NC}"

# 5. Verificar métricas locais
echo ""
echo -n "5. Endpoint de métricas local (/metrics)... "
curl -s http://localhost:9102/metrics > /dev/null
check_status

# 6. Verificar métricas no Pushgateway
echo ""
echo "6. Métricas no Pushgateway Remoto:"
echo -n "   Buscando job '${JOB_NAME}'... "
METRICS=$(curl -s "${PUSHGATEWAY_URL}/metrics" | grep "job=\"${JOB_NAME}\"" | wc -l)

if [ "$METRICS" -gt 0 ]; then
    echo -e "${GREEN}✅ Encontradas ${METRICS} métricas${NC}"
    echo ""
    echo "   Exemplos de métricas:"
    curl -s "${PUSHGATEWAY_URL}/metrics" | grep "job=\"${JOB_NAME}\"" | head -5
else
    echo -e "${RED}❌ Nenhuma métrica encontrada${NC}"
    echo -e "${YELLOW}   Possíveis causas:${NC}"
    echo "   - Container iniciou recentemente (aguardar 60s)"
    echo "   - Erro de conectividade com o Pushgateway"
    echo "   - Configuração incorreta do PROMETHEUS_PUSHGATEWAY_URL"
fi

# 7. Testar envio manual
echo ""
echo "7. Teste de Envio Manual:"
read -p "   Deseja forçar um push de métricas agora? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "   Reiniciando container para forçar envio..."
    docker-compose restart collector-api
    echo "   Aguardando 10 segundos..."
    sleep 10
    echo -n "   Verificando métricas..."
    METRICS_AFTER=$(curl -s "${PUSHGATEWAY_URL}/metrics" | grep "job=\"${JOB_NAME}\"" | wc -l)
    if [ "$METRICS_AFTER" -gt 0 ]; then
        echo -e " ${GREEN}✅ ${METRICS_AFTER} métricas encontradas${NC}"
    else
        echo -e " ${RED}❌ Ainda sem métricas${NC}"
    fi
fi

# 8. Resumo
echo ""
echo "============================================"
echo "📊 RESUMO"
echo "============================================"
echo "Pushgateway URL: ${PUSHGATEWAY_URL}"
echo "Job Name: ${JOB_NAME}"
echo "Container: ${CONTAINER_NAME}"
echo ""
echo "🔗 Links úteis:"
echo "   Pushgateway: ${PUSHGATEWAY_URL}"
echo "   Prometheus: http://wfdb01.vya.digital:9090"
echo "   Métricas locais: http://localhost:9102/metrics"
echo ""
echo "📖 Documentação: ./PROMETHEUS_CONFIG.md"
echo "============================================"
