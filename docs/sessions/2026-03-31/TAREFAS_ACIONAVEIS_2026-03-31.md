# LISTA DE TAREFAS PARA RESOLVER PENDÊNCIAS HERDADAS
## Sessão 2026-03-31 | Ação Diária

**Gerado**: 2026-03-31 12:30 UTC
**Base**: FINAL_STATUS_2026-03-30.md + DEBATE_PENDENCIAS_2026-03-31.md
**Escopo**: Tarefas acionáveis NUM DIA (não bloqueadas externamente)

---

## 🎯 QUADRO DE CONTROLE RÁPIDO

```
┌─────────────────────────────────────┐
│ TAREFAS DE HOJE (2026-03-31)        │
├─────────────────────────────────────┤
│ 🔧 IMPLEMENTAR  (2 tarefas)         │
│    • Gate Proveniência ANA-001      │
│    • Auditoria Scripts Proveniência │
│                                     │
│ 🔍 INVESTIGAR  (1 tarefa)           │
│    • Loki 401 SSH Diagnostic        │
│                                     │
│ 📋 PREPARAR    (1 tarefa)           │
│    • Recording Rules PR             │
│                                     │
│ 📤 COMUNICAR   (2 bloqueadores)     │
│    • Exporter Fix Deploy            │
│    • cAdvisor Labels Propagate      │
└─────────────────────────────────────┘
```

---

## ✅ TAREFAS IMPLEMENTAR (Não bloqueadas)

### TASK-001: Gate de Proveniência ANA-001 🔑
**Status**: ⏹️ NÃO INICIADA
**Prioridade**: 🟡 P2 (Importante para conformidade)
**Tempo Estimado**: 1-1.5h
**Owner**: python-dev (você pode fazer ou delegar)

#### O que é?
Validar que dados de entrada foram coletados por `job="n8n_analyzer"`. Impede análise de dados "importados" ou de origem desconhecida.

#### Onde fazer?
Arquivo novo ou estendido: `src/n8n_analyzer/analyzers/provenance.py`

#### Critério de Conclusão
- [ ] Módulo Python criado com gate via PromQL selector
- [ ] Rejeita dados com `job != "n8n_analyzer"`
- [ ] Teste unitário passa: `pytest tests/analyzers/test_provenance.py`
- [ ] Integrado em `src/n8n_analyzer/main.py` (chamado no início de pipeline)
- [ ] Documentação em `src/n8n_analyzer/analyzers/README.md` atualiza
- [ ] Log de controle mostra gate foi aplicado

#### Exemplo de Implementação
```python
# src/n8n_analyzer/analyzers/provenance.py

from prometheus_api_client import PrometheusConnect

def validate_data_provenance(prom_client, job_name="n8n_analyzer"):
    """Gate de proveniência: valida job da origem dos dados."""

    # Query: contar séries por job
    query = f'count(up{{job="{job_name}"}})'
    result = prom_client.custom_query(query)

    if not result or result[0]['value'][1] == '0':
        raise ValueError(
            f"Nenhuma série encontrada com job={job_name}. "
            f"Dados podem estar contaminados."
        )

    print(f"✅ Provenance gate OK: job={job_name} presente")
    return True
```

#### Requisitos Técnicos
- Acesso à classe `PrometheusConnect` (já existe em projeto)
- Compreensão de PromQL selectors
- Teste unitário básico

---

### TASK-002: Auditoria Proveniência Scripts wf001_*.py 📜
**Status**: ⏹️ NÃO INICIADA
**Prioridade**: 🔵 P3 (Housekeeping, não bloqueador)
**Tempo Estimado**: 45 min
**Owner**: python-dev

#### O que é?
Registrar contexto técnico de execução dos scripts (hostname, git commit, Python version, timestamps). Garante reprodutibilidade e rastreabilidade.

#### Onde fazer?
1. `scripts/wf001_fase1_pivotado.py` → adicionar logging
2. `scripts/wf001_fase2_drilldown.py` → adicionar logging
3. `scripts/.audit_log` → novo arquivo com histórico

