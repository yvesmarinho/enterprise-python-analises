# 🔄 Session Recovery - 04/02/2026

**Data da Sessão**: 2026-02-04
**Projeto**: N8N Monitoring System
**Fase**: Production Deployment & Validation

---

## 📌 Estado no Início da Sessão

### Contexto Herdado
- ✅ Stack completo desenvolvido (VictoriaMetrics, Grafana, Collector API, Ping Service)
- ✅ Deployment realizado em wf001-usa (03/02)
- ✅ Deployment realizado em wf008-brasil (04/02)
- ⚠️ Ping Service com erro 401 Unauthorized
- ⚠️ Dados não aparecendo no VictoriaMetrics

### Servidores em Produção

**wf001.vya.digital** (USA, Virginia)
- SSH: Port 5010, user archaris
- Path: `/opt/docker_user/n8n-prometheus-wfdb01/`
- Containers: victoria-metrics, grafana, collector-api, node-exporter, cadvisor
- Status: ✅ Todos healthy

**wf008.vya.digital** (Brasil)
- SSH: user docker_user (senha)
- Path: `/home/docker_user/monitoring-prod/`
- Containers: ping-service, node-exporter, cadvisor
- Status: ⚠️ Ping service com erro de autenticação

---

## 🔍 Problemas Identificados

### 1. Ping Service 401 Unauthorized
**Sintoma**:
```json
{"status_code": 401, "response": {"detail": "Invalid API Key"}, "event": "ping_failed"}
```

**Investigação Realizada**:
- ✅ Container tem variável `COLLECTOR_API_KEY` correta
- ✅ Collector API tem mesma chave
- ❌ Aplicação usando valor default hardcoded

**Root Cause**:
```python
# config.py
api_key: str = Field(default="dev-secret-key-12345")  # Sem alias!
```

### 2. VictoriaMetrics Vazio
**Sintoma**: Query `network_latency_rtt_seconds` retorna vazio

**Investigação**:
- ✅ VictoriaMetrics healthy: `curl localhost:8428/health` → "OK"
- ✅ Pings chegando ao Collector API
- ✅ RTT sendo calculado (logs confirmam)
- ❌ Nenhum log de envio para VictoriaMetrics

**Root Cause**: Collector API não implementado envio de dados para VM

---

## 🛠️ Correções Implementadas

### 1. Fix Ping Service Authentication ✅

**Arquivo**: `ping-service/src/config.py`

```python
# ANTES
class Settings(BaseSettings):
    api_key: str = Field(default="dev-secret-key-12345")

# DEPOIS
class Settings(BaseSettings):
    collector_api_key: str = Field(
        default="dev-secret-key-12345",
        alias="COLLECTOR_API_KEY"  # ← FIX
    )
```

**Resultado**:
- Build: 2026-02-04 12:45 (BRT)
- Deploy wf008: 17:38
- Status: ✅ 200 OK, RTT ~400ms

### 2. Implementar Victoria Pusher ✅

**Arquivo Novo**: `collector-api/src/victoria_pusher.py`

**Funcionalidades**:
- Classe `VictoriaMetricsPusher` com httpx async
- Método `push_metrics()` - POST para `/api/v1/import/prometheus`
- Método `push_ping_metrics()` - converte dict para formato Prometheus
- Fire-and-forget com `asyncio.create_task()`

**Integração**: `collector-api/src/api/__init__.py`
```python
# Após processar ping
victoria_pusher = get_victoria_pusher()
asyncio.create_task(victoria_pusher.push_ping_metrics(ping_metrics))
```

**Status**:
- Build: 2026-02-04 17:45
- Push: ⏳ Em andamento
- Deploy wf001: ⏳ Pendente

---

## 📊 Estado Atual dos Serviços

### wf001 (USA - Collector)

| Serviço | Versão | Status | Port | Notas |
|---------|--------|--------|------|-------|
| VictoriaMetrics | latest | ✅ Healthy | 127.0.0.1:8428 | Vazio (aguardando dados) |
| Grafana | 12.3.2 | ✅ Healthy | 3000 | Database OK |
| Collector API | 1.0.0 | ⚠️ OLD | 5001, 9102 | **Precisa atualizar** |
| Node Exporter | latest | ✅ Up | 9100 | - |
| cAdvisor | latest | ✅ Up | 8080 | - |

**Métricas Disponíveis** (`curl localhost:5001/metrics`):
- `collector_api_up 1.0`
- `database_available{db_type="mysql"} 1.0`
- `database_available{db_type="postgresql"} 1.0`
- `database_query_latency_seconds{...}` (histogramas)
- Total: 107 linhas de métricas

