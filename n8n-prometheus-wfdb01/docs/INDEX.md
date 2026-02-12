# 📚 INDEX - N8N Monitoring System

**Projeto**: N8N Monitoring System
**Última Atualização**: 2026-02-04 18:00
**Status**: 🟡 In Progress (70% Complete)

---

## 🎯 Visão Geral do Projeto

Sistema de monitoramento distribuído para coletar métricas de latência de rede (Brasil→USA) e performance do N8N, com armazenamento em VictoriaMetrics e visualização em Grafana.

**Arquitetura**:
```
wf008 (Brasil) → Collector API (USA) → VictoriaMetrics → Grafana
         ↓                                    ↑
    Ping Service                        N8N Metrics
```

---

## 📁 Estrutura do Projeto

```
n8n-prometheus-wfdb01/
├── 📂 collector-api/          # API para receber pings e métricas
│   ├── src/
│   │   ├── api/               # Endpoints FastAPI
│   │   ├── database/          # Probes PostgreSQL/MySQL
│   │   ├── metrics/           # Prometheus metrics
│   │   ├── victoria_pusher.py # 🆕 Envio para VictoriaMetrics
│   │   ├── config.py
│   │   ├── logger.py
│   │   ├── main.py
│   │   └── models.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── 📂 ping-service/           # Serviço de ping Brasil→USA
│   ├── src/
│   │   ├── config.py          # ✅ Fixed with alias
│   │   ├── logger.py
│   │   ├── main.py
│   │   ├── metrics.py
│   │   ├── ping_client.py     # ✅ Updated field name
│   │   └── scheduler.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── 📂 deploy/                 # Deployment files
│   ├── DEPLOY_GUIDE.md        # Manual de deployment
│   ├── DNS_CONFIGURATION.md   # Configuração DNS e Traefik
│   ├── wf001-usa/             # USA server configs
│   │   ├── docker-compose.yml # 5 containers
│   │   ├── .env.example
│   │   └── deploy.sh
│   └── wf008-brasil/          # Brasil server configs
│       ├── docker-compose.yml # 3 containers
│       ├── .env.example
│       └── deploy.sh
│
├── 📂 docs/                   # Documentação
│   ├── INDEX.md               # Este arquivo
│   ├── TODO.md                # Lista de tarefas
│   └── sessions/              # Documentação por sessão
│       └── 2026-02-04/        # 🆕 Sessão de hoje
│           ├── TODAY_ACTIVITIES_2026-02-04.md
│           ├── SESSION_RECOVERY_2026-02-04.md
│           ├── SESSION_REPORT_2026-02-04.md
│           └── FINAL_STATUS_2026-02-04.md
│
├── 📂 infrastructure/         # Configs de infra (deprecated)
│   ├── databases/
│   └── grafana/
│
├── 📂 scripts/                # Scripts auxiliares
│   ├── run_homologation.py
│   ├── test_collector_api.py
│   └── test_failure_scenarios.py
│
├── 📂 logs/                   # Logs locais
│   ├── collector-api/
│   ├── ping-service/
│   └── infrastructure/
│
├── 📂 grafana_data/           # Dados persistentes Grafana
├── 📂 victoria_data/          # Dados persistentes VictoriaMetrics
│
├── docker-compose.yml         # Compose local (dev)
├── .env                       # Environment variables
├── .env.example
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start

### Desenvolvimento Local

```bash
# 1. Clone & setup
cd n8n-prometheus-wfdb01
cp .env.example .env
# Editar .env com credenciais

# 2. Start services
docker compose up -d

# 3. Verificar
curl http://localhost:8428/health  # VictoriaMetrics
curl http://localhost:3000          # Grafana
curl http://localhost:5001/health  # Collector API
```

### Deploy Produção

**wf001 (USA)**:
```bash
cd deploy/wf001-usa/
cp .env.example .env
# Editar .env
./deploy.sh
```

**wf008 (Brasil)**:
```bash
cd deploy/wf008-brasil/
cp .env.example .env
# Editar .env
./deploy.sh
```

---

## 📊 Status dos Componentes

### wf001.vya.digital (USA - Collector)

| Container | Image | Status | Port | Notes |
|-----------|-------|--------|------|-------|
| prod-victoria-metrics | victoriametrics/victoria-metrics:latest | ✅ Healthy | 127.0.0.1:8428 | 90d retention |
| prod-grafana | grafana/grafana:12.3.2 | ✅ Healthy | 3000 | Datasource pending |
| prod-collector-api | adminvyadigital/n8n-collector-api:latest | ⏳ Update pending | 5001, 9102 | Victoria pusher ready |
| prod-node-exporter | prom/node-exporter:latest | ✅ Up | 9100 | System metrics |
| prod-cadvisor | gcr.io/cadvisor/cadvisor:latest | ✅ Up | 8080 | Container metrics |

**Health**: 5/6 OK (1 pending update)

### wf008.vya.digital (Brasil - Ping)

| Container | Image | Status | Port | Notes |
|-----------|-------|--------|------|-------|
| prod-ping-service | adminvyadigital/n8n-ping-service:latest | ✅ Healthy | 9101 | Pings working |
| prod-node-exporter | prom/node-exporter:latest | ✅ Up | 9100 | System metrics |
| prod-cadvisor | gcr.io/cadvisor/cadvisor:latest | ✅ Up | 8080 | Container metrics |

**Health**: 3/3 OK ✅

**Últimos Pings**: ~400ms RTT, 200 OK, intervalo 30s

---

## 🔑 Credenciais e Configuração

### API Keys
- **Collector API**: Ver `.env` (`COLLECTOR_API_KEY`)
- **N8N API**: Ver `.secrets/credentials.json`

### Databases (wfdb02.vya.digital)
- **PostgreSQL**: 5432, database `monitor_db`, user `monitor_user`
- **MySQL**: 3306, database `monitor_db`, user `monitor_user`

### Grafana
- **URL Local**: http://localhost:3000
- **URL Produção**: http://monitoring.vya.digital (⏳ DNS pending)
- **User**: admin
- **Password**: Ver `.env` (`GRAFANA_ADMIN_PASSWORD`)

### Collector API
- **URL Local**: http://localhost:5001
- **URL Produção**: https://api-monitoring.vya.digital
- **Auth**: Header `X-API-Key`

---

## 📈 Métricas Disponíveis

### Ping Metrics (Brasil→USA)

```prometheus
# RTT de rede (segundos)
network_latency_rtt_seconds{
  source_location="wf008_brazil",
  source_datacenter="wf008",
  source_country="BR",
  target_location="collector_api_usa"
}

