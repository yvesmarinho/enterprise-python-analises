# 📋 TODO - N8N Monitoring System

**Última Atualização**: 2026-02-04 18:00
**Projeto**: N8N Monitoring System
**Status**: 🟡 In Progress (70% Complete)

---

## 🔥 URGENTE - Próxima Sessão

### 1. Deploy Collector API ⏰ 5min
**Prioridade**: 🔴 CRÍTICA
**Bloqueador**: Sim - impede validação de dados

**Steps**:
```bash
# Verificar se push completou
docker images | grep collector-api

# wf001
ssh -p 5010 archaris@wf001.vya.digital
cd /opt/docker_user/n8n-prometheus-wfdb01/
docker pull adminvyadigital/n8n-collector-api:latest
docker compose restart collector-api
sleep 15
docker logs prod-collector-api --tail 50 | grep victoria
```

**Validação**:
- [ ] Log mostra `victoria_pusher_initialized`
- [ ] Após ping: `metrics_pushed_to_victoria`
- [ ] Sem erros HTTP

**Assigned**: -
**Due**: Início da próxima sessão

---

### 2. Validar Dados no VictoriaMetrics ⏰ 3min
**Prioridade**: 🔴 CRÍTICA
**Depende de**: #1

**Steps**:
```bash
# Query após 1-2 minutos
curl -s 'http://localhost:8428/api/v1/query?query=network_latency_rtt_seconds' | jq

# Verificar labels
curl -s 'http://localhost:8428/api/v1/label/__name__/values' | jq
```

**Validação**:
- [ ] Result não vazio
- [ ] Labels: source_location, source_country, target_location
- [ ] Valores numéricos (~0.35-0.40)
- [ ] Timestamp recente

**Assigned**: -
**Due**: Após #1

---

### 3. Configurar Grafana Datasource ⏰ 5min
**Prioridade**: 🟡 ALTA
**Depende de**: #2

**Steps**:
1. Acessar http://localhost:3000 (ou monitoring.vya.digital)
2. Configuration → Data Sources → Add data source
3. Type: **Prometheus**
4. Name: `VictoriaMetrics`
5. URL: `http://victoria-metrics:8428`
6. Access: **Server**
7. Save & Test

**Validação**:
- [ ] "Data source is working" message
- [ ] Explore mostra métricas disponíveis
- [ ] Query test retorna dados

**Assigned**: -
**Due**: Mesma sessão que #2

---

## 🎯 ALTA PRIORIDADE

### 4. Importar Dashboard N8N ⏰ 10min
**Prioridade**: 🟡 ALTA
**Depende de**: #3

**File**: `n8n-tuning/docker/grafana/dashboards/n8n-node-performance.json`

**Steps**:
1. Dashboards → Import → Upload JSON file
2. Ajustar datasource UID se necessário
3. Save

**Observações**:
- Dashboard pode estar vazio (normal - N8N não integrado ainda)
- Queries devem funcionar (mesmo retornando vazio)
- UID do datasource pode precisar ajuste manual

**Validação**:
- [ ] Dashboard importado sem erros
- [ ] Queries executam (podem retornar vazio)
- [ ] Panels renderizam corretamente

**Assigned**: -
**Due**: 2026-02-05

---

### 5. Adaptar Script n8n_metrics_exporter ⏰ 30min
**Prioridade**: 🟡 ALTA

**File**: `n8n-tuning/scripts/n8n_metrics_exporter.py`

**Changes Needed**:
- [ ] Atualizar credenciais N8N (`.secrets/credentials.json`)
- [ ] Atualizar VictoriaMetrics URL
- [ ] Testar coleta manual
- [ ] Verificar métricas no VM
- [ ] Validar formato

**Validação**:
```bash
python3 n8n_metrics_exporter.py
# Deve mostrar: ✅ Métricas enviadas para Victoria Metrics
```

**Assigned**: -
**Due**: 2026-02-05

---

### 6. Adaptar Script n8n_node_metrics_exporter ⏰ 30min
**Prioridade**: 🟡 ALTA