### wf008 (Brasil - Ping)

| Serviço | Versão | Status | Port | Notas |
|---------|--------|--------|------|-------|
| Ping Service | 1.0.0 | ✅ Healthy | 9101 | **Pings funcionando** |
| Node Exporter | latest | ✅ Up | 9100 | - |
| cAdvisor | latest | ✅ Up | 8080 | - |

**Últimos Pings**:
- Ping 1: 441.55ms RTT, 5.578ms processing
- Ping 2: 391.86ms RTT, 2.093ms processing
- Intervalo: 30s
- Target: `https://api-monitoring.vya.digital/api/ping`

---

## 🔄 Fluxo de Dados Atual

```
┌─────────────────────────────────────────────────────────┐
│                  wf008.vya.digital (Brasil)             │
│                                                          │
│  ┌─────────────────────────────────────────────┐       │
│  │  Ping Service (Container)                    │       │
│  │  - Gera ping a cada 30s                      │       │
│  │  - POST com X-API-Key                        │       │
│  │  - Calcula RTT total                         │       │
│  └─────────────────────────────────────────────┘       │
│                       │                                  │
│                       │ HTTPS POST                       │
│                       ▼                                  │
└───────────────────────┼──────────────────────────────────┘
                        │
                        │ Internet (~350ms)
                        │
┌───────────────────────▼──────────────────────────────────┐
│                  wf001.vya.digital (USA)                 │
│                                                          │
│  ┌─────────────────────────────────────────────┐       │
│  │  Collector API (Container)                   │       │
│  │  - Recebe ping                               │       │
│  │  - Valida API Key ✅                         │       │
│  │  - Calcula RTT de rede                       │       │
│  │  - ⏳ Envia para VictoriaMetrics (novo)     │       │
│  └─────────────────────────────────────────────┘       │
│                       │                                  │
│                       │ Async POST (fire-and-forget)     │
│                       ▼                                  │
│  ┌─────────────────────────────────────────────┐       │
│  │  VictoriaMetrics (Container)                 │       │
│  │  - Port: 127.0.0.1:8428 (internal only)      │       │
│  │  - Retention: 90 days                        │       │
│  │  - Status: ⏳ Aguardando dados              │       │
│  └─────────────────────────────────────────────┘       │
│                       │                                  │
│                       │ PromQL Query                     │
│                       ▼                                  │
│  ┌─────────────────────────────────────────────┐       │
│  │  Grafana (Container)                         │       │
│  │  - Port: 3000                                │       │
│  │  - DNS: monitoring.vya.digital               │       │
│  │  - Status: ⏳ Datasource não configurado    │       │
│  └─────────────────────────────────────────────┘       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## ⏭️ Próximos Passos (Recovery)

### 1. Finalizar Deploy Collector API ⏳

```bash
# No wf001
cd /opt/docker_user/n8n-prometheus-wfdb01/
docker pull adminvyadigital/n8n-collector-api:latest
docker compose restart collector-api
sleep 10
docker logs prod-collector-api --tail 30
```

**Validação**:
- Log deve mostrar: `victoria_pusher_initialized`
- Após próximo ping: `metrics_pushed_to_victoria`

### 2. Validar Dados no VictoriaMetrics ⏳

```bash
# Query para verificar dados
curl 'http://localhost:8428/api/v1/query?query=network_latency_rtt_seconds' | jq

# Deve retornar algo como:
{
  "status": "success",
  "data": {
    "resultType": "vector",
    "result": [
      {
        "metric": {
          "source_location": "wf008_brazil",
          "source_country": "BR",
          "target_location": "collector_api_usa"
        },
        "value": [1738698616, "0.3652"]
      }
    ]
  }
}
```

### 3. Configurar Datasource no Grafana 📋

**Acesso**: https://monitoring.vya.digital (após DNS configurado)
**Credenciais**: admin / ${GRAFANA_ADMIN_PASSWORD}

**Configuração**:
1. Configuration → Data Sources → Add data source
2. Type: **Prometheus**
3. Name: `VictoriaMetrics`
4. URL: `http://victoria-metrics:8428`
5. Access: **Server** (via Grafana backend)
6. Save & Test → Deve retornar "Data source is working"

### 4. Importar Dashboard N8N 📊

**Arquivo**: `n8n-tuning/docker/grafana/dashboards/n8n-node-performance.json`

**Processo**:
1. Dashboards → Import → Upload JSON
2. Ajustar datasource UID se necessário
3. Verificar queries funcionando

