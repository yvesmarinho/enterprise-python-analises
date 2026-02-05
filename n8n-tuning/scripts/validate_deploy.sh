#!/bin/bash
#
# Script de Validação do Deploy
# Verifica se tudo está funcionando corretamente
#

set -e

echo "🔍 VALIDAÇÃO DO DEPLOY DO N8N MONITORING"
echo "========================================"
echo ""

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Diretório do projeto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Contadores
PASSED=0
FAILED=0
WARNINGS=0

# Função para testar
test_check() {
    local description="$1"
    local command="$2"
    local expected="$3"
    
    echo -n "Verificando: $description... "
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ OK${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ FALHOU${NC}"
        ((FAILED++))
    fi
}

# Função para avisos
test_warning() {
    local description="$1"
    local command="$2"
    
    echo -n "Verificando: $description... "
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ OK${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠️ AVISO${NC}"
        ((WARNINGS++))
    fi
}

echo "1️⃣ VERIFICAÇÕES DE ARQUIVOS"
echo "----------------------------"

test_check "Arquivo de credenciais existe" "test -f .secrets/credentials.json"
test_check "Docker Compose existe" "test -f docker/docker-compose.yml"
test_check "Scripts Python existem" "test -f scripts/n8n_metrics_exporter.py"
test_check "Dashboards do Grafana existem" "test -d docker/grafana/dashboards"
test_check "Provisioning do Grafana existe" "test -d docker/grafana/provisioning"

echo ""
echo "2️⃣ VERIFICAÇÕES DE CONTAINERS"
echo "------------------------------"

test_check "VictoriaMetrics rodando" "docker ps | grep -q n8n-victoria-metrics"
test_check "Grafana rodando" "docker ps | grep -q n8n-grafana"
test_check "VictoriaMetrics health" "curl -sf http://localhost:8428/health"
test_check "Grafana health" "curl -sf http://localhost:3100/api/health"

echo ""
echo "3️⃣ VERIFICAÇÕES DE CREDENCIAIS"
echo "--------------------------------"

if [ -f .secrets/credentials.json ]; then
    # Verificar se as credenciais não estão com valores default
    if grep -q "SUBSTITUA_COM" .secrets/credentials.json; then
        echo -e "❌ Credenciais ainda não foram configuradas"
        ((FAILED++))
    else
        # Carregar credenciais
        N8N_URL=$(jq -r '.n8n.url' .secrets/credentials.json)
        N8N_KEY=$(jq -r '.n8n.api_key' .secrets/credentials.json)
        PG_HOST=$(jq -r '.postgresql.host' .secrets/credentials.json)
        PG_USER=$(jq -r '.postgresql.user' .secrets/credentials.json)
        PG_PASS=$(jq -r '.postgresql.password' .secrets/credentials.json)
        PG_DB=$(jq -r '.postgresql.database' .secrets/credentials.json)
        
        # Testar conexão N8N
        test_check "Conexão N8N API" "curl -sf -H 'X-N8N-API-KEY: $N8N_KEY' '$N8N_URL/api/v1/workflows'"
        
        # Testar conexão PostgreSQL (requer psql)
        test_warning "Conexão PostgreSQL" "PGPASSWORD='$PG_PASS' psql -h $PG_HOST -U $PG_USER -d $PG_DB -c 'SELECT 1' -t"
    fi
else
    echo -e "${RED}❌ Arquivo de credenciais não encontrado${NC}"
    ((FAILED++))
fi

echo ""
echo "4️⃣ VERIFICAÇÕES DE CRON"
echo "------------------------"

test_warning "Cron job instalado" "crontab -l | grep -q cron_executions.sh"
test_warning "Logs de cron existem" "test -f logs/cron.log"

if [ -f logs/cron.log ]; then
    LAST_RUN=$(tail -1 logs/cron.log | grep -oP '\[\K[^\]]+' || echo "nunca")
    echo "  Última execução: $LAST_RUN"
fi

echo ""
echo "5️⃣ VERIFICAÇÕES DE DADOS"
echo "-------------------------"

# Verificar se VictoriaMetrics tem métricas
METRICS_COUNT=$(curl -s 'http://localhost:8428/api/v1/labels' 2>/dev/null | jq '.data | length' || echo "0")

if [ "$METRICS_COUNT" -gt "0" ]; then
    echo -e "Métricas no VictoriaMetrics: ${GREEN}$METRICS_COUNT labels${NC}"
    ((PASSED++))
else
    echo -e "Métricas no VictoriaMetrics: ${YELLOW}0 labels (aguarde cron executar)${NC}"
    ((WARNINGS++))
fi

# Comparar workflows API vs VictoriaMetrics
if [ -n "$N8N_KEY" ] && [ -n "$N8N_URL" ]; then
    API_WORKFLOWS=$(curl -s -H "X-N8N-API-KEY: $N8N_KEY" "$N8N_URL/api/v1/workflows" 2>/dev/null | jq '.data | length' || echo "0")
    VM_WORKFLOWS=$(curl -s 'http://localhost:8428/api/v1/query?query=count(n8n_workflow_info)' 2>/dev/null | jq -r '.data.result[0].value[1]' || echo "0")
    
    echo "Workflows na API N8N: $API_WORKFLOWS"
    echo "Workflows no VictoriaMetrics: $VM_WORKFLOWS"
    
    if [ "$API_WORKFLOWS" == "$VM_WORKFLOWS" ] && [ "$API_WORKFLOWS" != "0" ]; then
        echo -e "${GREEN}✅ Dados consistentes${NC}"
        ((PASSED++))
    elif [ "$VM_WORKFLOWS" == "0" ]; then
        echo -e "${YELLOW}⚠️ Aguardando primeira coleta de dados${NC}"
        ((WARNINGS++))
    else
        echo -e "${YELLOW}⚠️ Divergência detectada (pode ser timing de coleta)${NC}"
        ((WARNINGS++))
    fi
fi

echo ""
echo "6️⃣ VERIFICAÇÕES DE GRAFANA"
echo "---------------------------"

# Verificar datasources (requer autenticação)
test_warning "Grafana datasources" "curl -sf -u admin:W123Mudar http://localhost:3100/api/datasources | jq -e '.[] | select(.name==\"VictoriaMetrics\")'"

# Contar dashboards
DASHBOARDS_COUNT=$(find docker/grafana/dashboards -name "*.json" 2>/dev/null | wc -l || echo "0")
echo "Dashboards encontrados: $DASHBOARDS_COUNT"

if [ "$DASHBOARDS_COUNT" -ge "3" ]; then
    echo -e "${GREEN}✅ Todos os dashboards presentes${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Faltam dashboards (esperado: 3)${NC}"
    ((FAILED++))
fi

echo ""
echo "7️⃣ VERIFICAÇÕES DE PYTHON"
echo "--------------------------"

if [ -d .venv ]; then
    test_check "Ambiente virtual Python" "test -x .venv/bin/python"
    
    if [ -x .venv/bin/python ]; then
        test_check "Módulo requests instalado" ".venv/bin/python -c 'import requests'"
        test_warning "Módulo psycopg2 instalado" ".venv/bin/python -c 'import psycopg2'"
    fi
else
    echo -e "${RED}❌ Ambiente virtual Python não encontrado${NC}"
    ((FAILED++))
fi

echo ""
echo "========================================"
echo "📊 RESUMO DA VALIDAÇÃO"
echo "========================================"
echo -e "${GREEN}✅ Passou: $PASSED${NC}"
echo -e "${YELLOW}⚠️ Avisos: $WARNINGS${NC}"
echo -e "${RED}❌ Falhou: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ] && [ $WARNINGS -le 2 ]; then
    echo -e "${GREEN}🎉 DEPLOY VALIDADO COM SUCESSO!${NC}"
    echo "O sistema está pronto para uso."
    exit 0
elif [ $FAILED -eq 0 ]; then
    echo -e "${YELLOW}⚠️ DEPLOY OK COM AVISOS${NC}"
    echo "O sistema básico está funcionando, mas alguns componentes opcionais falharam."
    echo "Revise os avisos acima."
    exit 0
else
    echo -e "${RED}❌ DEPLOY COM PROBLEMAS${NC}"
    echo "Corrija os erros acima antes de usar o sistema."
    echo "Consulte docs/DEPLOY_GUIDE.md para ajuda."
    exit 1
fi
