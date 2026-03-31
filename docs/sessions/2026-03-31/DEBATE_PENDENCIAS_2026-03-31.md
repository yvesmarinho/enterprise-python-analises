# DEBATE TÉCNICO: ANÁLISE DE PENDÊNCIAS HERDADAS
## Sessão de Remediação 2026-03-31

**Data**: 2026-03-31
**Referência**: FINAL_STATUS_2026-03-30.md
**Contexto**: Avaliação multilíngue de 5 pendências P1/P2/P3 + 2 tarefas em andamento + 4 itens backlog

---

## SEÇÃO 1: ANÁLISE POR PERSPECTIVA TÉCNICA

### Pendência: [P1] cAdvisor wf001 sem labels de container

#### 🐳 Perspectiva Docker/Infrastructure
**Severidade**: CRÍTICA para observability, média para análise
**Contexto**: cAdvisor coleta métricas de container (CPU, memória, I/O) mas sem labels, não consegue correlacionar com serviços N8N específicos.

**Impacto Operacional:**
- Métricas em wf001 aparecem como "container_id" genéricos
- Impossível filtrar por pod/container name em Prometheus queries
- Análise de performance de N8N degradada (não consegue isolar por workflow/execution)
- Visualizações em Grafana mostram dados mas sem contexto de serviço

**Dependência Externa:** `enterprise-observability` repo (fora deste workspace)
- Requer ajuste em cAdvisor daemonset YAML ou configuração de labels
- Possível issue: labels no cAdvisor precisam vir do kubelet/docker labels
- Se não é Kubernetes, pode ser Docker labels que precisam ser capturados

**Bloqueadora para análise?**: Parcialmente. Impede drill-down fino, mas grosso modo permiti análise por host.

---

#### 🔍 Perspectiva Python/Analysis
**Impacto no Pipeline ANA-001:**
- Scripts `wf001_fase1_pivotado.py` e `wf001_fase2_drilldown.py` usam host-level metrics, não container-level
- Gate de proveniência não depende de cAdvisor labels (usa Prometheus ingestion timestamps)
- Auditoria proveniência: não há correlação direta

**Recomendação:** P1 em urgência operacional, mas não bloqueadora IMEDIATA para análise de 31/03.

---

#### 📊 Perspectiva Observability/Grafana
**Impacto na Stack:**
- Dashboards N8N em `reports/Dashboards - Grafana.html` já estão configurados com queries que usariam labels
- Queries tipo `container_memory_usage_bytes{pod="n8n-workflow-*"}` falham ou retornam sem filtro
- Alertas de regressão (pendência backlog) não conseguem segmentar por container

**Bloqueia Alerta de Regressão?**: SIM. Alerta de regressão de instrumentação precisa correlacionar com labels de container.

---

### Pendência: [P1] Loki autenticação falhando (401)

#### 🔐 Perspectiva Observability/Logs
**Severidade**: CRÍTICA para visibilidade de logs, mas com fallback

**Contexto**: Loki em wfdb01 rejeitando requests (HTTP 401 Unauthorized).
Possibilidades:
1. Token expirado
2. Credencial incorreta configurada em Promtail/Vector
3. Loki RBAC habilitado mas permissões erradas
4. Certificado TLS ou mismatch de headers

**Impacto Imediato:**
- Logs de todos serviços (N8N, exporter, collector) não estão sendo ingeridos em Loki
- Grafana não consegue fazer buscas em Loki
- Troubleshooting visual de erros N8N impossível
- Alertas baseados em logs não funcionam

**Análise Afetada?**: Não diretamente. ANA-001 usa Prometheus (métricas), não Loki (logs). Mas troubleshooting de anomalias fica comprometido.

**Dependência Externa?**: Parcialmente. Credenciais podem estar em projeto de observability; requer SSH em wfdb01 para validação.

**Ordem de Resolução**: ANTES de submeter recording rules (P2) — se Loki tá quebrado, logs não vão funcionar.

---

