# Guia de Deploy em Produção
# Servidores: wf001 (USA) e wf008 (Brasil)

## 📋 Pré-requisitos

### Ambos Servidores (wf001 e wf008)
- [ ] Docker e Docker Compose instalados
- [ ] Usuário `docker_user` criado
- [ ] Conectividade SSH configurada
- [ ] Firewall básico configurado
- [ ] NTP sincronizado (importante para métricas de latência)

### Servidor wf001 (USA) - Específico
- [ ] Portas liberadas: 3000 (Grafana), 5000 (Collector API), 8428 (VictoriaMetrics)
- [ ] Acesso às bases de dados (wfdb02.vya.digital)
- [ ] Certificados SSL/TLS (se usar HTTPS)

### Servidor wf008 (Brasil) - Específico
- [ ] Porta 9101 liberada (métricas Ping Service)
- [ ] Conectividade HTTPS para wf001.vya.digital:5000

---

## 🚀 Passo a Passo de Deploy

### Fase 1: Preparação Local

#### 1.1. Build das Imagens Docker
```bash
cd /path/to/n8n-prometheus-wfdb01

# Build Collector API
docker build -t adminvyadigital/n8n-collector-api:latest ./collector-api/

# Build Ping Service
docker build -t adminvyadigital/n8n-ping-service:latest ./ping-service/

# Push para Docker Hub
docker push adminvyadigital/n8n-collector-api:latest
docker push adminvyadigital/n8n-ping-service:latest
```

**Alternativa sem Docker Hub**:
```bash
# Salvar imagens como arquivo
docker save adminvyadigital/n8n-collector-api:latest | gzip > collector-api.tar.gz
docker save adminvyadigital/n8n-ping-service:latest | gzip > ping-service.tar.gz

# Copiar para servidores
scp collector-api.tar.gz root@wf001.vya.digital:/tmp/
scp ping-service.tar.gz root@wf008.vya.digital:/tmp/

# Carregar nos servidores
ssh root@wf001.vya.digital "docker load < /tmp/collector-api.tar.gz"
ssh root@wf008.vya.digital "docker load < /tmp/ping-service.tar.gz"
```

#### 1.2. Configurar Credenciais
```bash
cd deploy/wf001-usa
cp .env.example .env
vi .env  # Adicionar credenciais reais

cd ../wf008-brasil
cp .env.example .env
vi .env  # Adicionar API key (mesma do wf001)
```

**Valores importantes a configurar**:
- `COLLECTOR_API_KEY`: Chave segura de 64+ caracteres (mesma em ambos)
- `POSTGRES_PASSWORD` e `MYSQL_PASSWORD`: Senhas reais do wfdb02
- `N8N_API_KEY`: Token JWT do N8N
- `GRAFANA_ADMIN_PASSWORD`: Senha forte para admin do Grafana

---

### Fase 2: Deploy wf001 (USA) - Stack Principal

#### 2.1. Preparar Servidor
```bash
# SSH no servidor
ssh root@wf001.vya.digital

# Criar usuário docker_user (se não existir)
useradd -r -s /bin/false docker_user

# Criar estrutura de diretórios
mkdir -p /opt/monitoring-prod/{victoria-data,grafana-data,grafana-provisioning,logs/collector-api}

# Ajustar permissões
DOCKER_UID=$(id -u docker_user)
DOCKER_GID=$(id -g docker_user)
chown -R ${DOCKER_UID}:${DOCKER_GID} /opt/monitoring-prod/victoria-data
chown -R ${DOCKER_UID}:${DOCKER_GID} /opt/monitoring-prod/logs
chown -R 472:472 /opt/monitoring-prod/grafana-data

# Verificar UID/GID
echo "DOCKER_UID=${DOCKER_UID}"
echo "DOCKER_GID=${DOCKER_GID}"
```

#### 2.2. Executar Deploy Automatizado
```bash
cd /path/to/n8n-prometheus-wfdb01/deploy/wf001-usa

# Configurar usuário SSH (se não for root)
export SSH_USER=seu_usuario

# Executar deploy
./deploy.sh
```