#### Critério de Conclusão
- [ ] Scripts loggam no início: hostname, git SHA, Python version, start time
- [ ] Scripts loggam no final: end time, status (OK/ERRO)
- [ ] Arquivo `scripts/.audit_log` criado com formato estruturado (JSON lines)
- [ ] Próxima execução adiciona linha automáticamente
- [ ] Exemplo de saída:
  ```json
  {"timestamp":"2026-03-31T12:00:00Z","script":"wf001_fase1_pivotado.py","hostname":"local-machine","git_sha":"5b71ab7","python":"3.11.8","status":"OK","exec_time_sec":120}
  ```

#### Implementação Rápida
```python
# No início de cada script
import json
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def log_execution_context():
    """Log execution context para auditoria."""
    audit_log_path = Path(__file__).parent / ".audit_log"

    hostname = socket.gethostname()
    git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    python_version = sys.version.split()[0]
    script_name = Path(__file__).name

    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "script": script_name,
        "hostname": hostname,
        "git_sha": git_sha,
        "python": python_version,
        "status": "started"
    }

    # Log
    with open(audit_log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return git_sha, hostname

# No final do script
try:
    main()
    log_execution_context()  # Sobrescreve com status=OK
except Exception as e:
    log_execution_context()  # Sobrescreve com status=ERROR
    raise
```

---

### TASK-003: Investigar Loki 401 - Diagnóstico 🔐
**Status**: ⏹️ NÃO INICIADA
**Prioridade**: 🔴 P1 (Crítico para observability, não bloqueia ANA-001 imediato)
**Tempo Estimado**: 1-1.5h
**Owner**: DevOps/System Engineer (você ou delegado)

#### O que é?
Diagnosticar por que Loki retorna HTTP 401 Unauthorized nas requisições. Bloqueia coleta de logs em wfdb01.

#### Pré-requisitos
- Acesso SSH a wfdb01
- Conhecimento básico de Docker/Kubernetes
- Curl instalado

#### Passos de Diagnóstico
```bash
# Step 1: SSH wfdb01
ssh user@wfdb01

# Step 2: Validar Loki está rodando
docker ps | grep loki
# ou
kubectl get pods -n observability | grep loki

# Step 3: Validar token configurado
docker inspect enterprise-loki | grep -i auth
# ou
kubectl get secret -n observability loki | grep token

# Step 4: Testar conexão (sem auth)
curl -v http://localhost:3100/loki/api/v1/label

# Step 5: Testar com token
LOKI_TOKEN=$(docker exec enterprise-loki printenv | grep LOKI_TOKEN | cut -d= -f2)
curl -v -H "Authorization: Bearer $LOKI_TOKEN" http://localhost:3100/loki/api/v1/label

# Step 6: Se TLS, testar com cert
curl -v --cacert /etc/ssl/certs/ca-certificates.crt \
  -H "Authorization: Bearer $LOKI_TOKEN" \
  https://loki.local:3100/loki/api/v1/label

# Step 7: Verificar logs do Loki
docker logs enterprise-loki | grep -i auth
# ou
kubectl logs -n observability deployment/loki | grep -i auth
```

#### Critério de Conclusão
- [ ] Documento criado: `docs/sessions/2026-03-31/LOKI_401_DIAGNOSTIC_2026-03-31.md`
- [ ] Causa raiz identificada (token expirado? cert? RBAC? endpoint?))
- [ ] Ação corretiva recomendada
- [ ] Se quick fix (<15 min), executada
- [ ] Se complexo, issue criada para observability team com evidence
- [ ] Document linkado em TODAY_ACTIVITIES_2026-03-31.md

#### Template de Saída
```markdown
## Loki 401 Diagnostic Report - 2026-03-31

**Achado 1**: Token LOKI_AUTH expirou em 2026-03-25
**Ação**: Renovar em [local] ou replicar credencial
**Status**: [OK / PENDENTE ESCALATION]

**Achado 2**: TLS cert mismatched
**Ação**: ...
**Status**: [...]
```

