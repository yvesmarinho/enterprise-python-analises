# Análise Técnica: Blockers de Observability — Recomendações para Debate

**Data:** 2026-03-31
**Projeto:** enterprise-python-analysis / ANA-001
**Status:** Análise de viabilidade e impacto técnico
**Preparado para:** python-dev, docker-expert, prometheus
**Contexto:** Encerramento ANA-001 com pendências operacionais (P1 Loki + P2 Recording Rules)

---

## 1. BLOCKER P1: LOKI AUTENTICAÇÃO FALHANDO (401)

### 1.1 Diagnosis Atual

| Aspecto | Status |
|---------|--------|
| Acesso público | `https://loki.vya.digital` → **401 Unauthorized** |
| Acesso interno (wfdb01) | Não testado sistematicamente |
| Credenciais esperadas | Basic Auth ou Token (não identificado) |
| Fonte de verdade | `.secrets/CREDENTIALS_FILLED.md` (local, perm 640) |
| Impacto documentado | Alertas em `docs/TODAY_ACTIVITIES.md` e `docs/TODO.md` desde 23/03 |

### 1.2 Impacto no Stack Observability (wfdb01)

#### **Coleta de Logs (severidade: ALTA)**

```
┌─────────────────────────────────────────────────────────────┐
│ Loki Write API (loki-write:3100)                           │
│ ↓                                                            │
│ [Promtail coleta logs → envia para Loki]                    │
│ ↓                                                            │
│ Loki Store (PostgreSQL + chunks)     ← FUNCIONAL (interno)  │
│ ↓                                                            │
│ Loki Read API (loki-read:3100) ← via Traefik para externo   │
│ ↓                                                            │
│ CLIENTE REMOTO (Grafana, análises) → 401 ❌                │
└─────────────────────────────────────────────────────────────┘
```

**Achados:**
- ✅ Coleta de logs está **funcionando** (Promtail → Loki interno)
- ✅ Armazenamento está **funcionando** (Loki Write e chunks no banco)
- ❌ **Queryabilidade remota está quebrada** (Loki Read retorna 401)
- ⚠️ Grafana consegue consultar Loki? → **Verificar** (datasource interno pode ter acesso)

#### **Quem depende de Loki:**

| Consumer | Acesso | Status |
|----------|--------|--------|
| Grafana (interno) | `http://loki-read:3100` | ✅ Likel funciona |
| Análises remotas (python-analysis) | `https://loki.vya.digital` | ❌ Bloqueado |
| Alertmanager (interno) | `http://loki-read:3100` | ✅ Likel funciona |
| Promtail (interno) | `http://loki-write:3100` | ✅ Funciona |
| N8N log queries (remoto) | Via Grafana API | ⚠️ Depende de Grafana |

### 1.3 Impacto na Coleta de Logs/Métricas N8N

#### **Logs N8N (severidade: MÉDIA)**

- **Coleta:** Funciona (Promtail coleta do docker socket)
- **Armazenamento:** Funciona (Loki-write recebe)
- **Consulta remota:** QUEBRADA (401)

**Problema prático:**
Script `scripts/analyze_grafana_dashboards.py` e similares **não podem fazer LogQL queries diretamente** via `https://loki.vya.digital`. Solução atual: via Grafana Explorer/HTTP proxy ou acesso direto a wfdb01.

#### **Métricas N8N (severidade: BAIXA)**

- Promtheus scrape: ✅ Funciona
- VictoriaMetrics storage: ✅ Funciona
- Recording rules deployment: ⏳ Aguardando (P2)

**Conclusão:** Loki 401 **NÃO bloqueia "diretamente"** coleta de métricas, mas bloqueia **troubleshooting remoto** de logs contextuais.

### 1.4 Urgência Técnica

