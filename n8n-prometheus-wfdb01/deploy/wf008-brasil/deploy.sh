#!/bin/bash
#
# Script de Deploy - wf008 (Brasil)
# Servidor: wf008.vya.digital (São Paulo, Brasil)
# Data: 2026-02-04
#

set -e

echo "============================================"
echo "  DEPLOY - Servidor wf008 (Brasil)"
echo "============================================"
echo ""

# Variáveis
SERVER="wf008.vya.digital"
SSH_USER="${SSH_USER:-root}"
DEPLOY_PATH="/opt/monitoring-prod"
BACKUP_PATH="/opt/monitoring-backups"

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Funções
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Verificar conexão SSH
log_info "Verificando conexão com $SERVER..."
if ! ssh -o ConnectTimeout=10 ${SSH_USER}@${SERVER} "echo 'Conexão OK'"; then
    log_error "Falha ao conectar com $SERVER"
    exit 1
fi

# 2. Criar diretórios no servidor
log_info "Criando estrutura de diretórios..."
ssh ${SSH_USER}@${SERVER} << 'ENDSSH'
    sudo mkdir -p /opt/monitoring-prod/logs/ping-service
    sudo mkdir -p /opt/monitoring-backups
    
    # Verificar se usuário docker_user existe
    if ! id docker_user > /dev/null 2>&1; then
        echo "Criando usuário docker_user..."
        sudo useradd -r -s /bin/false docker_user
    fi
    
    # Ajustar permissões
    DOCKER_UID=$(id -u docker_user)
    DOCKER_GID=$(id -g docker_user)
    sudo chown -R ${DOCKER_UID}:${DOCKER_GID} /opt/monitoring-prod/logs
    
    echo "UID do docker_user: ${DOCKER_UID}"
    echo "GID do docker_user: ${DOCKER_GID}"
ENDSSH

# 3. Copiar arquivos de configuração
log_info "Copiando arquivos para o servidor..."

# Docker Compose
scp docker-compose.yml ${SSH_USER}@${SERVER}:${DEPLOY_PATH}/

# .env
if [ -f .env ]; then
    log_warn "Copiando arquivo .env - verifique se as credenciais estão corretas!"
    scp .env ${SSH_USER}@${SERVER}:${DEPLOY_PATH}/
else
    log_warn "Arquivo .env não encontrado! Copie .env.example e ajuste:"
    log_warn "  scp .env.example ${SSH_USER}@${SERVER}:${DEPLOY_PATH}/.env"
    log_warn "  ssh ${SSH_USER}@${SERVER}"
    log_warn "  vi ${DEPLOY_PATH}/.env"
    read -p "Pressione ENTER para continuar ou Ctrl+C para cancelar..."
fi

# 4. Build e push da imagem do Ping Service
log_info "Verificando imagens Docker..."
read -p "Deseja fazer build e push do Ping Service? (s/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    log_info "Fazendo build da imagem..."
    
    # Ping Service
    docker build -t registry.vya.digital/n8n-ping-service:latest ../../ping-service/
    docker push registry.vya.digital/n8n-ping-service:latest
    
    log_info "Imagem enviada para o registry!"
fi

# 5. Deploy no servidor
log_info "Iniciando deploy no servidor..."
ssh ${SSH_USER}@${SERVER} << 'ENDSSH'
    cd /opt/monitoring-prod
    
    # Criar .env com variáveis do docker_user se não existir
    if [ ! -f .env ]; then
        DOCKER_UID=$(id -u docker_user)
        DOCKER_GID=$(id -g docker_user)
        echo "DOCKER_UID=${DOCKER_UID}" > .env
        echo "DOCKER_GID=${DOCKER_GID}" >> .env
        echo "Arquivo .env criado com UID/GID. ADICIONE AS CREDENCIAIS MANUALMENTE!"
        exit 1
    fi
    
    # Backup se já houver containers rodando
    if docker compose ps | grep -q "Up"; then
        echo "Parando serviços anteriores..."
        docker compose down
    fi
    
    # Pull das imagens
    docker compose pull
    
    # Subir serviços
    docker compose up -d
    
    # Aguardar inicialização
    sleep 10
    
    # Verificar status
    docker compose ps
ENDSSH

# 6. Validação
log_info "Validando deploy..."
sleep 5

log_info "Testando endpoints..."
echo -n "  - Ping Service metrics: "
if curl -s -f http://${SERVER}:9101/metrics > /dev/null; then
    log_info "OK"
else
    log_error "FALHA"
fi

echo -n "  - Node Exporter: "
if curl -s -f http://${SERVER}:9100/metrics > /dev/null; then
    log_info "OK"
else
    log_error "FALHA"
fi

# Testar ping para wf001
log_info "Testando conectividade Brasil -> USA..."
ssh ${SSH_USER}@${SERVER} "docker logs prod-ping-service --tail 20"

echo ""
log_info "Deploy finalizado!"
log_info ""
log_warn "Próximos passos:"
log_warn "  1. Verificar logs: ssh ${SSH_USER}@${SERVER} 'docker logs -f prod-ping-service'"
log_warn "  2. Configurar firewall (permitir apenas wf001)"
log_warn "  3. Validar métricas no Grafana (wf001)"
log_warn "  4. Configurar SSL/TLS para endpoints públicos"