#### 🏗️ Perspectiva DevOps/System Engineer
**Diagnóstico Requerido:**
```
1. SSH wfdb01, validar credencial Loki:
   - Verificar LOKI_AUTH_TOKEN em docker-compose/kubernetes
   - Testar curl -H "Authorization: Bearer $TOKEN" https://loki:3100/loki/api/v1/label

2. Validar Promtail/Vector config:
   - Verificar URL remota de Loki
   - Verificar token passado

3. Validar TLS/mTLS:
   - Se cert pinning ativo, certificado pode ter expirado
```

**Tempo Estimado de Resolução**: 30-45 min de investigação + 15 min de fix.

---

### Pendência: [P2] Gate de proveniência ANA-001

#### 🔑 Perspectiva Python/Analysis
**Severidade**: MÉDIA-ALTA para robustez da análise

**Contexto**: Pipeline ANA-001 extrai dados do Prometheus mas não valida se dados foram coletados por este serviço ou importados de outro lugar.

**O que é "Gate de Proveniência"?**
- Filtro nos dados de entrada que verifica: "estas métricas vieram do job N8N_ANALYZER ou de outra fonte?"
- Impede análise de dados "sujos" coletados de forma inconsistente
- Garante que relatório final tem garantia de qualidade

**Impacto Sem O Gate:**
- Resultados podem incluir anomalias artificiais (dados backdated, importados manualmente, etc.)
- Relatório perde credibilidade técnica
- Bloqueia submissão formal de findings

**Onde Implementar:**
```
arquivo: src/n8n_analyzer/analyzers/provenance.py (ou novo)
gatilho: no início de cada análise (main.py)
validação: verifica metadata de ingestion dos dados
```

**Dependência Externa?**: NÃO. Completamente resolvível neste repo.
**Requer Novo Código?**: SIM, módulo novo ou extensão de pipeline.
**Risco de Regressão?**: Baixo se implementado como pré-filtro.

---

#### 🔍 Perspectiva Observability/Prometheus
**Validação Técnica:**
- Prometheus labels `job`, `instance`, `__meta_*` registram proveniência
- Query: `SELECTORS{job="n8n_analyzer"}` retorna subset válido
- Rejeitar dados com `job != "n8n_analyzer"` implementável em PromQL

**Recomendação:** Implementar via PromQL selector + validação em Python.

---

### Pendência: [P2] Submeter recording rules N8N

#### 📏 Perspectiva Prometheus/Recording Rules
**Severidade**: MÉDIA-ALTA para performance e reutilização

**Contexto**: Recording rules pré-computam agregações (ex: "n8n:p95_latency:5m") para não computar em query time.

**Documentação Base:** `reports/PROMETHEUS_RECORDING_RULES_N8N_2026-03-18.md` (já existe!)

**Por que Submeter?**
- Regras precisam ser commitadas em `enterprise-observability` repo
- Serão carregadas no Prometheus da stack de produção
- Múltiplas análises futuras reutilizarão estas regras

**Dependência Externa?**: SIM. Requer PR para `enterprise-observability-dashboards`.

**Workflow de Submissão:**
1. ✅ Regras já estão documentadas em reports/
2. ⏳ Clonar `enterprise-observability-dashboards`
3. ⏳ Copiar rules para `prometheus/recording_rules/`
4. ⏳ Validar sintaxe: `promtool check rules`
5. ⏳ Submeter PR com descrição (linkando ANA-001)

**Pré-requisito:** Loki estar funcionando (P1) para que stack seja estável antes de adicionar regras complexas.

---

#### 🔍 Perspectiva DevOps/Observability
**Impacto na Stack:**
- Sem recording rules, Grafana queries rodam em tempo real (mais lento)
- Com rules, dashboards responsivos
- Regressão de performance se rules tiverem bugs → alerta (P2 backlog) detecta

**Ordem**: DEPOIS de validar Loki 401 e cAdvisor labels.

---

### Pendência: [P3] Auditoria de proveniência scripts wf001_*.py

#### 🔎 Perspectiva Python/Analysis
**Severidade**: BAIXA para operação atual, média para conformidade

**Contexto**: Scripts `wf001_fase1_pivotado.py` e `wf001_fase2_drilldown.py` executados manualmente.
Questão: "De qual host rodaram? Com qual versão de código? Com quais credenciais acessaram Prometheus?"

