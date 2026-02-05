# Deploy em Produção - N8N Monitoring System

Arquivos de configuração e scripts para deploy nos servidores wf001 (USA) e wf008 (Brasil).

## 📁 Estrutura

```
deploy/
├── DEPLOY_GUIDE.md           # Guia completo de deploy
├── wf001-usa/                # Servidor USA (Virginia)
│   ├── docker-compose.yml    # Stack completo (VictoriaMetrics, Grafana, Collector API, Prometheus)
│   ├── prometheus.yml        # Configuração de scraping
│   ├── .env.example          # Template de variáveis de ambiente
│   └── deploy.sh            # Script automatizado de deploy
└── wf008-brasil/            # Servidor Brasil (São Paulo)
    ├── docker-compose.yml    # Ping Service + Node Exporter
    ├── .env.example          # Template de variáveis de ambiente
    └── deploy.sh            # Script automatizado de deploy
```

## 🚀 Quick Start

### 1. Preparar Credenciais
```bash
# wf001 (USA)
cd wf001-usa
cp .env.example .env
vi .env  # Ajustar credenciais

# wf008 (Brasil)
cd ../wf008-brasil
cp .env.example .env
vi .env  # Ajustar API key
```

### 2. Build das Imagens
```bash
# Na raiz do projeto
docker build -t registry.vya.digital/n8n-collector-api:latest ./collector-api/
docker build -t registry.vya.digital/n8n-ping-service:latest ./ping-service/

# Push para registry (ou salvar como .tar.gz)
docker push registry.vya.digital/n8n-collector-api:latest
docker push registry.vya.digital/n8n-ping-service:latest
```

### 3. Deploy Automatizado

#### wf001 (USA) - Deploy primeiro
```bash
cd wf001-usa
export SSH_USER=root  # ou seu usuário SSH
./deploy.sh
```

#### wf008 (Brasil) - Deploy depois
```bash
cd wf008-brasil
export SSH_USER=root
./deploy.sh
```

### 4. Validação
```bash
# wf001
curl http://wf001.vya.digital:5000/health
curl http://wf001.vya.digital:3000/api/health
curl http://wf001.vya.digital:8428/health

# wf008
curl http://wf008.vya.digital:9101/metrics
ssh root@wf008.vya.digital "docker logs prod-ping-service --tail 20"
```

## 📖 Documentação Completa

Consulte [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md) para:
- Pré-requisitos detalhados
- Deploy manual passo a passo
- Configuração de firewall e segurança
- SSL/TLS com Nginx
- Troubleshooting
- Checklist completo

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────┐
│      wf008 (Brasil - São Paulo)         │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │     Ping Service                 │  │
│  │  - Envia pings a cada 30s       │  │
│  │  - Exporta métricas :9101       │  │
│  └──────────────────────────────────┘  │
│              │                          │
│              │ HTTPS POST               │
│              ▼                          │
└──────────────┼──────────────────────────┘
               │
               │ ~150ms latency
               │
┌──────────────▼──────────────────────────┐
│      wf001 (USA - Virginia)             │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │     Collector API :5000          │  │
│  │  - Recebe pings                  │  │
│  │  - Calcula RTT                   │  │
│  │  - Monitora DBs (wfdb02)         │  │
│  └──────────────┬───────────────────┘  │
│                 │                       │
│  ┌──────────────▼───────────────────┐  │
│  │     Prometheus :9090             │  │
│  │  - Scraping de métricas          │  │
│  │  - Agrega dados                  │  │
│  └──────────────┬───────────────────┘  │
│                 │                       │
│  ┌──────────────▼───────────────────┐  │
│  │  VictoriaMetrics :8428           │  │
│  │  - Armazenamento (90 dias)       │  │
│  │  - Time series database          │  │
│  └──────────────┬───────────────────┘  │
│                 │                       │
│  ┌──────────────▼───────────────────┐  │
│  │      Grafana :3000               │  │
│  │  - Dashboards                    │  │
│  │  - Alertas                       │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## 🔧 Comandos Úteis

### Gerenciar Serviços
```bash
# wf001
ssh root@wf001.vya.digital
cd /opt/monitoring-prod
docker compose ps
docker compose logs -f collector-api
docker compose restart collector-api

# wf008
ssh root@wf008.vya.digital
cd /opt/monitoring-prod
docker compose ps
docker compose logs -f ping-service
```

### Backup Manual
```bash
# wf001
ssh root@wf001.vya.digital
cd /opt/monitoring-prod
tar -czf /opt/monitoring-backups/backup-manual-$(date +%Y%m%d).tar.gz \
  victoria-data/ grafana-data/ prometheus-data/
```

### Atualizar Serviços
```bash
# Fazer push da nova imagem
docker push registry.vya.digital/n8n-collector-api:latest

# No servidor
ssh root@wf001.vya.digital
cd /opt/monitoring-prod
docker compose pull collector-api
docker compose up -d collector-api
```

## 🔒 Segurança

### Checklist Mínimo
- [ ] Firewall configurado (UFW)
- [ ] Portas restritas por IP
- [ ] Usuário não-root (docker_user)
- [ ] Senhas fortes no .env
- [ ] SSL/TLS em produção
- [ ] Backup automatizado

### Portas Essenciais
**wf001 (USA)**:
- 5000: Collector API (apenas wf008)
- 3000: Grafana (admin IPs)
- 9090: Prometheus (admin IPs)
- 8428: VictoriaMetrics (interno)

**wf008 (Brasil)**:
- 9101: Ping Service metrics (apenas wf001)
- 9100: Node Exporter (apenas wf001)

## 📊 Monitoramento

### Health Endpoints
```bash
# Collector API
curl http://wf001.vya.digital:5000/health

# Grafana
curl http://wf001.vya.digital:3000/api/health

# VictoriaMetrics
curl http://wf001.vya.digital:8428/health

# Prometheus
curl http://wf001.vya.digital:9090/-/healthy
```

### Métricas Principais
- `network_latency_rtt_seconds` - Latência Brasil→USA
- `ping_requests_total` - Total de pings enviados
- `database_query_latency_seconds` - Latência das queries nos DBs
- `api_request_duration_seconds` - Performance da API

## 🐛 Troubleshooting Rápido

**Ping Service não conecta**:
```bash
ssh root@wf008.vya.digital "curl -v https://wf001.vya.digital:5000/health"
```

**VictoriaMetrics sem dados**:
```bash
curl http://wf001.vya.digital:9090/api/v1/targets
```

**Grafana sem métricas**:
```bash
curl 'http://wf001.vya.digital:8428/api/v1/query?query=up'
```

## 📞 Contato e Suporte

- **Logs**: `docker compose logs -f <service>`
- **Status**: `docker compose ps`
- **Documentação Completa**: [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md)
- **Projeto**: `/opt/monitoring-prod/`