**File**: `n8n-tuning/scripts/n8n_node_metrics_exporter.py`

**Changes Needed**:
- [ ] Atualizar credenciais PostgreSQL
- [ ] Atualizar VictoriaMetrics URL
- [ ] Testar conexão DB
- [ ] Testar coleta manual
- [ ] Verificar métricas agregadas

**Validação**:
```bash
python3 n8n_node_metrics_exporter.py
# Deve mostrar: Top 10 nodes mais lentos
```

**Assigned**: -
**Due**: 2026-02-05

---

## 📊 MÉDIA PRIORIDADE

### 7. Configurar Cron Jobs ⏰ 15min
**Prioridade**: 🟢 MÉDIA
**Depende de**: #5, #6

**Schedule Sugerido**:
```cron
# Workflows e execuções (hourly)
0 * * * * /path/to/n8n_metrics_exporter.py >> /var/log/n8n-metrics.log 2>&1

# Node metrics (hourly)
5 * * * * /path/to/n8n_node_metrics_exporter.py >> /var/log/n8n-node-metrics.log 2>&1
```

**Validação**:
- [ ] Cron instalado e rodando
- [ ] Logs gerados corretamente
- [ ] Métricas aparecem no VM a cada hora
- [ ] Dashboard atualiza automaticamente

**Assigned**: -
**Due**: 2026-02-06

---

### 8. Configurar DNS Público ⏰ 10min
**Prioridade**: 🟢 MÉDIA

**Records Necessários**:
```
monitoring.vya.digital      A    <wf001_public_ip>
api-monitoring.vya.digital  A    <wf001_public_ip>
```

**TTL**: Start with 300s (5min), increase to 3600s after validation