**Por que Importa?**
- Reprodutibilidade: próxima sessão precisa validar se resultados são consistentes
- Auditoria: garantir que dados de ANA-001 não têm viés de execução
- Compliance: registrar exatamente que ferramentas e versões foram usadas

**O que Auditar:**
```
☐ Hostname onde script rodou (echo $HOSTNAME)
☐ Python version (sys.version)
☐ Git commit sha256 de wf001_fase1_pivotado.py
☐ Prometheus target validado (pré-check antes de queries)
☐ Credenciais usadas (logged anonimizado)
☐ Timestamps de início/fim exato
```

**Onde Registrar:** Adicionar inline ao script ou em arquivo separado `scripts/.audit_log`

**Risco se Não Fizer:** Relatório perde cadeia de proveniência completa.

---

#### 🏗️ Perspectiva DevOps/Security
**Recomendação**: P3 é housekeeping, mas importante para padrões de auditoria enterprise.
Não bloqueadora para próximas análises, mas dever fazer antes de publicar relatório final.

---

### Tarefas em Andamento

#### Task 1: Aplicação do fix de instrumentação no exporter/collector

**Status**: ✋ BLOQUEADO por dependência externa
**Contexto**: Fix preparado em `reports/N8N_INSTRUMENTATION_ACTION_PLAN_2026-03-30.md` +`n8n_instrumentation_guard_rules_2026-03-30.yaml`

**O Que Precisa Acontecer:**
1. Deploy no repositório `enterprise-observability` (fora deste workspace)
2. Reload de Prometheus config
3. Verificar se métricas voltam ao comportamento esperado

**Bloqueador**: Acesso ao outro repo + permissão de deploy.
**Dependências Relacionadas**:
- cAdvisor labels (P1) — faz parte do mesmo deploy observability
- Loki 401 (P1) — mesmo stack
- Recording rules (P2) — pode rodar após fix estar deploiado

---

#### Task 2: Mapeamento de docker scopes para nomes de serviço no host wf001

**Status**: ✋ BLOQUEADO por cAdvisor labels (P1)
**Contexto**: Correlacionar container_id genérico com service name "n8n-workflow", "n8n-node", etc.

**Por que Requerido:**
- Permitir drill-down fino de performance por tipo de N8N service
- Fundamental para relatório final detalhado

**Bloqueador**: Sem cAdvisor labels, mapeamento é manual e frágil.
**Sequência**: Task 1 (infrastructure fix) → depois Task 2 (mapeamento).

---

### Backlog de Instrumentação N8N

#### Item 1: Corrigir `n8n_workflow_execution_duration_seconds_sum` para monotonic

**Status**: 🔄 Requer codigo novo no exporter
**Problema**: Métrica apareça com valores não-monotônicos (pode descer), violando SLO de prometheus histograms.

**Requer**: Acesso ao `enterprise-observability` repo, fix no collector code.

---

#### Item 2: Adicionar buckets finos de histograma para latências sub-100ms

**Status**: 🔄 Requer config no exporter
**Por que**: Atualmente histograma tem buckets: 0.001, 0.01, 0.1, 1, ... (muito grosseiro para sub-100ms).
Sugerido em relatório: adicionar buckets: 0.005, 0.05, 0.075, 0.09 para melhor resolução.

**Requer**: Config change no Prometheus scrape config ou no exporter.

---

#### Item 3: Revalidar p95 com variância após rollout do fix

**Status**: 🚀 Ação pós-deploy
**Sequência**: Depois que fix de Item 1 deploiar, re-rodar análise com `wf001_fase1_pivotado.py` e `wf001_fase2_drilldown.py`.

**Diferença Esperada**: p95 deve cair ou estabilizar (sem oscilações artificiais).

---

#### Item 4: Criar/ativar alerta de regressão de instrumentação

**Status**: 🔄 Requer Prometheus rule + notificação
**Regra Sugerida:**
```promql
# Detectar se métrica parou de ser monotônica
n8n_workflow_execution_duration_seconds_sum > ignoring(le)
  (shift(n8n_workflow_execution_duration_seconds_sum, 5m))
```