**OU Deploy Manual**:
```bash
# Copiar arquivos
scp docker-compose.yml root@wf001.vya.digital:/opt/monitoring-prod/
scp .env root@wf001.vya.digital:/opt/monitoring-prod/

# SSH e iniciar
ssh root@wf001.vya.digital
cd /opt/monitoring-prod
docker compose pull
docker compose up -d

# Verificar logs
docker compose logs -f collector-api
```

#### 2.3. Validar wf001
```bash
# Testar endpoints
curl http://wf001.vya.digital:8428/health  # VictoriaMetrics
curl http://wf001.vya.digital:3000/api/health  # Grafana
curl http://wf001.vya.digital:5000/health  # Collector API

# Verificar métricas
curl http://wf001.vya.digital:9102/metrics | grep api_request
curl http://wf001.vya.digital:9100/metrics | grep node_cpu

# Verificar logs
ssh root@wf001.vya.digital "docker logs prod-collector-api --tail 50"
```

---

### Fase 3: Deploy wf008 (Brasil) - Ping Service

#### 3.1. Preparar Servidor
```bash
ssh root@wf008.vya.digital

# Criar usuário docker_user
useradd -r -s /bin/false docker_user

# Criar diretórios
mkdir -p /opt/monitoring-prod/logs/ping-service

# Ajustar permissões
DOCKER_UID=$(id -u docker_user)
DOCKER_GID=$(id -g docker_user)
chown -R ${DOCKER_UID}:${DOCKER_GID} /opt/monitoring-prod/logs

echo "DOCKER_UID=${DOCKER_UID}"
echo "DOCKER_GID=${DOCKER_GID}"
```

#### 3.2. Executar Deploy
```bash
cd /path/to/n8n-prometheus-wfdb01/deploy/wf008-brasil

# Executar deploy
./deploy.sh
```

**OU Manual**:
```bash
scp docker-compose.yml root@wf008.vya.digital:/opt/monitoring-prod/
scp .env root@wf008.vya.digital:/opt/monitoring-prod/

ssh root@wf008.vya.digital
cd /opt/monitoring-prod
docker compose pull
docker compose up -d
```

#### 3.3. Validar wf008
```bash
# Testar endpoints locais
curl http://wf008.vya.digital:9101/metrics  # Ping Service
curl http://wf008.vya.digital:9100/metrics  # Node Exporter

# Verificar logs de ping
ssh root@wf008.vya.digital "docker logs -f prod-ping-service"

# Deve mostrar pings sendo enviados:
# [info] ping_success rtt_ms=145.23 status_code=200
```

---

### Fase 4: Validação End-to-End

#### 4.1. Verificar Latência Brasil→USA
```bash
# No wf008, verificar se pings estão sendo enviados
ssh root@wf008.vya.digital "docker logs prod-ping-service --tail 20 | grep ping_success"

# Deve mostrar RTT entre 120-200ms (latência transatlântica)
```

#### 4.2. Verificar Métricas no VictoriaMetrics
```bash
# Query de teste
curl -s 'http://wf001.vya.digital:8428/api/v1/query?query=network_latency_rtt_seconds' | jq .

# Deve retornar dados se scraping estiver funcionando
```

#### 4.3. Acessar Grafana
```
URL: http://wf001.vya.digital:3000
User: admin
Password: <configurado no .env>

- Verificar datasource VictoriaMetrics
- Importar dashboards
- Validar métricas visíveis
```

---

## 🔒 Segurança e Hardening

### 1. Firewall Rules (UFW)

#### wf001 (USA)
```bash
ssh root@wf001.vya.digital

# Bloquear tudo por padrão
ufw default deny incoming
ufw default allow outgoing

# SSH
ufw allow 22/tcp

# Permitir apenas wf008 acessar Collector API
ufw allow from <IP_wf008> to any port 5000 proto tcp

# Grafana (restringir IPs se possível)
ufw allow 3000/tcp

# Ativar
ufw enable
```