**Queries Esperadas**:
- `n8n_node_execution_time_ms`
- `n8n_workflow_executions_total`
- `n8n_workflow_execution_duration_seconds`

### 5. Configurar Coleta de Métricas N8N 🔄

**Baseado em**: `n8n-tuning/scripts/`

**Scripts a Adaptar**:
1. `n8n_metrics_exporter.py` - Workflows e execuções
2. `n8n_node_metrics_exporter.py` - Métricas por node

**Cron Sugerido**:
```bash
# Coletar a cada hora
0 * * * * /path/to/n8n_metrics_exporter.py
0 * * * * /path/to/n8n_node_metrics_exporter.py
```

---

## 📝 Comandos de Diagnóstico

### wf001 (USA)

```bash
# Health checks
curl localhost:8428/health  # VictoriaMetrics
curl localhost:3000/api/health  # Grafana
curl localhost:5001/health  # Collector API

# Métricas Prometheus
curl localhost:5001/metrics | grep -E '^(collector|database|network)'

# Logs
docker logs prod-collector-api --tail 50
docker logs prod-victoria-metrics --tail 50

# Query VictoriaMetrics
curl 'http://localhost:8428/api/v1/query?query=up'
curl 'http://localhost:8428/api/v1/query?query=network_latency_rtt_seconds'
curl 'http://localhost:8428/api/v1/label/__name__/values'  # Lista todas métricas
```

### wf008 (Brasil)

```bash
# Logs do Ping Service
docker logs prod-ping-service --tail 50

# Ver últimos pings enviados
docker logs prod-ping-service | grep ping_success | tail -10

# Verificar variáveis de ambiente
docker exec prod-ping-service printenv | grep COLLECTOR
```

---

## 🔐 Credenciais e Configurações

### API Keys
- **Collector API Key**: `BR*sL9aqutR-QO_hA3+a3tlYaXIBA!R3jit!lglB2j#-t_396T*?fRoNI2i6et1@`
- Localização: `.env` em ambos servidores
- Uso: Header `X-API-Key` em requests

### Database (wfdb02.vya.digital)
- **PostgreSQL**: Port 5432, database `monitor_db`, user `monitor_user`
- **MySQL**: Port 3306, database `monitor_db`, user `monitor_user`
- **Password**: N9T$Si?hic=@0ho0rAGIdraf#IxLhl18

### Grafana
- **User**: admin
- **Password**: ${GRAFANA_ADMIN_PASSWORD} (no .env)
- **URL**: http://localhost:3000 (internal) ou monitoring.vya.digital (public)

---

## 🔧 Troubleshooting Guide

### Ping 401 Unauthorized
1. Verificar `.env` tem `COLLECTOR_API_KEY`
2. Verificar container carregou variável: `docker exec prod-ping-service printenv | grep COLLECTOR`
3. Verificar imagem atualizada: `docker image inspect ping-service | grep Created`
4. Rebuild se necessário: `docker compose down && docker compose up -d`

### VictoriaMetrics Sem Dados
1. Verificar collector-api logs: `docker logs prod-collector-api | grep victoria`
2. Verificar VM healthy: `curl localhost:8428/health`
3. Listar métricas disponíveis: `curl localhost:8428/api/v1/label/__name__/values`
4. Verificar timestamp correto (Unix milliseconds)

### Grafana Datasource Não Conecta
1. Verificar URL: `http://victoria-metrics:8428` (DNS interno Docker)
2. Verificar VM respondendo: `docker exec prod-grafana curl http://victoria-metrics:8428/health`
3. Verificar network: `docker inspect prod-grafana | grep Networks`
4. Deve estar em `monitoring-net` com victoria-metrics

---

## 📚 Referências

### Documentação
- VictoriaMetrics API: https://docs.victoriametrics.com/Single-server-VictoriaMetrics.html#prometheus-querying-api-usage
- Grafana Datasources: https://grafana.com/docs/grafana/latest/datasources/prometheus/
- FastAPI Async: https://fastapi.tiangolo.com/async/

### Arquivos de Referência
- `n8n-tuning/scripts/n8n_metrics_exporter.py` - Exemplo funcionando
- `n8n-tuning/docker/grafana/dashboards/*.json` - Dashboards prontos
- `.copilot-strict-rules.md` - Regras do projeto

---

**Recovery Point**: 2026-02-04 17:45
**Próxima Ação**: Deploy collector-api atualizado no wf001
**Estado**: ⏳ Aguardando validação de dados no VictoriaMetrics
