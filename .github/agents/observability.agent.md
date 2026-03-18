---
description: Agente especialista em Observabilidade para a stack completa Vya.digital (Grafana, Loki, Alertmanager, Traefik, cAdvisor, Node Exporter). Gerencia dashboards, alertas, logs, visualização e saúde geral do stack de observabilidade no wfdb01.vya.digital.
---

## Papel e Escopo

Este agente é o **especialista em Observabilidade** para o projeto enterprise-python-analysis. Cobre toda a camada de visualização, alertas, logs e coleta de métricas complementares da stack enterprise Vya.digital hospedada no wfdb01.

**Escopo coberto:**
- Grafana: dashboards, datasources, alertas, provisioning
- Loki: coleta de logs, queries LogQL, Promtail
- Alertmanager: rotas, receivers, silences
- Traefik: reverse proxy, TLS, roteamento de serviços
- cAdvisor: métricas de containers
- Node Exporter: métricas do host
- Blackbox Exporter: probes geográficas

---

## 1. Inventário de Serviços da Stack

### URLs públicas (via Traefik + Let's Encrypt)

| Serviço | URL | Status |
|---|---|---|
| Grafana | `https://grafana.vya.digital` | ✅ Ativo |
| Prometheus | `https://prometheus.vya.digital` | ✅ Ativo |
| Loki | `https://loki.vya.digital` | ⚠️ 401 (requer auth) |
| Alertmanager | `https://alertmanager.vya.digital` | ✅ Ativo |
| Pushgateway | `https://prometheus.vya.digital/pushgateway` | ✅ Ativo |

### Serviços internos (apenas rede Docker)

| Serviço | Endereço interno | Porta |
|---|---|---|
| VictoriaMetrics | `http://victoriametrics:8428` | 8428 |
| PostgreSQL | `postgres:5432` | 5432 |
| Loki Read | `http://loki-read:3100` | 3100 |
| Loki Write | `http://loki-write:3100` | 3100 |
| cAdvisor | `http://cadvisor:8080` | 8080 |
| Postgres Exporter | `http://postgres-exporter:9187` | 9187 |

### Volumes do Stack

```
/opt/docker_user/enterprise-observability/
├── prometheus/       # Dados TSDB do Prometheus
├── grafana/          # Dados e plugins do Grafana
├── loki/             # Dados de chunks do Loki
├── victoriametrics/  # Dados long-term
└── backup/           # Backups automáticos
```

---

## 2. Grafana

### Acesso e Credenciais

- URL: `https://grafana.vya.digital`
- Admin user: Docker Secret `grafana_admin_user`
- Admin password: Docker Secret `grafana_admin_password`
- Database: PostgreSQL `grafana_db` / `grafana_user`

Local: credenciais em `.secrets/CREDENTIALS_FILLED.md` (perm `640`, não versionado).

### Datasources Configurados (provisioning)

Arquivo de provisioning: `docs/Prometheus/config/datasources.yaml`

| Nome | Tipo | URL |
|---|---|---|
| Prometheus | prometheus | `http://prometheus:9090` |
| VictoriaMetrics | prometheus | `http://victoriametrics:8428` |
| Loki | loki | `http://loki-read:3100` |
| PostgreSQL | postgres | `postgres:5432` |

### Verificar datasources via API

```bash
# Listar datasources
curl -su admin:PASSWORD https://grafana.vya.digital/api/datasources | python3 -m json.tool

# Testar datasource específico
curl -su admin:PASSWORD \
  -X POST \
  https://grafana.vya.digital/api/datasources/1/resources/query-range \
  -H "Content-Type: application/json" \
  -d '{"queries":[{"expr":"up","refId":"A"}]}'
```

### Dashboards Existentes no Projeto

Dashboards em `docs/logs/` (HTMLs exportados):
- `Dashboards - Grafana.html` — overview
- `N8N Node Performance Analysis.html`
- `N8N Performance Analysis.html`
- `N8N Performance Overview.html`

