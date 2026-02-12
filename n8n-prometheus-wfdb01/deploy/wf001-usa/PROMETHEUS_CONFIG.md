# Configuração Prometheus - wf001-usa

## 📍 Servidor
- **Nome**: wf001.vya.digital
- **Localização**: USA - Virginia
- **Stack Prometheus**: enterprise-observability @ wfdb01.vya.digital

## 🔗 URLs da Stack Enterprise Observability
- **Pushgateway**: `https://prometheus.vya.digital/pushgateway`
- **Prometheus**: `https://prometheus.vya.digital`
- **Grafana**: `https://grafana.vya.digital`
- **Alertmanager**: `https://alertmanager.vya.digital`
- **Loki**: `https://loki.vya.digital`

Todas as URLs usam HTTPS com certificados Let's Encrypt via Traefik.

## 🔧 Configuração Aplicada

O Collector API neste servidor foi configurado para enviar métricas para o Prometheus Pushgateway remoto:

```yaml
environment:
  - PROMETHEUS_PUSHGATEWAY_URL=https://prometheus.vya.digital/pushgateway
  - PROMETHEUS_PUSHGATEWAY_ENABLED=true
  - PROMETHEUS_PUSHGATEWAY_INTERVAL=60
  - PROMETHEUS_JOB_NAME=collector_api_wf001_usa
```

## 📊 Métricas Enviadas

### Identificação no Prometheus:
- **Job**: `collector_api_wf001_usa`
- **Instance**: `0.0.0.0:5000` (gerado automaticamente)

### Métricas Disponíveis:
- `api_requests_total{job="collector_api_wf001_usa"}` - Total de requisições
- `api_request_duration_seconds{job="collector_api_wf001_usa"}` - Duração das requisições
- `network_latency_rtt_seconds{job="collector_api_wf001_usa"}` - Latência de rede
- `database_query_latency_seconds{job="collector_api_wf001_usa"}` - Latência de DB
- `database_available{job="collector_api_wf001_usa"}` - Status do banco
- `collector_api_up{job="collector_api_wf001_usa"}` - Status do serviço

## 🚀 Deploy

### 1. Configurar Variáveis de Ambiente

Crie o arquivo `.env` neste diretório:

```bash
# Docker User
DOCKER_UID=1000
DOCKER_GID=1000

# Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=sua_senha_segura

# Collector API
COLLECTOR_API_KEY=sua_api_key_segura

# PostgreSQL
POSTGRES_USER=monitor_user
POSTGRES_PASSWORD=senha_postgresql
POSTGRES_HOSTNAME=wfdb02.vya.digital
POSTGRES_PORT=5432
POSTGRES_DB=monitor_db

# MySQL
MYSQL_USER=monitor_user
MYSQL_PASSWORD=senha_mysql
MYSQL_HOSTNAME=wfdb02.vya.digital
MYSQL_PORT=3306
MYSQL_DB=monitor_db

# N8N
N8N_URL=https://workflow.vya.digital/
N8N_API_KEY=sua_n8n_api_key
```

### 2. Criar Diretórios de Dados

```bash
sudo mkdir -p /opt/docker_user/n8n-prometheus-wfdb01/{victoria-data,grafana-data,grafana-provisioning,logs/collector-api}
sudo chown -R $USER:$USER /opt/docker_user/n8n-prometheus-wfdb01
```

### 3. Iniciar Serviços

```bash
cd /opt/docker_user/n8n-prometheus-wfdb01/deploy/wf001-usa
docker-compose up -d
```

### 4. Verificar Status

```bash
# Ver logs do collector-api
docker logs prod-collector-api | grep prometheus

# Verificar métricas locais
curl http://localhost:9102/metrics

# Verificar métricas no Pushgateway remoto
curl http://wfdb01.vya.digital:9091/metrics | grep collector_api_wf001_usa
```

## 🔍 Monitoramento

### Queries Prometheus

```promql
# Status do serviço
collector_api_up{job="collector_api_wf001_usa"}

# Taxa de requisições por minuto
rate(api_requests_total{job="collector_api_wf001_usa"}[1m])

# Latência média de database
avg(database_query_latency_seconds{job="collector_api_wf001_usa"})

# Disponibilidade de databases
database_available{job="collector_api_wf001_usa"}
```

### Dashboards Grafana

Importe dashboards apontando para o Prometheus remoto:
- URL: `http://wfdb01.vya.digital:9090`
- Filtre por job: `collector_api_wf001_usa`

## 🛠️ Troubleshooting

### Problema: Métricas não aparecem no Pushgateway

**Verificar conectividade:**
```bash
docker exec prod-collector-api curl http://wfdb01.vya.digital:9091/
```

**Verificar logs:**
```bash
docker logs prod-collector-api | grep prometheus
```

**Verificar variáveis:**
```bash
docker exec prod-collector-api env | grep PROMETHEUS
```

### Problema: Firewall bloqueando

No servidor wfdb01.vya.digital, verifique:
```bash
sudo ufw status
sudo ufw allow 9091/tcp
```

### Problema: Reiniciar serviço

```bash
docker-compose restart collector-api
```

## 📝 Notas

1. **Dual Storage**:
   - Victoria Metrics permanece para armazenamento local
   - Prometheus remoto para agregação centralizada

2. **Frequência de Push**:
   - Métricas enviadas a cada 60 segundos
   - Ajustável via `PROMETHEUS_PUSHGATEWAY_INTERVAL`

3. **Job Name**:
   - Único por servidor: `collector_api_wf001_usa`
   - Facilita identificação no Prometheus

4. **Persistência**:
   - Métricas persistem no Pushgateway mesmo se o collector-api reiniciar
   - Não há perda de dados durante deploys

## 🔗 Links Úteis

- Prometheus Pushgateway: https://prometheus.vya.digital/pushgateway/
- Prometheus Server: https://prometheus.vya.digital/
- Grafana: https://grafana.vya.digital/
- Alertmanager: https://alertmanager.vya.digital/
- Loki: https://loki.vya.digital/
- Grafana Local (wf001): https://monitoring.vya.digital/
- Collector API: https://api-monitoring.vya.digital/
- Documentação: ../../../PROMETHEUS_INTEGRATION_SUMMARY.md
