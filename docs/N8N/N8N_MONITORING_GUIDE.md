# N8N Monitoring Guide

**Servidor:** WF001 (31.220.103.208)  
**Data de Implementação:** 05/02/2026  
**Status:** ✅ Configurado no Prometheus

---

## 🎯 Visão Geral

Monitoramento completo do N8N (workflow automation) rodando no servidor **WF001** através de métricas nativas expostas pelo N8N.

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│  N8N (WF001 - 31.220.103.208:5678)                         │
│  • Workflows automation                                     │
│  • Metrics endpoint: /metrics                               │
└────────────────────────┬────────────────────────────────────┘
                         │ (scrape 15s)
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  Prometheus                                                  │
│  • Job: n8n                                                  │
│  • Remote write → VictoriaMetrics (12 meses)                │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  Grafana                                                     │
│  • Dashboard N8N Workflows                                   │
│  • Alertas de falhas                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Configuração do N8N

### 1. Habilitar Métricas no N8N

**Variáveis de ambiente necessárias:**

```bash
# No servidor WF001, editar docker-compose.yaml ou .env do N8N

N8N_METRICS=true
N8N_METRICS_PREFIX=n8n_
N8N_METRICS_INCLUDE_DEFAULT_METRICS=true
N8N_METRICS_INCLUDE_CACHE_METRICS=true
N8N_METRICS_INCLUDE_MESSAGE_EVENT_BUS_METRICS=true
```

**Exemplo docker-compose.yaml no WF001:**

```yaml
version: '3.8'

services:
  n8n:
    image: n8nio/n8n:latest
    container_name: n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      # Configurações básicas
      - N8N_HOST=n8n.vya.digital
      - N8N_PORT=5678
      - N8N_PROTOCOL=https
      - WEBHOOK_URL=https://n8n.vya.digital/
      
      # Métricas Prometheus ✅
      - N8N_METRICS=true
      - N8N_METRICS_PREFIX=n8n_
      - N8N_METRICS_INCLUDE_DEFAULT_METRICS=true
      - N8N_METRICS_INCLUDE_CACHE_METRICS=true
      - N8N_METRICS_INCLUDE_MESSAGE_EVENT_BUS_METRICS=true
      
      # Database (ajustar conforme necessário)
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_PORT=5432
    volumes:
      - n8n-data:/home/node/.n8n
    networks:
      - n8n-network

volumes:
  n8n-data:

networks:
  n8n-network:
```

### 2. Reiniciar N8N

```bash
# No servidor WF001 (31.220.103.208)
ssh root@31.220.103.208

# Reiniciar container N8N
docker compose restart n8n

# Verificar logs
docker logs -f n8n
```

### 3. Validar Endpoint

```bash
# Testar endpoint de métricas
curl http://31.220.103.208:5678/metrics

# Deve retornar algo como:
# n8n_workflow_executions_total{workflow_id="1",status="success"} 42
# n8n_node_executions_total{node_type="httpRequest"} 150
# ...
```

---

## 📊 Métricas Disponíveis

### Métricas de Workflows

```promql
# Total de execuções por workflow
n8n_workflow_executions_total{workflow_id="123",status="success"}
n8n_workflow_executions_total{workflow_id="123",status="error"}

# Duração das execuções (buckets de histograma)
n8n_workflow_execution_duration_seconds_bucket{workflow_id="123"}
n8n_workflow_execution_duration_seconds_sum{workflow_id="123"}
n8n_workflow_execution_duration_seconds_count{workflow_id="123"}
```

### Métricas de Nós

```promql
# Execuções por tipo de nó
n8n_node_executions_total{node_type="httpRequest"}
n8n_node_executions_total{node_type="webhook"}
n8n_node_executions_total{node_type="set"}
```

### Métricas de Cache (se habilitado)

```promql
# Cache hits/misses
n8n_cache_hits_total
n8n_cache_misses_total
n8n_cache_updates_total
```

### Métricas do Message Event Bus

```promql
# Mensagens processadas
n8n_message_event_bus_messages_total{event_type="workflow.success"}
n8n_message_event_bus_messages_total{event_type="workflow.error"}
```