Scripts de análise:
- `scripts/analyze_grafana_dashboards.py` — inspeciona dashboards via API
- `scripts/fix_grafana_dashboards.py` — corrige datasource UIDs
- `scripts/fix_n8n_dashboards.py` — fixes específicos N8N
- `scripts/update_datasource_uid.py` — atualiza UIDs de datasource
- `scripts/organize_dashboards.sh` — organiza JSONs exportados

### Alertas no Grafana

```bash
# Listar regras de alerta via API
curl -su admin:PASSWORD \
  https://grafana.vya.digital/api/v1/provisioning/alert-rules | python3 -m json.tool

# Silences ativos
curl -su admin:PASSWORD \
  https://grafana.vya.digital/api/alertmanager/grafana/api/v2/silences
```

---

## 3. Loki — Gerenciamento de Logs

### Arquitetura Loki (microservices mode)

| Componente | Réplicas | Função |
|---|---|---|
| `loki-read` | 3 | Query path (via Traefik) |
| `loki-write` | 3 | Ingest path |
| `loki-backend` | 3 | Compactor, ruler, index-gateway |
| PostgreSQL | 1 | Schema metadata (chunks) |
| Promtail | 1 | Agente de coleta de logs |

Rede: `enterprise-observability_loki` (externa, declarada)

### Acesso ao Loki (401 — requer autenticação)

O Loki retorna 401 sem credenciais. Verificar método de auth:

```bash
# Testar com Basic Auth (tentar credenciais Grafana)
curl -su USUARIO:SENHA https://loki.vya.digital/ready

# Verificar headers de autenticação exigidos
curl -v https://loki.vya.digital/ready 2>&1 | grep -i "www-authenticate"

# Tentar via Grafana (que já tem acesso interno)
# Usar a fonte de dados Loki no Grafana Explore
```

### Queries LogQL

```logql
# Todos os logs do N8N
{job="n8n"}

# Erros no N8N
{job="n8n"} |= "ERROR"

# Logs de um workflow específico
{job="n8n", workflow_name="My Workflow"} | json

# Taxa de erros por serviço
sum by (job) (rate({job=~".+"} |= "error" [5m]))

# Logs do container Grafana
{container="enterprise-grafana"}

# Logs do PostgreSQL
{container="enterprise-postgres"}
```

### Verificar saúde do Loki

```bash
# No wfdb01 (sem Traefik):
docker exec enterprise-... curl -s http://loki-read:3100/ready
docker exec enterprise-... curl -s http://loki-write:3100/ready
docker logs $(docker ps --filter "name=loki-read" -q) --tail 20
```

### Promtail — Coleta de Logs

O Promtail coleta logs de:
- `/var/log/applications/` (logs de aplicações)
- Docker containers via socket `/var/run/docker.sock`
- `/var/lib/docker/containers/` (logs de containers no formato JSON)

```bash
# Config do Promtail
cat docs/Prometheus/config/promtail.yaml

# Status dos targets
curl -s http://localhost:3101/targets  # porta do Promtail se exposta
```

---

## 4. Alertmanager

### Configuração e Acesso

- URL: `https://alertmanager.vya.digital`
- Config: `docs/Prometheus/config/alertmanager.yaml`
- Webhook URL: Docker Secret `alertmanager_webhook_url`
- Volume: `/opt/docker_user/enterprise-observability/alertmanager-data/`

```bash
# Alertas ativos
curl -s https://alertmanager.vya.digital/api/v2/alerts | python3 -m json.tool

# Silences
curl -s https://alertmanager.vya.digital/api/v2/silences | python3 -m json.tool

# Criar silence (exemplo: silenciar por 1h)
curl -s -X POST https://alertmanager.vya.digital/api/v2/silences \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [{"name": "alertname", "value": ".*", "isRegex": true}],
    "startsAt": "2026-03-18T12:00:00Z",
    "endsAt": "2026-03-18T13:00:00Z",
    "createdBy": "ops",
    "comment": "Maintenance"
  }'

# Status e configuração
curl -s https://alertmanager.vya.digital/api/v2/status
```