# Tempo de processamento da API
collector_api_processing_seconds

# Total de pings recebidos
collector_api_pings_received_total{
  source_location="wf008_brazil",
  source_country="BR"
}
```

### Collector API Metrics

```prometheus
# Status da API
collector_api_up

# Disponibilidade dos databases
database_available{db_type="mysql"}
database_available{db_type="postgresql"}

# Latência de queries
database_query_latency_seconds{
  db_type="mysql|postgresql",
  operation="health_check|test_query",
  status="success|failed"
}

# Requisições HTTP
api_requests_total{endpoint, method, status_code}
api_request_duration_seconds{endpoint, method}
```

### N8N Metrics (Quando Integrado)

```prometheus
# Workflows
n8n_workflow_executions_total{workflow_id, workflow_name}
n8n_workflow_executions_success{workflow_id, workflow_name}
n8n_workflow_executions_failed{workflow_id, workflow_name}
n8n_workflow_execution_duration_seconds{workflow_id, workflow_name}

# Nodes
n8n_node_execution_time_ms{workflow_name, node_name}
n8n_node_execution_time_max_ms{workflow_name, node_name}
n8n_node_type_avg_time_ms{node_type}
n8n_node_type_executions_total{node_type}
```

---

## 🔍 Comandos Úteis

### Health Checks

**wf001 (USA)**:
```bash
# VictoriaMetrics
curl localhost:8428/health

# Grafana
curl localhost:3000/api/health

# Collector API
curl localhost:5001/health

# Métricas Prometheus
curl localhost:5001/metrics
```

**wf008 (Brasil)**:
```bash
# Ping Service logs
docker logs prod-ping-service --tail 50

# Últimos pings com sucesso
docker logs prod-ping-service | grep ping_success | tail -10
```

### VictoriaMetrics Queries

```bash
# Listar todas as métricas
curl 'http://localhost:8428/api/v1/label/__name__/values' | jq

# Query RTT
curl 'http://localhost:8428/api/v1/query?query=network_latency_rtt_seconds' | jq

# Query time series (last 1h)
curl 'http://localhost:8428/api/v1/query_range?query=network_latency_rtt_seconds&start=-1h&step=30s' | jq
```

### Docker Operations

```bash
# Ver logs
docker logs <container> --tail 50

# Restart
docker compose restart <service>

# Status
docker compose ps

# Ver environment
docker exec <container> printenv
```

---

## 🐛 Troubleshooting

### Ping Service 401 Unauthorized

**Sintoma**: `{"status_code": 401, "response": {"detail": "Invalid API Key"}}`

**Fix**:
1. Verificar `.env` tem `COLLECTOR_API_KEY`
2. Verificar container carregou: `docker exec prod-ping-service printenv | grep COLLECTOR`
3. Verificar imagem atualizada: `docker image inspect ping-service | grep Created`
4. Rebuild se necessário

**Referência**: [TODAY_ACTIVITIES_2026-02-04.md](./sessions/2026-02-04/TODAY_ACTIVITIES_2026-02-04.md)

### VictoriaMetrics Vazio

**Sintoma**: Query retorna `"result":[]`

**Verificar**:
1. Collector API logs: `docker logs prod-collector-api | grep victoria`
2. VM healthy: `curl localhost:8428/health`
3. Métricas disponíveis: `curl localhost:8428/api/v1/label/__name__/values`

**Referência**: [SESSION_RECOVERY_2026-02-04.md](./sessions/2026-02-04/SESSION_RECOVERY_2026-02-04.md)

### Grafana Datasource Não Conecta

**Verificar**:
1. URL correta: `http://victoria-metrics:8428`
2. VM respondendo: `docker exec prod-grafana curl http://victoria-metrics:8428/health`
3. Network: `docker inspect prod-grafana | grep Networks`
4. Deve estar em `monitoring-net` com victoria-metrics