**Requer**: Deploy em Prometheus rules (enterprise-observability).
**Pré-requisito**: cAdvisor labels + Loki 401 resolvido (para contexto em alerta).

---

## SEÇÃO 2: MATRIZ DE DEPENDÊNCIAS E BLOQUEADORES

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      GRAFO DE DEPENDÊNCIAS                              │
└─────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────────┐
                    │  External Deploy         │
                    │  (enterprise-observ.)   │
                    └────────┬─────────────────┘
                             │
                ┌────────────┬──────────────┐
                │            │              │
         ┌──────▼────┐  ┌────▼──────┐  ┌───▼──────────┐
         │ cAdvisor   │  │ Loki 401  │  │ Exporter Fix │
         │ Labels P1  │  │  P1       │  │ (In Progress)│
         └────┬───────┘  └────┬──────┘  └───┬──────────┘
              │               │             │
         ┌────▼────┐      ┌────▼────┐   ┌──▼────────────┐
         │Docker    │      │Observ.  │   │  Bucket Fine  │
         │Mapping   │      │Stack OK │   │  Tuning       │
         │Task 2    │      │         │   │  (Backlog 2)  │
         └────┬─────┘      └─────────┘   └──┬────────────┘
              │                              │
              └──────────────┬───────────────┘
                             │
                    ┌────────▼──────┐
                    │ p95 Revalidar │
                    │ (Backlog 3)   │
                    └-------────────┘
```

**Legenda:**
- P1 = Bloqueadora CRÍTICA para análise de 31/03
- P2 = Importante para conformidade/performance, não bloqueadora imediata
- P3 = Housekeeping, não bloqueadora
- Task = Tarefa em andamento, bloqueada por externa

---

## SEÇÃO 3: CONTEXTO DOS BLOQUEADORES HERDADOS

### Bloqueador 1: Dependência Externa - Código Exporter/Collector

**Está em**: `../enterprise-observability/` (fora deste repo)
**O que afeta**:
- Task In Progress #1 (instrumentação fix applicado)
- cAdvisor labels P1
- Loki auth P1 (possível)
- Bucket tuning, alerta, validação

**Como Desbloquear**:
1. ✉️ Notificar equipe de observability em `enterprise-observability`
2. 🔍 Validar PRs pendentes ou criar nova issue
3. ⏳ Aguardar merge + deploy
4. ✅ Re-ativar análise após deploy (Backlog 3)

**Comunicação Sugerida**:
```markdown
## Issue: N8N Instrumentation Fix Deployment + Label Propagation

**Artefatos Prontos**:
- reports/N8N_INSTRUMENTATION_ACTION_PLAN_2026-03-30.md
- reports/N8N_INSTRUMENTATION_VALIDATION_2026-03-30.json
- n8n_instrumentation_guard_rules_2026-03-30.yaml

**Requerido para wfdb01**:
1. Deploy exporter fix (monotonic validation)
2. Propagate cAdvisor labels para Prometheus
3. Validar Loki auth token (401 debug)
4. Adicionar histogram buckets finos
```

---

### Bloqueador 2: Dependência Operacional - Deploy e Reload Stack

**Está em**: wfdb01 (infrastructure controlled)
**O que afeta**:
- Todas mudanças observability stack

**Dono**: DevOps/SRE team (provavelmente)

**Como Desbloquear**:
- Coordenar com SRE para janelaFeaturedMaintenance
- Validar que Prometheus + Grafana + Loki todos estão OK pós-deploy
- Testar antes em stage se disponível

---

## SEÇÃO 4: RECOMENDAÇÕES CONSOLIDADAS

### Árvore de Priorização para 2026-03-31

```
🎯 OBJETIVO: Gerar debate de dependências e listar tarefas