| Critério | Avaliação |
|----------|-----------|
| ANA-001 pode encerrar sem isto? | ✅ **Sim** (métricas estão OK) |
| Afeta decisão técnica sobre N8N? | ⚠️ **Parcialmente** (logs ajudariam troubleshooting futuro) |
| Bloqueia deploy de recording rules (P2)? | ❌ **Não** (são independentes) |
| Afeta alertas de performance N8N? | ❌ **Não** (baseados em métricas, não logs) |
| Impacto operacional em produção? | ⚠️ **Médio** (diagnóstico remoto prejudicado) |

**Ranking de urgência ANA-001:** 🔴 P1 **MAS** não é blocker crítico do projeto. É **operacional**.

### 1.5 Estratégia de Resolução

#### **Opção A: Debug & Fix (Recomendado para este ciclo)**

Requires coordenação com **docker-expert** (gerencia stack enterprise-observability).

```bash
# Passo 1: SSH ao wfdb01 (obrigatório SPA)
fwknop --rc-file ~/.fwknoprc -n wfdb01 && sleep 3 && \
  ssh -p 5010 archaris@wfdb01.vya.digital

# Passo 2: Verificar método de autenticação esperado
docker exec enterprise-prometheus curl -v http://localhost:3100/ready
# → Procurar headers como WWW-Authenticate

# Passo 3: Verificar configuração do Loki (Traefik + auth)
docker inspect enterprise-loki-read --format='{{json .Config.Labels}}' | python3 -m json.tool
# → Verificar labels traefik.http.middlewares.* (pode ter middleware de auth)

# Passo 4: Extrair credenciais de Loki (do Docker Secret)
docker secret inspect loki_read_basic_auth --format '{{.Spec.Data}}' | base64 -d
# OU verificar arquivo .env / docker-compose

# Passo 5: Testar auth com credenciais
curl -su USERNAME:PASSWORD https://loki.vya.digital/ready

# Passo 6: Se auth OK, adicionar credenciais ao Grafana datasource (via API)
curl -su admin:PASSWORD https://grafana.vya.digital/api/datasources/3 \
  -X PUT -H "Content-Type: application/json" \
  -d '{
    "type":"loki",
    "url":"http://loki-read:3100",
    "basicAuth":true,
    "basicAuthUser":"USUARIO",
    "secureJsonData":{"basicAuthPassword":"SENHA"}
  }'
```

**Esforço estimado:** 2–3 horas (debug + validação + documentação)

#### **Opção B: Workaround (Curto prazo)**

Se Option A não for viável neste ciclo:
- Queries via Grafana proxy (já disponível internamente)
- SSH tunnel para acesso interno a loki-read:3100
- Documentar em runbook

**Esforço estimado:** 30 minutos

#### **Opção C: Postergar**

Documentar como **P1 operacional** para próximo ciclo. ANA-001 não é bloqueado.

### 1.6 Responsabilidade & Coordenação

| Role | Responsabilidade |
|------|-------------------|
| **python-dev** (este projeto) | Validar impacto em scripts de análise; testar workaround |
| **docker-expert** | Verificar auth middleware no Traefik; extrair/validar credenciais Loki |
| **prometheus** | Confirmar que datasource Loki no Grafana tem credenciais corretas |
| **infra/ops** | Deploy de fix se necessário (reload Traefik/Loki) |

### 1.7 Pode ser resolvida localmente?

**Não.** Requer acesso ao wfdb01 (host remoto) e conhecimento de:
- Docker Secrets e Traefik labels
- Configuração de middleware de auth no enterprise-observability
- Aktualizacao de datasources no Grafana

**Coordenação necessária:** docker-expert + prometheus

---

## 2. BLOCKER P2: RECORDING RULES N8N NÃO FOI SUBMETIDO

### 2.1 Status Atual

| Item | Status |
|------|--------|
| Recording rules criadas? | ✅ Sim (arquivo: `reports/PROMETHEUS_RECORDING_RULES_N8N_2026-03-18.md`) |
| Validadas sintaticamente? | ✅ Sim (YAML válido, PromQL compilável) |
| Testadas em staging? | ❌ Não |
| Submetidas ao enterprise-observability-dashboards? | ❌ Não |
| Impacto de NÃO submeter? | ⚠️ Conhecido & documentado |