### Métricas Padrão Node.js

```promql
# Memória
nodejs_heap_size_total_bytes
nodejs_heap_size_used_bytes
nodejs_external_memory_bytes

# CPU
process_cpu_user_seconds_total
process_cpu_system_seconds_total

# Event Loop
nodejs_eventloop_lag_seconds
```

---

## 📈 Queries Úteis para Dashboards

### Taxa de Execuções por Hora

```promql
sum(rate(n8n_workflow_executions_total[1h])) by (status)
```

### Taxa de Erro (%)

```promql
(
  sum(rate(n8n_workflow_executions_total{status="error"}[5m])) 
  / 
  sum(rate(n8n_workflow_executions_total[5m]))
) * 100
```

### Top 5 Workflows Mais Executados

```promql
topk(5, sum by (workflow_id) (
  rate(n8n_workflow_executions_total[24h])
))
```

### Duração Média (P95)

```promql
histogram_quantile(0.95, 
  sum by (le, workflow_id) (
    rate(n8n_workflow_execution_duration_seconds_bucket[5m])
  )
)
```

### Workflows Mais Lentos (P99)

```promql
topk(5, 
  histogram_quantile(0.99, 
    sum by (le, workflow_id) (
      rate(n8n_workflow_execution_duration_seconds_bucket[5m])
    )
  )
)
```

### Taxa de Sucesso por Workflow

```promql
sum by (workflow_id) (
  rate(n8n_workflow_executions_total{status="success"}[5m])
) 
/ 
sum by (workflow_id) (
  rate(n8n_workflow_executions_total[5m])
)
```

### Nós Mais Utilizados

```promql
topk(10, sum by (node_type) (
  rate(n8n_node_executions_total[1h])
))
```

### Uso de Memória

```promql
nodejs_heap_size_used_bytes{job="n8n"} / 1024 / 1024
```

---

## 🎨 Dashboard Grafana

### Importar Dashboard Pronto

```bash
# Dashboard ID: 17344 (N8N Workflow Monitoring)
# Grafana → Dashboards → Import → 17344
```

### Criar Dashboard Custom

**Painéis sugeridos:**

1. **Overview**
   - Total de workflows ativos
   - Execuções nas últimas 24h
   - Taxa de erro atual

2. **Performance**
   - Duração média (P50, P95, P99)
   - Workflows mais lentos
   - Event loop lag

3. **Errors**
   - Taxa de erro por workflow
   - Últimos 10 erros
   - Workflows com mais falhas

4. **Resources**
   - Uso de memória heap
   - CPU usage
   - Cache hit ratio

5. **Workflows Details**
   - Execuções por workflow (gráfico de barras)
   - Tendência de execuções (time series)
   - Status de cada workflow

---

## 🚨 Alertas Recomendados

### 1. Taxa de Erro Alta

```yaml
# rules/n8n-alerts.yml
groups:
  - name: n8n_alerts
    interval: 30s
    rules:
      - alert: N8NHighErrorRate
        expr: |
          (
            sum(rate(n8n_workflow_executions_total{status="error"}[5m])) 
            / 
            sum(rate(n8n_workflow_executions_total[5m]))
          ) > 0.1
        for: 5m
        labels:
          severity: warning
          service: n8n
          server: wf001
        annotations:
          summary: "N8N error rate is high"
          description: "Error rate is {{ printf \"%.2f\" $value }}% (threshold: 10%)"
```

### 2. Workflow Falhando Constantemente

```yaml
- alert: N8NWorkflowConstantFailure
  expr: |
    rate(n8n_workflow_executions_total{status="error"}[15m]) > 0.5
  for: 15m
  labels:
    severity: critical
    service: n8n
  annotations:
    summary: "Workflow {{ $labels.workflow_id }} is constantly failing"
    description: "Workflow has {{ printf \"%.2f\" $value }} failures/second"
```

### 3. Execução Muito Lenta

```yaml
- alert: N8NSlowExecution
  expr: |
    histogram_quantile(0.95, 
      rate(n8n_workflow_execution_duration_seconds_bucket[5m])
    ) > 300
  for: 10m
  labels:
    severity: warning
    service: n8n
  annotations:
    summary: "N8N workflow execution is slow"
    description: "P95 execution time is {{ printf \"%.2f\" $value }}s (threshold: 300s)"
```