---

### TASK-004: Preparar Recording Rules PR 📊
**Status**: ⏹️ NÃO INICIADA
**Prioridade**: 🟡 P2 (Importante para performance, não urgente hoje)
**Tempo Estimado**: 1h
**Owner**: Observability Specialist ou python-dev

#### O que é?
Validar e preparar `reports/PROMETHEUS_RECORDING_RULES_N8N_2026-03-18.md` para submissão como PR em `enterprise-observability-dashboards` repo.

#### Por que agora?
1. Artefato já existe pronto
2. Pode ser feito em paralelo
3. Prerequisite: Loki estar funcionando (não necessário para esta tarefa, mas recomendado)
4. PR não será submetida HOJE, apenas preparada

#### Critério de Conclusão
- [ ] Arquivo `reports/PROMETHEUS_RECORDING_RULES_N8N_2026-03-18.md` lido e validado
- [ ] Sintaxe das rules testada: `promtool check rules rules.yaml`
- [ ] Cada rule tem comentário explicando seu propósito
- [ ] Arquivo README.md preparado com:
  - [ ] Data de origem (ANA-001 analysis, 2026-03-18)
  - [ ] Contexto (por que estas rules?)
  - [ ] Como testar
  - [ ] Link para issue/PR em enterprise-python-analysis
- [ ] Arquivo `docs/sessions/2026-03-31/RECORDING_RULES_PR_READY_2026-03-31.md` criado com:
  - [ ] Linkto das rules
  - [ ] Status "PRONTO PARA SUBMISSÃO"
  - [ ] Instruções de como submeter PR

#### Validação Syntax
```bash
# Copiar regras em arquivo temp
cat reports/PROMETHEUS_RECORDING_RULES_N8N_2026-03-18.md | grep -A 100 "^groups:" > /tmp/rules.yaml

# Validar
promtool check rules /tmp/rules.yaml
# Esperado: "SUCCESS"

# Contar quantas rules
grep "^  - record:" /tmp/rules.yaml | wc -l
# Esperado: ~10-15 rules
```

#### Next Step (NÃO fazer heute, apenas preparar)
Depois de Loki estar OK, submeter PR em `enterprise-observability-dashboards` com:
```
Title: Add N8N recording rules from ANA-001 analysis
Body:
- Rules ajudam Prometheus a pre-compute N8N aggregations
- Reduz carga de query em dashboards
- Source: reports/PROMETHEUS_RECORDING_RULES_N8N_2026-03-18.md
- Analysis: enterprise-python-analysis#ANA001
```

---

## 🔍 INVESTIGAÇÕES REQUERIDAS (1 tarefa)

Resumido acima em TASK-003.

---

## 📤 COMUNICAÇÕES NECESSÁRIAS (Bloqueadores Externos)

### COMUNICADO-001: Exporter Fix Deployment
**Para**: observability team / `enterprise-observability` maintainers
**Urgência**: 🔴 HOJE (P1 bloqueador)
**Via**: GitHub issue ou Slack

#### Conteúdo Sugerido
```markdown
## Issue: Deploy N8N Instrumentation Fix + Infrastructure Updates

**Objetivo**: Aplicar fix de instrumentação preparado em ANA-001

**Artefatos Prontos Neste Repo**:
- reports/N8N_INSTRUMENTATION_ACTION_PLAN_2026-03-30.md (plano técnico)
- reports/N8N_INSTRUMENTATION_VALIDATION_2026-03-30.json (validação)
- reports/n8n_instrumentation_guard_rules_2026-03-30.yaml (Prometheus rules)

**Requerido**:
1. Deploy exporter fix em enterprise-observability (monotonic validation)
2. Propagate cAdvisor labels para Prometheus (fix in wf001)
3. Validar Loki auth 401 (debug credenciais em wfdb01)

** Timeline**: Idealmente esta semana
```

---