┌─ FASE 1: Validation (2h, não bloqueada externamente)
│  ├─ Auditoria scripts (P3) ← FAZER HOJE
│  └─ Gate proveniência ANA-001 (P2) ← START TODAY
│
├─ FASE 2: Investigation (1.5h, requer diagnóstico)
│  ├─ Loki 401 SSH validation (P1)
│  ├─ Relatório de estado atual
│  └─ Ação corretiva local
│
├─ FASE 3: Documentação + Submissão (1h)
│  ├─ Submeter recording rules PR (P2)
│  └─ Documentar findings de investigação
│
└─ FASE 4: Aguardando (async, bloqueada externamente)
   ├─ Task 1: Exporter fix deployment
   ├─ Task 2: Docker mapping (após Task 1)
   └─ Backlog 3: p95 revalidation (após Task 1)
```

### Recomendação de Sequência

**HOJE (2026-03-31, DENTRO deste repo - não bloqueado):**
1. ✅ Implementar **Gate de Proveniência** (P2) — Python code
2. ✅ Auditar **proveniência scripts** (P3) — Documentation
3. ⚙️ Investigar **Loki 401** (P1) — SSH diagnostic
4. 📊 Preparar **Recording Rules PR** (P2) — Review readiness

**BLOCKED EXTERNALLY (aguardando enterprise-observability):**
1. ⏳ Exporter fix deployment (In Progress Task 1)
2. ⏳ cAdvisor labels (P1)
3. ⏳ Bucket tuning (Backlog 2)

---

## SEÇÃO 5: LISTA DE TAREFAS PARA RESOLVER PENDÊNCIAS

### Formato: [STATUS] ID | TAREFA | PRIORIDADE | REQUISITOS | OWNER | EST. TEMPO

---

### ✅ TAREFAS IMEDIATAS (Não bloqueadas, fazer hoje)

#### TASK-001 | Implementar Gate de Proveniência ANA-001
- **Prioridade**: P2 (importante para conformidade)
- **Descrição**: Criar filtro que valida se dados vieram de job="n8n_analyzer"
- **Requisitos**: Conhecimento Python, PromQL, Pydantic
- **Arquivo Alvo**: `src/n8n_analyzer/analyzers/provenance.py` (novo ou estendido)
- **Critério de Conclusão**:
  - [ ] Módulo cria gate com seletores PromQL válidos
  - [ ] Gate rejeiteitems com job != "n8n_analyzer"
  - [ ] Teste unitário passa
  - [ ] Integrado em pipeline principal (main.py)
  - [ ] Documentação atualizada em README
- **Owner Sugerido**: python-dev
- **Tempo Estimado**: 1-1.5h
- **Bloqueadores**: Nenhum
- **Dependências Posteriores**: Gate de proveniência deve estar OK antes de revalidar p95 (Backlog 3)

---

#### TASK-002 | Auditar Proveniência de Scripts wf001_fase*.py
- **Prioridade**: P3 (housekeeping)
- **Descrição**: Criar audit trail para scripts executados (hostname, git commit, Python version, timestamps)
- **Requisitos**: Conhecimento shell/Python, git
- **Arquivo Alvo**:
  - `scripts/wf001_fase1_pivotado.py` (adicionar logging de context)
  - `scripts/wf001_fase2_drilldown.py` (adicionar logging de context)
  - `scripts/.audit_log` (novo arquivo com histórico)
- **Critério de Conclusão**:
  - [ ] Scripts loggam: hostname, git SHA, Python version, start/end timestamps
  - [ ] Arquivo .audit_log criado com entradas anteriores (pós-factum se necessário)
  - [ ] Próxima execução cria entrada em .audit_log automaticamente
  - [ ] Formatomj de log é estruturado (JSON ou CSV)
- **Owner Sugerido**: python-dev
- **Tempo Estimado**: 45 min
- **Bloqueadores**: Nenhum
- **Dependências Posteriores**: Nenhuma imediata

---

#### TASK-003 | Investigar Loki 401 - Diagnóstico Técnico
- **Prioridade**: P1 (crítico para observability, não bloqueador IMEDIATO para ANA-001)
- **Descrição**: SSH em wfdb01, diagnosticar por que Loki retorna 401 Unauthorized
- **Requisitos**: Acesso SSH wfdb01, conhecimento Loki/auth
- **Passos**:
  1. SSH wfdb01
  2. Validar token/credencial em docker-compose ou k8s config
  3. Executar `curl -v -H "Authorization: Bearer $LOKI_TOKEN" https://loki:3100/api/v1/label`
  4. Se falha, validar TLS cert + issuer
  5. Documentar achados
