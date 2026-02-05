#!/bin/bash
#
# Script de Deploy - wf001 (USA)
# Servidor: wf001.vya.digital (Virginia, USA)
# Data: 2026-02-04
#

set -e

echo "============================================"
echo "  DEPLOY - Servidor wf001 (USA)"
echo "============================================"
echo ""

# Variáveis
SERVER="wf001.vya.digital"
SSH_USER="${SSH_USER:-root}"
DEPLOY_PATH="/opt/monitoring-prod"
BACKUP_PATH="/opt/monitoring-backups"

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

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
    sudo mkdir -p /opt/monitoring-prod/{victoria-data,grafana-data,grafana-provisioning,prometheus-config,prometheus-data,logs/{collector-api,prometheus}}
    sudo mkdir -p /opt/monitoring-backups
    
    # Verificar se usuário docker_user existe
    if ! id docker_user > /dev/null 2>&1; then
        echo "Criando usuário docker_user..."
        sudo useradd -r -s /bin/false docker_user
    fi
    
    # Ajustar permissões
    DOCKER_UID=$(id -u docker_user)
    DOCKER_GID=$(id -g docker_user)
    sudo chown -R ${DOCKER_UID}:${DOCKER_GID} /opt/monitoring-prod/victoria-data
    sudo chown -R ${DOCKER_UID}:${DOCKER_GID} /opt/monitoring-prod/logs
    sudo chown -R 472:472 /opt/monitoring-prod/grafana-data
    sudo chmod 755 /opt/monitoring-prod/prometheus-config
    
    echo "UID do docker_user: ${DOCKER_UID}"
    echo "GID do docker_user: ${DOCKER_GID}"
ENDSSH

# 3. Copiar arquivos de configuração
log_info "Copiando arquivos para o servidor..."

# Docker Compose
scp docker-compose.yml ${SSH_USER}@${SERVER}:${DEPLOY_PATH}/

# Prometheus Config
scp prometheus.yml ${SSH_USER}@${SERVER}:${DEPLOY_PATH}/prometheus-config/

# .env (se existir)
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

# 4. Copiar provisioning do Grafana (se existir)
if [ -d "../../infrastructure/grafana/provisioning" ]; then
    log_info "Copiando configurações do Grafana..."
    scp -r ../../infrastructure/grafana/provisioning/* ${SSH_USER}@${SERVER}:${DEPLOY_PATH}/grafana-provisioning/
fi

# 5. Build e push das imagens (se usar registry)
log_info "Verificando imagens Docker..."
read -p "Deseja fazer build e push das imagens? (s/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    log_info "Fazendo build das imagens..."
    
    # Collector API
    docker build -t registry.vya.digital/n8n-collector-api:latest ../../collector-api/
    docker push registry.vya.digital/n8n-collector-api:latest
    
    log_info "Imagens enviadas para o registry!"
fi

# 6. Deploy no servidor
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
    
    # Backup de configuração anterior (se existir)
    if docker compose ps | grep -q "Up"; then
        echo "Fazendo backup da configuração atual..."
        docker compose down
        tar -czf /opt/monitoring-backups/backup-$(date +%Y%m%d_%H%M%S).tar.gz \
            victoria-data/ grafana-data/ prometheus-data/ 2>/dev/null || true
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

# 7. Validação
log_info "Validando deploy..."
sleep 5

log_info "Testando endpoints..."
echo -n "  - VictoriaMetrics: "
if curl -s -f http://${SERVER}:8428/health > /dev/null; then
    log_info "OK"
else
    log_error "FALHA"
fi

echo -n "  - Grafana: "
if curl -s -f http://${SERVER}:3000/api/health > /dev/null; then
    log_info "OK"
else
    log_error "FALHA"
fi

echo -n "  - Collector API: "
if curl -s -f http://${SERVER}:5000/health > /dev/null; then
    log_info "OK"
else
    log_error "FALHA"
fi

echo -n "  - Prometheus: "
if curl -s -f http://${SERVER}:9090/-/healthy > /dev/null; then
    log_info "OK"
else
    log_error "FALHA"
fi

echo ""
log_info "Deploy finalizado!"
log_info "Acesse:"
log_info "  - Grafana: http://${SERVER}:3000"
log_info "  - Prometheus: http://${SERVER}:9090"
log_info "  - VictoriaMetrics: http://${SERVER}:8428"
log_info ""
log_warn "Próximos passos:"
log_warn "  1. Configurar firewall/segurança"
log_warn "  2. Configurar SSL/TLS (Nginx reverse proxy)"
log_warn "  3. Fazer deploy do ping-service no wf008"
log_warn "  4. Validar coleta de métricas"