---

## 📚 Documentação Detalhada

### Deployment
- [DEPLOY_GUIDE.md](../deploy/DEPLOY_GUIDE.md) - Guia completo de deployment
- [DNS_CONFIGURATION.md](../deploy/DNS_CONFIGURATION.md) - Configuração DNS e Traefik

### Sessões de Desenvolvimento
- **2026-02-04**: Validation & Bug Fixes
  - [Today's Activities](./sessions/2026-02-04/TODAY_ACTIVITIES_2026-02-04.md) - Log detalhado
  - [Session Recovery](./sessions/2026-02-04/SESSION_RECOVERY_2026-02-04.md) - Guia de continuação
  - [Session Report](./sessions/2026-02-04/SESSION_REPORT_2026-02-04.md) - Relatório executivo
  - [Final Status](./sessions/2026-02-04/FINAL_STATUS_2026-02-04.md) - Estado final

### Referências Externas
- [VictoriaMetrics Docs](https://docs.victoriametrics.com/)
- [Grafana Docs](https://grafana.com/docs/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Prometheus Metrics](https://prometheus.io/docs/concepts/metric_types/)

---

## 🔄 Workflow Típico

### Adicionar Nova Métrica

1. **Definir no código**:
```python
from prometheus_client import Counter
my_metric = Counter('my_metric_name', 'Description', ['label1', 'label2'])
```

2. **Coletar dados**:
```python
my_metric.labels(label1='value1', label2='value2').inc()
```

3. **Enviar para VictoriaMetrics**:
```python
victoria_pusher = get_victoria_pusher()
metrics_text = "my_metric_name{label1=\"value1\"} 123 1738698616000"
await victoria_pusher.push_metrics(metrics_text)
```

4. **Query no Grafana**:
```promql
my_metric_name{label1="value1"}
```

### Criar Dashboard Grafana

1. Dashboards → New Dashboard
2. Add Panel → Add Query
3. Query: PromQL syntax
4. Visualize: Time series, gauge, table, etc.
5. Save dashboard
6. Export JSON para versionamento

### Deploy Nova Versão

1. **Modificar código**
2. **Build**:
   ```bash
   docker build -t adminvyadigital/SERVICE:latest --no-cache .
   ```
3. **Push**:
   ```bash
   docker push adminvyadigital/SERVICE:latest
   ```
4. **Deploy**:
   ```bash
   ssh server
   docker pull adminvyadigital/SERVICE:latest
   docker compose restart SERVICE
   ```
5. **Validar**:
   ```bash
   docker logs SERVICE --tail 50
   ```

---

## 📞 Contatos e Recursos

### Servidores

**wf001.vya.digital** (USA):
- SSH: `ssh -p 5010 archaris@wf001.vya.digital`
- Auth: SSH key
- Sudo: Yes (passwordless)
- Path: `/opt/docker_user/n8n-prometheus-wfdb01/`

**wf008.vya.digital** (Brasil):
- SSH: `ssh docker_user@wf008.vya.digital`
- Auth: Password
- Path: `/home/docker_user/monitoring-prod/`

### Docker Registry
- Hub: Docker Hub
- Org: `adminvyadigital`
- Images: `n8n-collector-api`, `n8n-ping-service`

### URLs (após DNS)
- Grafana: https://monitoring.vya.digital
- Collector API: https://api-monitoring.vya.digital

---

## 🎯 Roadmap

### ✅ Fase 1: Core Infrastructure (Completo)
- [x] Arquitetura
- [x] Collector API
- [x] Ping Service
- [x] Deployment wf001 e wf008
- [x] Fix autenticação

### ⏳ Fase 2: Data Pipeline (70% Completo)
- [x] Pings funcionando
- [ ] ⏳ Dados no VictoriaMetrics (deploy pending)
- [ ] Grafana datasource
- [ ] Dashboard básico

### 📋 Fase 3: N8N Integration (0%)
- [ ] Scripts adaptados
- [ ] Cron configurado
- [ ] Dashboards N8N
- [ ] Métricas por node

### 📋 Fase 4: Production Ready (0%)
- [ ] DNS público
- [ ] Alerting
- [ ] Backup procedures
- [ ] Documentation completa
- [ ] Team training

**ETA Completion**: 2026-02-08

---

## 📊 Métricas do Projeto

**Progresso Geral**: 70%
**Issues Críticos**: 0
**Issues Abertos**: 3 (1 major, 2 minor)
**Linhas de Código**: ~2000
**Linhas de Documentação**: ~3000
**Containers**: 8 (5 wf001 + 3 wf008)
**Uptime**: 100% (últimas 48h)

---

**Última Atualização**: 2026-02-04 18:00
**Próxima Revisão**: Início da próxima sessão
**Mantenedor**: GitHub Copilot + Yves Marinho
