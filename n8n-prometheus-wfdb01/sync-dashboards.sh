#!/bin/bash
# Script de sincronização dos dashboards para o servidor remoto wfdb01
# Data: 09/02/2026

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
SERVER="wfdb01"
REMOTE_USER="${REMOTE_USER:-root}"
REMOTE_PATH="/opt/docker_user/enterprise-observability"
LOCAL_PATH="$(cd "$(dirname "$0")" && pwd)"

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   🚀 Sync Dashboards Grafana → Servidor Remoto wfdb01${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# Verificar se está no diretório correto
if [ ! -f "docker-compose.yaml" ]; then
    echo -e "${RED}❌ Erro: docker-compose.yaml não encontrado${NC}"
    echo -e "${YELLOW}Execute o script dentro do diretório wfdb01-docker-folder${NC}"
    exit 1
fi

# Verificar se grafana/dashboards existe
if [ ! -d "grafana/dashboards" ]; then
    echo -e "${RED}❌ Erro: diretório grafana/dashboards não encontrado${NC}"
    exit 1
fi

# Contar dashboards
DASHBOARD_COUNT=$(ls -1 grafana/dashboards/*.json 2>/dev/null | wc -l)
echo -e "${GREEN}📊 Dashboards encontrados: $DASHBOARD_COUNT${NC}"
echo ""

# Listar dashboards
echo -e "${YELLOW}Dashboards a sincronizar:${NC}"
for dashboard in grafana/dashboards/*.json; do
    filename=$(basename "$dashboard")
    size=$(du -h "$dashboard" | cut -f1)
    echo -e "   • ${filename} (${size})"
done
echo ""

# Confirmar sync
read -p "$(echo -e ${YELLOW}Confirmar sincronização com $SERVER? [s/N]: ${NC})" -n 1 -r
echo
if [[ ! $REPLY =~ ^[SsYy]$ ]]; then
    echo -e "${RED}❌ Sync cancelado${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   📡 Iniciando Sincronização${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# Testar conectividade SSH
echo -e "${YELLOW}🔍 Testando conectividade SSH...${NC}"
if ssh -o ConnectTimeout=5 -o BatchMode=yes ${REMOTE_USER}@${SERVER} exit 2>/dev/null; then
    echo -e "${GREEN}✅ Conexão SSH OK${NC}"
else
    echo -e "${RED}❌ Erro: Não foi possível conectar via SSH${NC}"
    echo -e "${YELLOW}Verifique: ssh ${REMOTE_USER}@${SERVER}${NC}"
    exit 1
fi
echo ""

# Criar diretórios no servidor remoto
echo -e "${YELLOW}📁 Criando diretórios no servidor remoto...${NC}"
ssh ${REMOTE_USER}@${SERVER} "
    mkdir -p ${REMOTE_PATH}/grafana/provisioning/dashboards
    mkdir -p ${REMOTE_PATH}/grafana/dashboards
    echo '✅ Diretórios criados'
"
echo ""

# Sync provisioning config
echo -e "${YELLOW}📋 Sincronizando configuração de provisioning...${NC}"
rsync -avz --progress \
    grafana/provisioning/dashboards/ \
    ${REMOTE_USER}@${SERVER}:${REMOTE_PATH}/grafana/provisioning/dashboards/
echo -e "${GREEN}✅ Provisioning sincronizado${NC}"
echo ""

# Sync dashboards
echo -e "${YELLOW}📊 Sincronizando dashboards JSON...${NC}"
rsync -avz --progress \
    grafana/dashboards/ \
    ${REMOTE_USER}@${SERVER}:${REMOTE_PATH}/grafana/dashboards/
echo -e "${GREEN}✅ Dashboards sincronizados${NC}"
echo ""

# Sync docker-compose.yaml
echo -e "${YELLOW}🐋 Sincronizando docker-compose.yaml...${NC}"
rsync -avz --progress \
    docker-compose.yaml \
    ${REMOTE_USER}@${SERVER}:${REMOTE_PATH}/docker-compose.yaml.new
echo -e "${GREEN}✅ Docker Compose sincronizado como .new${NC}"
echo ""

# Ajustar permissões
echo -e "${YELLOW}🔐 Ajustando permissões...${NC}"
ssh ${REMOTE_USER}@${SERVER} "
    cd ${REMOTE_PATH}
    chown -R 472:472 grafana/ 2>/dev/null || true
    chmod -R 755 grafana/provisioning/
    chmod -R 644 grafana/dashboards/*.json
    echo '✅ Permissões ajustadas'
"
echo ""

# Validar estrutura
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   🔍 Validação no Servidor Remoto${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

ssh ${REMOTE_USER}@${SERVER} "
    cd ${REMOTE_PATH}

    echo -e '${YELLOW}📁 Estrutura de diretórios:${NC}'
    ls -lh grafana/provisioning/dashboards/
    echo ''

    echo -e '${YELLOW}📊 Dashboards ($(ls grafana/dashboards/*.json 2>/dev/null | wc -l) arquivos):${NC}'
    ls -lh grafana/dashboards/*.json | awk '{print \"   \" \$9 \" (\" \$5 \")\"}'
    echo ''
"

# Opções de deploy
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   🎯 Próximos Passos${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Escolha uma opção:${NC}"
echo -e "  ${GREEN}1)${NC} Aplicar docker-compose e reiniciar Grafana (RECOMENDADO)"
echo -e "  ${GREEN}2)${NC} Apenas reiniciar Grafana (mantém compose atual)"
echo -e "  ${GREEN}3)${NC} Validar compose sem aplicar"
echo -e "  ${GREEN}4)${NC} Sair (aplicar manualmente depois)"
echo ""

read -p "$(echo -e ${YELLOW}Escolha [1-4]: ${NC})" -n 1 -r CHOICE
echo ""

case $CHOICE in
    1)
        echo ""
        echo -e "${YELLOW}🔄 Aplicando novo docker-compose...${NC}"
        ssh ${REMOTE_USER}@${SERVER} "
            cd ${REMOTE_PATH}

            # Backup do compose atual
            cp docker-compose.yaml docker-compose.yaml.backup-\$(date +%Y%m%d-%H%M%S)

            # Aplicar novo compose
            mv docker-compose.yaml.new docker-compose.yaml

            # Validar
            docker-compose config > /dev/null && echo '✅ Compose válido' || echo '❌ Compose inválido'

            # Recriar Grafana
            echo 'Recriando container Grafana...'
            docker-compose up -d --force-recreate grafana

            echo ''
            echo 'Aguardando 10s para startup...'
            sleep 10

            echo ''
            echo '📋 Logs do Grafana:'
            docker logs enterprise-grafana --tail=30
        "
        echo ""
        echo -e "${GREEN}✅ Deploy concluído!${NC}"
        ;;

    2)
        echo ""
        echo -e "${YELLOW}🔄 Reiniciando apenas Grafana...${NC}"
        ssh ${REMOTE_USER}@${SERVER} "
            cd ${REMOTE_PATH}
            docker-compose restart grafana

            echo ''
            echo 'Aguardando 10s para startup...'
            sleep 10

            echo ''
            echo '📋 Logs do Grafana:'
            docker logs enterprise-grafana --tail=30
        "
        echo ""
        echo -e "${GREEN}✅ Grafana reiniciado!${NC}"
        ;;

    3)
        echo ""
        echo -e "${YELLOW}🔍 Validando docker-compose...${NC}"
        ssh ${REMOTE_USER}@${SERVER} "
            cd ${REMOTE_PATH}
            echo 'Compose atual:'
            docker-compose config | grep -A 15 'grafana:' || true
            echo ''
            echo 'Novo compose:'
            docker-compose -f docker-compose.yaml.new config | grep -A 15 'grafana:' || true
        "
        ;;

    4|*)
        echo ""
        echo -e "${YELLOW}ℹ️  Para aplicar manualmente depois:${NC}"
        echo ""
        echo -e "  ${GREEN}# Conectar ao servidor${NC}"
        echo -e "  ssh ${REMOTE_USER}@${SERVER}"
        echo ""
        echo -e "  ${GREEN}# Navegar para diretório${NC}"
        echo -e "  cd ${REMOTE_PATH}"
        echo ""
        echo -e "  ${GREEN}# Aplicar novo compose${NC}"
        echo -e "  mv docker-compose.yaml.new docker-compose.yaml"
        echo ""
        echo -e "  ${GREEN}# Reiniciar Grafana${NC}"
        echo -e "  docker-compose up -d --force-recreate grafana"
        echo ""
        ;;
esac

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Script concluído!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}🌐 Validar em:${NC} https://grafana.vya.digital"
echo -e "${YELLOW}📊 Dashboards:${NC} https://grafana.vya.digital/dashboards"
echo ""