- **Critério de Conclusão**:
  - [ ] Documento `docs/sessions/2026-03-31/LOKI_401_DIAGNOSTIC_2026-03-31.md` criado
  - [ ] Causa raiz identificada (token expirado, cert, RBAC, etc)
  - [ ] Ação corretiva recomendada
  - [ ] Se for quick fix local, executada
- **Owner Sugerido**: System Engineer ou DevOps
- **Tempo Estimado**: 1-1.5h
- **Bloqueadores**: Acesso SSH wfdb01
- **Comentário**: Se for complexo, pode ser escalado como issue para observability team após diagnostic

---

#### TASK-004 | Review Recording Rules para Submissão PR
- **Prioridade**: P2 (importante para performance stack)
- **Descrição**: Validar e preparar artefato `reports/PROMETHEUS_RECORDING_RULES_N8N_2026-03-18.md` para PR em enterprise-observability
- **Requisitos**: Conhecimento Prometheus, PromQL, git flow
- **Passos**:
  1. Ler `reports/PROMETHEUS_RECORDING_RULES_N8N_2026-03-18.md`
  2. Validar sintaxe de rules com `promtool check rules`
  3. Documentar contexto de cada rule (por que existe, que métrica depende)
  4. Preparar commit message + PR description
  5. Clonar `enterprise-observability-dashboards` (se necessário para PR)
- **Critério de Conclusão**:
  - [ ] Rules validadas com promtool
  - [ ] Documentação de contexto clara
  - [ ] PR pronta para submissão (não ainda submetida, apenas preparada)
  - [ ] Linkado a ANA-001 analysis
- **Owner Sugerido**: ObservabilitySpecialist (pode ser current session ou preparação)
- **Tempo Estimado**: 1h
- **Bloqueadores**: Nenhum
- **Nota**: PR só é submetida APÓS Loki 401 resolver (P1 antes de P2)

---

### ⏳ TAREFAS BLOQUEADAS EXTERNAMENTE (Dependem enterprise-observability)

#### TASK-EXT-001 | [EXTERNAL] Deploy N8N Instrumentation Fix
- **Prioridade**: P1 (crítico, desbloqueador de várias outras)
- **Status**: Em Andamento (desde 2026-03-30)
- **Descrição**: Aplicar fix em `enterprise-observability` exporter code para monotonic metric validation
- **Arquivo Responsável**: `enterprise-observability/src/exporter/n8n_collector.py` (ou similar)
- **Owner**: observability team (fora deste repo)
- **Depends On**: Nenhum
- **Blocks**:
  - Task In Progress #2 (Docker mapping)
  - Backlog Item 3 (p95 revalidation)
  - Backlog Item 4 (alerta regressão)
- **Artefatos Presentes Neste Repo**:
  - reports/N8N_INSTRUMENTATION_ACTION_PLAN_2026-03-30.md
  - reports/N8N_INSTRUMENTATION_VALIDATION_2026-03-30.json
  - n8n_instrumentation_guard_rules_2026-03-30.yaml
- **Ação Requerida**: Comunicar a observability team com PRs/issues + link a artefatos acima

---