**Steps**:
1. Adicionar A records no DNS provider
2. Aguardar propagação (5-15min)
3. Testar: `nslookup monitoring.vya.digital`
4. Acessar https://monitoring.vya.digital
5. Verificar SSL (Let's Encrypt via Traefik)

**Validação**:
- [ ] DNS resolve para IP correto
- [ ] HTTPS funciona
- [ ] Certificado válido
- [ ] Grafana acessível
- [ ] Collector API acessível

**Assigned**: -
**Due**: 2026-02-06

---

### 9. Criar Dashboard Brasil→USA Latency ⏰ 20min
**Prioridade**: 🟢 MÉDIA
**Depende de**: #3

**Panels**:
1. **Time Series**: network_latency_rtt_seconds (last 24h)
2. **Stat**: Current RTT
3. **Stat**: Average RTT (24h)
4. **Stat**: Max RTT (24h)
5. **Stat**: Min RTT (24h)
6. **Table**: Last 20 pings with details

**Queries**:
```promql
# Panel 1 - Time series
network_latency_rtt_seconds{source_country="BR"}

# Panel 2 - Current
network_latency_rtt_seconds{source_country="BR"}

# Panel 3 - Average
avg_over_time(network_latency_rtt_seconds{source_country="BR"}[24h])

# Panel 4 - Max
max_over_time(network_latency_rtt_seconds{source_country="BR"}[24h])

# Panel 5 - Min
min_over_time(network_latency_rtt_seconds{source_country="BR"}[24h])
```

**Validação**:
- [ ] Todos panels renderizam
- [ ] Dados corretos (~350-400ms)
- [ ] Updates a cada 30s
- [ ] Export JSON para versionamento

**Assigned**: -
**Due**: 2026-02-06

---

## 🔧 BAIXA PRIORIDADE (Melhorias)

### 10. Adicionar Grafana Alerting ⏰ 30min
**Prioridade**: 🟣 BAIXA

**Alerts Sugeridos**:
1. RTT > 1000ms por 5min
2. Ping failure rate > 10%
3. Collector API down
4. VictoriaMetrics disk > 80%

**Due**: 2026-02-07

---

### 11. Configurar Backup VictoriaMetrics ⏰ 20min
**Prioridade**: 🟣 BAIXA

**Strategy**:
- Daily snapshots para S3
- Retention: 30 days
- Test restore procedure

**Due**: 2026-02-07

---

### 12. Documentação de Operação ⏰ 60min
**Prioridade**: 🟣 BAIXA

**Topics**:
- Runbook
- Troubleshooting guide
- Backup & restore
- Monitoring & alerts
- Scale procedures

**Due**: 2026-02-08

---

## ✅ CONCLUÍDO

### Session 2026-02-04

- [x] Diagnosticar problema autenticação Ping Service
- [x] Corrigir config.py com alias="COLLECTOR_API_KEY"
- [x] Build e deploy ping-service atualizado
- [x] Validar pings funcionando (200 OK, ~400ms RTT)
- [x] Diagnosticar VictoriaMetrics vazio
- [x] Implementar victoria_pusher.py
- [x] Integrar pusher no collector-api
- [x] Build collector-api atualizado
- [x] Push para registry (em progresso ao fim da sessão)
- [x] Documentar sessão completa (1200+ linhas)

### Session 2026-02-03

- [x] Deploy completo wf001 (VictoriaMetrics, Grafana, Collector API)
- [x] Corrigir permissões (Grafana UID 472, VM UID 1001)
- [x] Corrigir paths relativos no docker-compose
- [x] Validar health de todos containers
- [x] Deploy wf008 (Ping Service)
- [x] Configurar environment variables

### Pre-Sessions

- [x] Arquitetura do sistema
- [x] Desenvolvimento Collector API
- [x] Desenvolvimento Ping Service
- [x] Setup de infraestrutura
- [x] Configuração de segurança (VictoriaMetrics internal-only)
- [x] Documentação de deployment

---

## 📊 Progress Tracker

```
Overall: ████████████████░░░░ 70%

Components:
├─ Infrastructure        ██████████████████████ 100%
├─ Connectivity          ██████████████████████ 100%
├─ Data Collection       ████████████████░░░░░░  80%
├─ Data Storage          ██████████░░░░░░░░░░░░  50%
├─ Visualization         ████░░░░░░░░░░░░░░░░░░  20%
└─ N8N Integration       ░░░░░░░░░░░░░░░░░░░░░░   0%

Critical Path:
[✅ Deploy] → [⏳ Validate] → [⏳ Configure] → [⏳ Integrate]
```

---

## 🎯 Definition of Done

### Phase 1: Core Monitoring (Current) - 70%
- [x] Deployment completo
- [x] Pings funcionando
- [ ] ⏳ Dados no VictoriaMetrics
- [ ] ⏳ Grafana configurado
- [ ] ⏳ Dashboard básico funcionando

### Phase 2: N8N Integration - 0%
- [ ] Scripts adaptados
- [ ] Cron configurado
- [ ] Dashboards N8N funcionando
- [ ] Métricas por node disponíveis

### Phase 3: Production Ready - 0%
- [ ] DNS público
- [ ] SSL certificates
- [ ] Alerting configurado
- [ ] Backup procedures
- [ ] Documentation completa

---

## 📝 Notes

### Blockers
- ⏳ Collector API push em andamento (blocking: data validation)

### Dependencies
```
#1 (Deploy) ← MUST DO FIRST
   ↓
#2 (Validate) ← Blocks everything else
   ↓
#3 (Grafana DS) ← Enables dashboards
   ├→ #4 (Import Dashboard)
   └→ #9 (Create Dashboard)

#5 (N8N Exporter) ← Independent
#6 (Node Exporter) ← Independent
   ↓
#7 (Cron) ← Needs both exporters

#8 (DNS) ← Independent, nice-to-have
```

### Time Estimates
- **Next Session**: ~1h (items #1-3)
- **Complete Phase 1**: ~3h (items #1-4, #9)
- **Complete Phase 2**: ~5h (items #5-7)
- **Complete Phase 3**: ~3h (items #8, #10-12)
- **Total Remaining**: ~11h (~3 sessions)

---

**Atualizado**: 2026-02-04 18:00
**Próxima Revisão**: Início da próxima sessão
**Status**: Ready for handover