### 2.2 Impacto no Stack Observability (wfdb01)

#### **Sem Recording Rules:**

```
┌─────────────────────────────────────────────────────────────┐
│ Query Grafana Remota: topk(10, histogram_quantile(0.95, ...))│
│ ↓                                                             │
│ Prometheus HTTP API                                          │
│ ↓                                                             │
│ [Computar quantis em tempo real]                             │
│ [30+ dias de dados de histograma]                            │
│ [Overhead: ~1-2s] ← A query pode timeout (> 60s)            │
│ ↓ RESULTADO                                                   │
│ ❌ Timeout ou sucesso lento                                  │
└─────────────────────────────────────────────────────────────┘
```

#### **Com Recording Rules (após deploy):**

```
┌─────────────────────────────────────────────────────────────┐
│ Query Grafana Remota: topk(10, n8n:workflow_p95_latency:...) │
│ ↓                                                             │
│ Prometheus HTTP API                                          │
│ ↓                                                             │
│ [Buscar série pré-computada em wfdb01]                       │
│ [Overhead: ~ 100-200ms] ← Sub-segundo                        │
│ ↓ RESULTADO                                                   │
│ ✅ Instantâneo                                                │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Impacto na Coleta de Logs/Métricas N8N

#### **Métricas N8N (severidade: MÉDIA-ALTA)**

- **Coleta base:** ✅ Funciona (exporter em wf001 emite métricas)
- **Armazenamento:** ✅ Funciona (Prometheus scrape → VictoriaMetrics storage)
- **Consulta de quantis:** ⚠️ **LENTO sem recording rules**

**Consequências práticas:**
1. Dashboards Grafana N8N podem **timeout** ou render **vazio**
2. Alertas baseados em P95/P99 **NÃO existem** ou são **muito caros computacionalmente**
3. Análises ad-hoc que usam `histogram_quantile()` **são lentas** (depende de onde executam)

#### **Análise ANA-001 (severidade: BAIXA)**

- ANA-001 foi executado **diretamente em wfdb01** (aceso interno a Victoria Metrics)
- Recording rules **não eram necessárias** para o sucesso de ANA-001

**Conclusão:** Recording rules são **uma melhoria** para futuras análises remotas, não uma dependência do ANA-001 que já terminou.

### 2.4 Urgência Técnica

| Critério | Avaliação |
|----------|-----------|
| ANA-001 pode encerrar sem isto? | ✅ **Sim** (ANA-001 executou no wfdb01 direto) |
| Melhora operacional? | ✅ **Sim** (dashboards + alertas remotos mais rápidos) |
| Bloqueia escalação? | ⚠️ **Sim** (próximas análises podem ter timeout remoto) |
| Afeta decisão técnica? | ❌ **Não** (conclusões já foram tiradas) |
| Impacto em produção N8N? | ❌ **Não** (apenas observability) |

**Ranking de urgência ANA-001:** 🟡 P2 **NÃO BLOCKER**, mas **boa prática** para operações futuras.

### 2.5 Estratégia de Resolução

#### **Opção A: Submit Corretamente (Recomendado)**

Requer coordenação com **prometheus** (gerencia rules do Prometheus) e **docker-expert** (deploy via docker-compose).

```bash
# Passo 1: SCP o arquivo de rules para wfdb01
fwknop --rc-file ~/.fwknoprc -n wfdb01 && sleep 3 && scp -P 5010 \
  reports/PROMETHEUS_RECORDING_RULES_N8N_2026-03-18.md \
  archaris@wfdb01.vya.digital:/tmp/n8n_rules_proposal.md