### 4. Alto Uso de Memória

```yaml
- alert: N8NHighMemoryUsage
  expr: |
    (nodejs_heap_size_used_bytes{job="n8n"} / nodejs_heap_size_total_bytes{job="n8n"}) > 0.9
  for: 5m
  labels:
    severity: warning
    service: n8n
  annotations:
    summary: "N8N memory usage is high"
    description: "Heap usage is {{ printf \"%.2f\" $value }}% (threshold: 90%)"
```

### 5. N8N Down

```yaml
- alert: N8NDown
  expr: up{job="n8n"} == 0
  for: 2m
  labels:
    severity: critical
    service: n8n
    server: wf001
  annotations:
    summary: "N8N is down"
    description: "N8N on WF001 (31.220.103.208) has been down for 2 minutes"
```

---

## 🔍 Troubleshooting

### Métricas não aparecem

```bash
# 1. Verificar se N8N está expondo métricas
curl http://31.220.103.208:5678/metrics

# 2. Verificar variáveis de ambiente
docker exec n8n env | grep N8N_METRICS

# 3. Ver logs do N8N
docker logs n8n | grep -i metric

# 4. Verificar se Prometheus está coletando
# Prometheus UI → Status → Targets → procurar "n8n"
```

### Porta 5678 não acessível

```bash
# Verificar firewall no WF001
ssh root@31.220.103.208
ufw status
ufw allow 5678/tcp

# Verificar se container expõe porta
docker ps | grep n8n
docker port n8n
```

### Métricas aparecendo mas sem dados

```bash
# Executar algum workflow para gerar métricas
# As métricas só aparecem após primeira execução

# Ou criar workflow de teste simples que executa a cada 1 minuto
```

---

## 📋 Checklist de Implementação

- [ ] N8N rodando no WF001 (31.220.103.208)
- [ ] Variáveis `N8N_METRICS=true` configuradas
- [ ] Container N8N reiniciado
- [ ] Endpoint `/metrics` acessível externamente
- [ ] Porta 5678 liberada no firewall
- [ ] Job `n8n` adicionado ao Prometheus
- [ ] Prometheus coletando (verificar /targets)
- [ ] Métricas visíveis em query Prometheus
- [ ] Dashboard criado/importado no Grafana
- [ ] Alertas configurados no AlertManager
- [ ] Testado com execução de workflow

---

## 🚀 Deploy Rápido

```bash
# 1. SSH no servidor WF001
ssh root@31.220.103.208

# 2. Editar docker-compose do N8N
cd /path/to/n8n
nano docker-compose.yaml

# Adicionar variáveis de ambiente:
# N8N_METRICS=true
# N8N_METRICS_PREFIX=n8n_
# N8N_METRICS_INCLUDE_DEFAULT_METRICS=true

# 3. Reiniciar
docker compose restart n8n

# 4. Validar
curl http://localhost:5678/metrics

# 5. Liberar firewall (se necessário)
ufw allow from 82.197.64.145 to any port 5678 comment 'Prometheus WFDB02'

# 6. No servidor Prometheus (WFDB02 ou local)
# Verificar config/prometheus.yaml tem job n8n
# Reiniciar Prometheus
docker compose restart prometheus

# 7. Validar no Grafana
# Ir em Explore → Datasource: Prometheus
# Query: up{job="n8n"}
# Deve retornar: 1
```

---

## 📚 Referências

- **N8N Metrics Documentation:** https://docs.n8n.io/hosting/configuration/configuration-examples/metrics/
- **Prometheus Configuration:** https://prometheus.io/docs/prometheus/latest/configuration/configuration/
- **Grafana Dashboard:** https://grafana.com/grafana/dashboards/17344

---

**Servidor:** WF001 (31.220.103.208)  
**Porta:** 5678  
**Endpoint:** http://31.220.103.208:5678/metrics  
**Job Prometheus:** n8n  
**Última Atualização:** 05/02/2026