#### TASK-EXT-002 | [EXTERNAL] Propagate cAdvisor Labels para Prometheus
- **Prioridade**: P1 (crítico para observability)
- **Status**: Planejada (não iniciada)
- **Descrição**: Configurar cAdvisor em wf001 para expor container labels como Prometheus labels
- **Bloqueado por**: TASK-EXT-001 (pode ser feito em paralelo, mas mesmo deploy window)
- **Requisitos**: Acesso a cAdvisor daemonset config (k8s) ou docker labels config (docker)
- **Ação**: Comunicar com DevOps/observability team
- **Critério de Conclusão**:
  - [ ] cAdvisor query em Prometheus retorna labels tipo `container_name="n8n-workflow"`
  - [ ] Queries em Grafana conseguem filtrar por label
  - [ ] Docker mapping (Task In Progress #2) pode ser executada

---

### ⏸️ BACKLOG DE INSTRUMENTAÇÃO (Tarefas futuras, bloqueadas por TASK-EXT-001)

#### BACKLOG-001 | Adicionar Histogram Buckets Finos sub-100ms
- **Prioridade**: P2 (melhoria de resolução)
- **Está em Backlog**: Sim, será feito APÓS fix inicial deploy
- **Descrição**: Configurar Prometheus scrape config para adicionar buckets: 0.005s, 0.05s, 0.075s, 0.09s
- **Owner**: prometheus team (observability)
- **Tempo**: ~30 min (config change)

---

#### BACKLOG-002 | Revalidar p95 Após Deploy do Fix
- **Prioridade**: P1 (crítico para validação de ANA-001)
- **Está em Backlog**: Sim, será feito DEPOIS que fix deploiar
- **Descrição**:
  - Re-executar `scripts/wf001_fase1_pivotado.py`
  - Re-executar `scripts/wf001_fase2_drilldown.py`
  - Comparar p95 valores com relatório anterior
  - Validar que métrica agora é monotônica
- **Requisitos**: Gate de Proveniência implementado (TASK-001)
- **Critério de Conclusão**:
  - [ ] Novo relatório `reports/n8n_perf_ANA001_REVALIDATION_2026-03-31.md` criado
  - [ ] Comparação lado-a-lado com análise anterior
  - [ ] Monotonicity validated (sem oscilações artificiais)
  - [ ] Conclusão: "ANA-001 revalidado com sucesso" ou "Anomalia encontrada"
- **Owner**: python-dev (análise, scripts)
- **Tempo Estimado**: 1.5-2h (scripts + comparação + documentação)

---

#### BACKLOG-003 | Criar Alerta de Regressão de Instrumentação
- **Prioridade**: P2 (importante para operação futura)
- **Está em Backlog**: Sim, DEPOIS que fix + buckets estiverem ok
- **Descrição**: Criar Prometheus alert_rule que detecta se métrica parou de ser monotônica
- **Pseudocódigo PromQL**:
  ```
  alert: N8NMetricNonMonotonic
  expr: |
    increase(n8n_workflow_execution_duration_seconds_sum[5m]) < 0
  for: 1m
  severity: critical
  ```
- **Owner**: prometheus team (observability)
- **Tempo**: ~45 min

---

## RESUMO EXECUTIVO FINAL

### Pendências P1 (Críticas para 31/03)

| Tarefa | Bloqueador? | Ação Hoje | Responsável |
|--------|-----------|----------|-------------|
| Loki 401 | Não ANA-001, SIM observability | TASK-003: Diagnóstico | DevOps/current session |
| cAdvisor labels | Não ANA-001, SIM observability | TASK-EXT-002: Comunicar | observability team |

### Pendências P2 (Importantes, não bloqueadores imediatos)

| Tarefa | Bloqueador? | Ação Hoje | Responsável |
|--------|-----------|----------|-------------|
| Gate proveniência | Não hoje, SIM para revalidação | TASK-001: Implementar | python-dev |
| Recording rules | Não hoje, SIM para conformidade | TASK-004: Preparar PR | observability specialist |

### Pendências P3 (Housekeeping)

| Tarefa | Bloqueador? | Ação Hoje | Responsável |
|--------|-----------|----------|-------------|
| Auditoria scripts | Não | TASK-002: Implementar | python-dev |

### Tarefas Em Andamento (Bloqueadas Externamente)

| Task | Bloqueadora Para | Ação | Owner |
|------|-----------------|------|-------|
| Exporter fix | Backlog 2, Backlog 3 | TASK-EXT-001: Comunicar | observability team |
| Docker mapping | Análise fine-grained | Aguarda fix | python-dev (pós-deploy) |

---

**Documento Gerado**: 2026-03-31 12:30 UTC
**Debate Consolidado**: Múltiplas perspectivas técnicas integradas
**Próximo Passo**: Executar TASK-001 até TASK-004 hoje, comunicar TASK-EXT-001 e TASK-EXT-002 para equipes de observability
