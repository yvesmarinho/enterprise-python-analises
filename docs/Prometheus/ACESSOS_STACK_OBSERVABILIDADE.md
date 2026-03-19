# 🗺️ Acessos — Stack de Observabilidade (wfdb01)

**Fonte**: `docker-compose.yaml` — Enterprise Observability Stack
**Última análise**: 19/03/2026
**Host**: `wfdb01.vya.digital` (SSH porta 5010, acesso via fwknop SPA)

---

## 🌐 Endpoints Públicos (via Traefik HTTPS)

| Serviço | URL Pública | Porta Interna | Autenticação |
|---|---|---|---|
| Grafana | `https://grafana.vya.digital` | 3000 | Login (admin/admin) — `grafana_admin_*` secrets |
| Prometheus | `https://prometheus.vya.digital` | 9090 | Open (protegido por Traefik) |
| Loki | `https://loki.vya.digital` | 3100 | Open (Traefik) |
| Alertmanager | `https://alertmanager.vya.digital` | 9093 | Open (Traefik) |
| Pushgateway | `https://prometheus.vya.digital/pushgateway` | 9091 | Open (via strip-prefix) |

---

## 🔒 Portas Expostas no Host (sem Traefik)

| Serviço | Container | Porta Host | Porta Container | Observação |
|---|---|---|---|---|
| Grafana | `enterprise-grafana` | `3002` | `3000` | Acesso direto HTTP (além do Traefik) |
| Prometheus | `enterprise-prometheus` | `9091` | `9090` | Acesso direto HTTP (além do Traefik) |
| Alertmanager | `enterprise-alertmanager` | `9093` | `9093` | Acesso direto HTTP (além do Traefik) |
| cAdvisor | `enterprise-cadvisor` | `8080` | `8080` | Sem Traefik — só host |
| Node Exporter | `enterprise-node-exporter-host` | `9100` | `9100` | `network_mode: host` — porta padrão |

---

## 🔐 Serviços Internos APENAS (sem acesso externo)

| Serviço | Container | Endpoint Interno | Motivo |
|---|---|---|---|
| **VictoriaMetrics** | `enterprise-victoriametrics` | `http://victoriametrics:8428` | ⚠️ Sem `ports:`, sem Traefik — **somente rede Docker** |
| PostgreSQL | `enterprise-postgres` | `postgres:5432` | Interno — dados do Grafana/Loki |
| Postgres Exporter | `enterprise-postgres-exporter` | `postgres-exporter:9187` | Interno — scraped pelo Prometheus |
| Promtail | `enterprise-promtail` | — | Push-only para Loki |
| Loki Write | `loki-write` (3 réplicas) | `loki-write:3100` | Interno — escrita |
| Loki Backend | `loki-backend` (3 réplicas) | `loki-backend:3100` | Interno — compactação/índice |

---

## ⚠️ VictoriaMetrics — Problema de Acesso do Host

O container `enterprise-victoriametrics` **não expõe portas para o host** e **não tem rota Traefik**.

> Comentário no docker-compose: *"UI não exposta via Traefik por segurança. Apenas API em http://victoriametrics:8428 disponível internamente"*

### Opções de Acesso para o ANA-001

**Opção A — `docker exec` em container da mesma rede (recomendado para teste rápido):**
```bash
# Executar o analyzer dentro de um container Python na rede correta
docker run --rm \
  --network enterprise-observability_loki \
  -v ~/n8n-analyzer-run:/app \
  -w /app \
  python:3.11-slim \
  bash -c "pip install -e . -q && \
    VICTORIA_METRICS_URL=http://victoriametrics:8428 \
    PROMETHEUS_URL=http://prometheus:9090 \
    python analyze_n8n_performance.py \
      --from '2026-01-01' --to '2026-01-19' \
      --step-global '1h' --output-format markdown --output-dir reports"
```

**Opção B — `docker exec` dentro do container Prometheus (já na rede):**
```bash
# Verificar se curl está disponível dentro do prometheus
docker exec enterprise-prometheus wget -qO- "http://victoriametrics:8428/health"
```

**Opção C — Expor porta temporariamente (apenas para análise pontual):**
```bash
# CUIDADO: expõe VictoriaMetrics no host sem autenticação
# Usar somente em sessão de análise e remover depois
cd /opt/docker_user/enterprise-observability
docker compose exec victoriametrics sh -c "echo OK"  # teste
# Alternativa: socat ou rinetd para fazer port-forward na loopback
socat TCP-LISTEN:8428,bind=127.0.0.1,fork \
  EXEC:"docker exec -i enterprise-victoriametrics nc 127.0.0.1 8428"
```

**Opção D — Testar conectividade pelo IP interno do container:**
```bash
VM_IP=$(docker inspect enterprise-victoriametrics \
  --format '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}')
echo "VictoriaMetrics IPs: $VM_IP"
curl -s "http://<IP>:8428/health"  # funciona apenas do host se rota existir
```

### ✅ Recomendação para ANA-001

**Usar Opção A** — `docker run` na rede `enterprise-observability_loki`:

```bash
cd ~/n8n-analyzer-run

docker run --rm \
  --network enterprise-observability_loki \
  -v "$(pwd)":/app \
  -w /app \
  python:3.11-slim \
  sh -c "pip install -e . -q && \
    VICTORIA_METRICS_URL=http://victoriametrics:8428 \
    PROMETHEUS_URL=http://prometheus:9090 \
    LOKI_URL=http://loki-gateway:3100 \
    REQUEST_TIMEOUT_SECONDS=120 \
    python analyze_n8n_performance.py \
      --from '2026-01-01' \
      --to '2026-03-19' \
      --step-global '1h' \
      --output-format markdown \
      --output-dir reports"
```

---

## 🔗 Redes Docker

| Rede | Tipo | Serviços |
|---|---|---|
| `enterprise-observability_loki` | external | Todos (rede principal do stack) |
| `app-network` | external | Grafana, Prometheus, Loki-read, Alertmanager, Pushgateway, VictoriaMetrics |

---

## 📋 Retenção de Dados

| Serviço | Retenção | Endpoint |
|---|---|---|
| Prometheus | 15 dias (máx 10GB) | `https://prometheus.vya.digital` |
| VictoriaMetrics | **12 meses** | `http://victoriametrics:8428` (interno) |
| Loki | Configurado em `loki.yaml` | `https://loki.vya.digital` |