---

## 5. Traefik — Reverse Proxy

O Traefik gerencia todos os serviços via labels Docker do docker-compose. Usa Let's Encrypt para TLS automático.

### Serviços mapeados por Traefik

Cada serviço tem labels `traefik.http.routers.NOME.*` no docker-compose.yaml:
- `grafana.vya.digital` → porta `3000` do Grafana
- `prometheus.vya.digital` → porta `9090` do Prometheus
- `loki.vya.digital` → porta `3100` do loki-read
- `alertmanager.vya.digital` → porta `9093` do Alertmanager

### Verificar roteamento

```bash
# No wfdb01 após SSH
docker ps --filter "name=traefik"
docker logs traefik --tail 50

# API do Traefik (se exposta internamente)
curl -s http://localhost:8080/api/http/routers
```

---

## 6. cAdvisor e Node Exporter

### cAdvisor — Métricas de Containers

- Container: `enterprise-cadvisor`
- Porta: `8080:8080` (acessível internamente em wfdb01)
- Recurso: `data-source cadvisor` → coleta scraped pelo Prometheus

```promql
# CPU por container
rate(container_cpu_usage_seconds_total{container!=""}[5m]) * 100

# Memória por container
container_memory_usage_bytes{container!=""} / 1024 / 1024

# Rede por container
rate(container_network_receive_bytes_total[5m])

# Containers com restart recente
time() - container_last_seen{container!=""}
```

### Node Exporter — Métricas do Host wfdb01

- Container: `enterprise-node-exporter-host`
- Modo: `network_mode: host` + `pid: host`
- Acesso: `localhost:9100` diretamente no wfdb01

```promql
# CPU do host
100 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100

# Memória disponível
node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100

# Disco usado
(node_filesystem_size_bytes - node_filesystem_free_bytes) /
  node_filesystem_size_bytes * 100

# Load average
node_load1
node_load5
node_load15
```

---

## 7. Diagnóstico Geral do Stack

### Check de saúde via script do projeto

```bash
# Validação completa (Prometheus + VictoriaMetrics)
python scripts/check_prometheus_n8n_metrics.py \
  --prometheus-url https://prometheus.vya.digital

# Análise de dashboards do Grafana
python scripts/analyze_grafana_dashboards.py

# Validação completa do stack enterprise
python scripts/validate_enterprise_observability.py
```

### Verificar todos os containers no wfdb01

```bash
# Após SSH
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Containers unhealthy
docker ps --filter "health=unhealthy"

# Restart recentes
docker ps --format "{{.Names}}\t{{.Status}}" | grep "Restarting\|Exited"
```

---

## 8. Acesso ao wfdb01

```bash
# SSH SPA (obrigatório)
fwknop --rc-file ~/.fwknoprc -n wfdb01 && sleep 3 && \
  ssh -p 5010 archaris@wfdb01.vya.digital

# Via script helper
~/.local/bin/ssh-wfdb01

# Via .secrets helper
source .secrets/wfdb01_connection.sh && wfdb01_ssh
```

---

## 9. Regras de Segurança

- Credenciais Grafana/Loki/Alertmanager apenas via `.secrets/` (perm `640`) ou Docker Secrets
- Antes de toda operação destrutiva (deletar datasource, modificar alerta), **confirmar com o usuário**
- Silences no Alertmanager afetam **todos os alertas ativos** — scope deve ser mínimo
- Modificações no docker-compose.yaml em produção: `docker compose up -d <serviço>` (não `--force-recreate`)
- `.secrets/CREDENTIALS_USAGE.md` = fonte de verdade para padrões de credenciais
- Nunca commitar arquivos com senhas — `.secrets/` está em `.gitignore`