# Passo 2: No wfdb01, criar o arquivo YAML das rules
ssh -p 5010 archaris@wfdb01.vya.digital << 'EOF'
# Extrair bloco YAML (entre ```yaml e ```)
cat > /opt/docker_user/enterprise-observability/prometheus/rules/n8n_performance.yaml << 'RULES'
[CONTEÚDO DO BLOCO YAML DO ARQUIVO .md]
RULES
# Verificar sintaxe
docker exec enterprise-prometheus promtool check rules \
  /etc/prometheus/rules/n8n_performance.yaml
EOF

# Passo 3: Fazer reload zero-downtime
ssh -p 5010 archaris@wfdb01.vya.digital << 'EOF'
curl -s -X POST http://localhost:9090/-/reload
sleep 5
# Validar que rules foram carregadas
curl -s http://localhost:9090/api/v1/rules | grep -i "n8n_workflow_p95"
EOF

# Passo 4: Testar no Grafana
# → Abrir Grafana Explorer (datasource: Prometheus)
# → Query: n8n:workflow_p95_latency:rate10m
# → Deve retornar série em < 500ms
```

**Esforço estimado:** 1–2 horas (SCP + aplicação + validação + documentação)

#### **Opção B: Validação em Staging Primeiro**

Se houver ambiente de staging para Prometheus:
1. Deploy rules em staging
2. Testar queries por 24h
3. Validar que métricas estão sendo computadas
4. Deploy em produção

**Esforço estimado:** 4–6 horas (+ tempo de espera)

#### **Opção C: Postergar para Próximo Ciclo**

Documentar como **P2 técnico** para:
- Próxima análise remota (se necessária)
- Otimização de dashboards N8N no Grafana

### 2.6 Responsabilidade & Coordenação

| Role | Responsabilidade |
|------|-------------------|
| **python-dev** (este projeto) | Preparar arquivo YAML; documentar no enterprise-observability-dashboards |
| **prometheus** | Revisar PromQL; validar que métricas expostas são corretas |
| **docker-expert** | Deploy das rules via docker-compose (SCP + reload); verificar que `n8n_workflow_execution_duration_seconds_bucket` está sendo scraped |
| **infra/ops** | Monitorar stress CPU do Prometheus após deploy (rules adicionam carga) |

### 2.7 Pode ser resolvida localmente?

**Parcialmente.**
- Preparação do arquivo YAML: ✅ Pode fazer aqui
- SCP para wfdb01: ✅ Pode fazer (precisa SPA)
- Validation no wfdb01: ✅ Pode fazer (precisa SSH)
- Deploy efetivo (reload Prometheus): ⚠️ **Requer coordenação** com docker-expert

---

## 3. ANÁLISE COMPARATIVA: P1 vs P2

| Aspecto | P1 (Loki 401) | P2 (Recording Rules) |
|--------|--------------|-------------------|
| **Blocker de ANA-001?** | ❌ Não | ❌ Não |
| **Afeta coleta N8N?** | 🟡 Logs remotos | 🟡 Queries remotas |
| **Afeta operações?** | ✅ Sim (troubleshooting) | ✅ Sim (performance dashboards) |
| **Pode fazer localmente?** | ❌ Não | 🟡 Parcialmente |
| **Urgência técnica** | 🔴 P1 (operacional) | 🟡 P2 (otimização) |
| **Complexidade** | Média (debug + auth) | Baixa (aplicação + validação) |
| **Tempo estimado** | 2–3h | 1–2h |
| **Coordenação necessária?** | ✅ docker-expert + prometheus | ✅ prometheus + docker-expert |
| **Risco de regressão?** | Baixo (auth fix) | Baixo (rules adicionadas) |
| **Prioridade recomendada** | 2ª (debug pode levar tempo) | 1ª (simples e rápido) |

---

## 4. ORDEM DE EXECUÇÃO RECOMENDADA

### **Ciclo 1: Submeter Recording Rules (P2)**

**Por quê?** Implementação simples, validação rápida, melhora imediata de observability.

```
Timeline:
- T+0h00: Preparar arquivo YAML em formao pronto para deploy
- T+0h30: Enviar para prometheus + docker-expert para revisão
- T+1h00: Deploy em wfdb01 (SCP + reload)
- T+1h30: Validação em Grafana (testar queries)
- T+2h00: Documentação de conclusão
```

**Bloqueadores:** Nenhum. Pode começar imediatamente após este debate.

### **Ciclo 2: Resolver Loki 401 (P1)**

**Por quê?** Requer debug em wfdb01, pode levar mais tempo, menos urgente operacionalmente.

```
Timeline:
- T+0h00: Iniciar debug com docker-expert (verificar auth middleware)
- T+2h00: Testar credenciais; validar acesso interno vs remoto
- T+3h00: Aplicar fix (se simples) ou documentar workaround (se complexo)
- T+3h30: Validação final
```

**Bloqueadores:** Disponibilidade de docker-expert para SSH ao wfdb01.

---

## 5. RECOMENDACIÓN FINAL PARA DEBATE

### **Proposta de Decisão:**

| Item | Recomendação | Rationale |
|------|--------------|-----------|
| **Executar P2 (Recording Rules)?** | ✅ **SIM** | ROI alto (1-2h), melhora permanente, sem risco |
| **Executar P1 (Loki 401)?** | 🟡 **Condicional** | Se docker-expert tem tempo; senão, postergar para próximo ciclo |
| **Bloqueia encerramento ANA-001?** | ❌ **Não** | Ambas são operacionais, não técnicas |
| **Prioridade de debate?** | P2 > P1 | P2 é "quick win"; P1 é "infrastructure debt" |

### **Ações Imediatas Propostas:**

1. **[python-dev]** Preparar arquivo YAML final de recording rules (30 min)
2. **[prometheus]** Revisar PromQL + labels das rules (15 min)
3. **[docker-expert]** Agendarar slot de 1h para deployment em wfdb01
4. **[all]** Agendar debug de Loki 401 para próxima semana

---

## 6. Apêndice: Artefatos de Suporte

### A. Arquivo de Recording Rules (pronto para deploy)

Localização: `reports/PROMETHEUS_RECORDING_RULES_N8N_2026-03-18.md`

**Contenha:**
- 7 recording rules (P50, P95, P99, taxa execução, taxa falha, global P95, max 99.9)
- Interval: 5m (balance entre granularidade e CPU)
- Labels: quantile, aggregation, scope (para contexto em alertas)
- Impacto esperado: ~5MB/mês em armazenamento; ~2-5% CPU overhead no Prometheus

### B. Alertas Sugeridos (Inclusos no arquivo de rules)

**2 alertas recomendados para deploy paralelo:**
- `N8NWorkflowHighLatencyP95` (warning): P95 > 2s por 15 min
- `N8NWorkflowCriticalLatencyP99` (critical): P99 > 5s por 10 min

### C. Teste de Validação (Pós-Deploy)

```promql
# No Grafana Explore (datasource: Prometheus)
# Todas deve retornar valores (não NaN) em < 500ms

# 1. Série base existe?
n8n_workflow_execution_duration_seconds_bucket

# 2. Recording rule foi computado?
n8n:workflow_p95_latency:rate10m

# 3. Valores estão razoáveis (não infinito/NaN)?
n8n:workflow_p95_latency:rate10m > 0 and n8n:workflow_p95_latency:rate10m < 3600

# 4. Há dados para diferentes workflows?
topk(5, n8n:workflow_p95_latency:rate10m)
```

---

## 7. Encerramento

Esta análise consolida:
- ✅ Impacto técnico de cada blocker
- ✅ Urgência e priorização
- ✅ Estratégia de resolução com esforço estimado
- ✅ Responsabilidades e coordenação necessária
- ✅ Recomendação de ordem de execução

**Próximo passo:** Debate com python-dev, docker-expert e prometheus para confirmação de execução e alocação de tempo.

---

**Assinatura digital:** enterprise-python-analysis/ANA-001
**Preparado por:** Observability Agent (em `observability` mode)
**Data:** 2026-03-31 UTC
**Hash:** [commit sha — será informado após push]