### COMUNICADO-002: cAdvisor Labels Propagation
**Para**: DevOps/SRE / `enterprise-observability` maintainers
**Urgência**: 🔴 P1 (bloqueador de observability)
**Via**: GitHub issue ou Slack

#### Conteúdo Sugerido
```markdown
## Issue: cAdvisor Labels Propagation for wf001

**Context**: N8N performance analysis (ANA-001) requer container names em cAdvisor metrics.

**Necessário**:
- Configure cAdvisor daemonset (ou docker labels) em wf001 para expor:
  - `container_name` label (ex: "n8n-workflow", "n8n-execute")
  - Qualquer label de deployment (pod/service names)

**Resultado**: Queries em Prometheus como:
```promql
container_memory_usage_bytes{container_name="n8n-workflow"}
```

**Desbloqueará**: Follow-up analysis de fine-grained performance, task de docker mapping
```

---

## 📅 AGENDA SUGERIDA PARA 2026-03-31

```
☐ 09:00-10:00: TASK-001 [Implementar Gate Proveniência]
☐ 10:00-10:45: TASK-002 [Auditoria Scripts]
☐ 10:45-12:00: TASK-003 [Loki 401 Diagnostic]
☐ 12:00-12:15: COMUNICADO-001, COMUNICADO-002 [Enviar issues]
☐ 12:15-13:15: TASK-004 [Preparar Recording Rules PR]
☐ 13:15-14:00: Documentar findings em TODAY_ACTIVITIES_2026-03-31.md
☐ 14:00-15:00: Aguardando feedback de bloqueadores externos
```

**Total**: 6h de trabalho, sem bloqueadores internos.

---

## 🎯 DEFINIÇÃO DE SUCESSO (Fim do Dia)

✅ **Se isto estiver feito, dia foi sucesso:**

1. TASK-001: `src/n8n_analyzer/analyzers/provenance.py` implementado + testado
2. TASK-002: `.audit_log` criado com histórico + scripts atualizados
3. TASK-003: `LOKI_401_DIAGNOSTIC_2026-03-31.md` documentado
4. TASK-004: `RECORDING_RULES_PR_READY_2026-03-31.md` criado
5. COMUNICADOS: Issues criadas em observability repo com evidências
6. TODAY_ACTIVITIES_2026-03-31.md: Atualizado com progresso

---

## 📊 RASTREAMENTO DE PROGRESSO

Use este template para atualizar a cada tarefa:

```markdown
## Update 2026-03-31

### TASK-001 ✅ CONCLUÍDO [XX:XX]
- Gate implementado em provenance.py
- Tests passando
- Integrado em main.py
- Documentação atualizada

### TASK-002 ⏳ EM PROGRESSO [XX:XX]
- Implementando audit logging...
- Scripts atualizados: [lista]

### TASK-003 🔍 INVESTIGANDO [XX:XX]
- SSH wfdb01 validado
- Token verificado: [resultado]
- Causa raiz: [...] ou "Em investigação"

### Bloqueadores
- COMUNICADO-001: Aguardando response
- COMUNICADO-002: Aguardando response
```

---

## 🔗 REFERÊNCIAS RÁPIDAS

- Contexto Completo: `docs/sessions/2026-03-31/DEBATE_PENDENCIAS_2026-03-31.md`
- Pendências Herdadas: `docs/sessions/2026-03-30/FINAL_STATUS_2026-03-30.md`
- Scripts Fase 1: `scripts/wf001_fase1_pivotado.py`
- Scripts Fase 2: `scripts/wf001_fase2_drilldown.py`
- Instrumentation Plan: `reports/N8N_INSTRUMENTATION_ACTION_PLAN_2026-03-30.md`
- Recording Rules: `reports/PROMETHEUS_RECORDING_RULES_N8N_2026-03-18.md`

---

**Status**: Documento gerado 2026-03-31 12:30 UTC
**Próximo Revisão**: Fim de 2026-03-31
**Owner**: Current session team + observability team (external tasks)