#### wf008 (Brasil)
```bash
ssh root@wf008.vya.digital

ufw default deny incoming
ufw default allow outgoing

# SSH
ufw allow 22/tcp

# Permitir apenas wf001 coletar métricas
ufw allow from <IP_wf001> to any port 9101 proto tcp
ufw allow from <IP_wf001> to any port 9100 proto tcp

ufw enable
```

### 2. SSL/TLS com Nginx (Recomendado)
```bash
# Instalar Nginx no wf001
apt install nginx certbot python3-certbot-nginx

# Configurar reverse proxy
cat > /etc/nginx/sites-available/monitoring << 'EOF'
server {
    listen 443 ssl http2;
    server_name monitoring.vya.digital;

    ssl_certificate /etc/letsencrypt/live/monitoring.vya.digital/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/monitoring.vya.digital/privkey.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# Obter certificado
certbot --nginx -d monitoring.vya.digital
```

### 3. Backup Automatizado
```bash
# Crontab no wf001
crontab -e

# Backup diário às 3h
0 3 * * * cd /opt/monitoring-prod && tar -czf /opt/monitoring-backups/backup-$(date +\%Y\%m\%d).tar.gz victoria-data/ grafana-data/

# Limpar backups >30 dias
0 4 * * * find /opt/monitoring-backups/ -name "backup-*.tar.gz" -mtime +30 -delete
```

---

## 📊 Monitoramento do Monitoramento

### Alertas Críticos (configurar no Grafana)
- [ ] Ping Service down por >5min
- [ ] Collector API down por >5min
- [ ] Latência >300ms por >10min
- [ ] VictoriaMetrics disk >80%

### Health Checks Externos
```bash
# Adicionar no cron para alertar se serviços caírem
*/5 * * * * curl -f http://wf001.vya.digital:5000/health || echo "Collector API DOWN" | mail -s "ALERT" admin@vya.digital
```

---

## 🐛 Troubleshooting

### Problema: Ping Service não conecta no Collector API
```bash
# Verificar conectividade
ssh root@wf008.vya.digital "curl -v https://wf001.vya.digital:5000/health"

# Verificar DNS
ssh root@wf008.vya.digital "nslookup wf001.vya.digital"

# Verificar firewall
ssh root@wf001.vya.digital "ufw status"
```

### Problema: VictoriaMetrics sem dados
```bash
# Testar query manual
curl 'http://wf001.vya.digital:8428/api/v1/query?query=up'

# Verificar logs do VictoriaMetrics
docker logs prod-victoria-metrics --tail 50
```

### Problema: Grafana não mostra métricas
```bash
# Verificar datasource
curl http://wf001.vya.digital:3000/api/datasources

# Testar query direto no VictoriaMetrics
curl 'http://wf001.vya.digital:8428/api/v1/query?query=network_latency_rtt_seconds'

# Ver logs do Grafana
docker logs prod-grafana | grep error
```

---

## ✅ Checklist Final

### Pré-Deploy
- [ ] Build das imagens concluído
- [ ] Credenciais configuradas (.env)
- [ ] Usuário docker_user criado em ambos servidores
- [ ] Diretórios criados e permissões ajustadas
- [ ] Conectividade SSH testada

### Deploy wf001
- [ ] Docker Compose up -d executado
- [ ] Todos containers healthy
- [ ] VictoriaMetrics respondendo
- [ ] Grafana acessível
- [ ] Collector API respondendo /health

### Deploy wf008
- [ ] Docker Compose up -d executado
- [ ] Ping Service healthy
- [ ] Logs mostram pings sendo enviados
- [ ] RTT ~120-200ms (Brasil→USA)

### Segurança
- [ ] Firewall configurado em ambos
- [ ] Apenas IPs necessários liberados
- [ ] SSL/TLS configurado (produção)
- [ ] Senhas fortes em .env
- [ ] Backup automatizado ativo

### Validação Final
- [ ] Métricas visíveis no Grafana
- [ ] Alertas configurados
- [ ] Documentação atualizada
- [ ] Equipe treinada

---

## 📞 Suporte
- Documentação: `/opt/monitoring-prod/README.md`
- Logs: `docker compose logs -f <service>`
- Status: `docker compose ps`
- Restart: `docker compose restart <service>`
