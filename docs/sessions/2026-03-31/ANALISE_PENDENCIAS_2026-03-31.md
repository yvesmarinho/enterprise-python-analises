# Análise de Pendências Herdadas — Sessão 2026-03-31

**Data:** 31/03/2026
**Escopo:** Avaliação técnica, impacto e recomendações de priorização
**Direção:** Consolidação para debate multilíngue com agentes especializados

---

## 1. Resumo Executivo

Das cinco pendências herdadas da sessão 2026-03-30 (vide [FINAL_STATUS_2026-03-30.md](../2026-03-30/FINAL_STATUS_2026-03-30.md)):

| Item | Prioridade | Bloqueador? | Requer Ext.? | Status |
|------|-----------|-----------|------------|--------|
| **Gate de proveniência ANA-001** | P2 | ⚠️ Condicional | ❌ Não | **Pendente análise** |
| **Auditoria proveniência scripts wf001_*.py** | P3 | ❌ Não | ❌ Não | **Pendente análise** |
| [P1] cAdvisor labels | P1 | ✅ Sim | ✅ Sim | Fora do escopo |
| [P1] Loki autenticação | P1 | ✅ Sim | ✅ Sim | Fora do escopo |
| [P2] Recording rules N8N | P2 | ⚠️ Condicional | ✅ Sim | Fora do escopo |

**Recomendação de foco:** As duas pendências analisadas neste documento (P2 e P3) **não dependem de ação externa** e podem ser tratadas **integralmente neste repositório**, diferentemente das P1 que requerem coordenação com `enterprise-observability`.

---

## 2. Pendência 1: Gate de Proveniência ANA-001 (P2)

### 2.1 Definição do Problema

**O que é:** Um **filtro/validador estrutural** que deve ser executado **antes** de qualquer correlação estatística entre métricas de N8N, host e container.

**Por que existe:** O debate de especialistas (seção 6.1 de [DEBATE_ESPECIALISTAS_FALHA_ANALISE_DADOS_VPS_2026-03-30.md](../2026-03-30/DEBATE_ESPECIALISTAS_FALHA_ANALISE_DADOS_VPS_2026-03-30.md)) documentou que a análise anterior **extrapolou conclusões sem provar cadeia completa de proveniência**:

1. Dados de `instance` foram interpretados como `host` sem auditoria de origem.
2. Fontes de cAdvisor vieram marcadas como `wf001` mas sem **mapeamento comprovado** de ID de container → nome de serviço.
3. A série de latência principal (`n8n_workflow_execution_duration_seconds`) tinha **variância zero** (bucket único), invalidando correlação Pearson.
4. Janela temporal efetiva da métrica era **menor que a janela consultada** (falta de cobertura real vs. cobertura teórica).

**Impacto direto:** O relatório final de ANA-001 precisou ser rebaixado a **"análise preliminar"** (vide [RELATORIO_TECNICO_ANALISE_N8N_2026-03-30.md](../2026-03-30/RELATORIO_TECNICO_ANALISE_N8N_2026-03-30.md), seção 4).

---

### 2.2 Localização Técnica no Pipeline

```
cli.py (_run_analysis)
│
├─ 1. Config load + env resolve ✅ Implementado
│
├─ 2. LatencyAnalyzer.analyze()          ← Serie alvo principal
│   └─ Query: histogram_quantile(0.95, n8n_workflow_execution_duration_seconds_bucket[window])
│      Labels: {workflow_id, workflow_name, instance, le}
│
├─ 3. [**MISSING GATE**] Provenance validation
│   ├─ Check 1: instance ∈ {"wf001", "wf008", "wfdb01", ...} (whitelist válidos)
│   ├─ Check 2: Série tem variância > min_threshold (atualmente não validado)
│   ├─ Check 3: Cobertura temporal: >80% de pontos no intervalo solicitado
│   ├─ Check 4: Se filtro houve (label_filter), validar injetado corretamente
│   └─ Check 5: Se correlação, validar que series origem e alvo têm mesmo host
│
├─ 4. CorrelationAnalyzer.analyze()      ← Depende de 3 ser válido
│
└─ 5. Report generation
```

**Status Code:** Não existe código para esta validação. O pipeline pula direto para análise.

---

### 2.3 Impacto Técnico no Projeto

#### A. Downstream — Relatórios Executivos

| Afetado | Risco | Evidência |
|---------|-------|-----------|
| `--output-format markdown` | 🔴 **Alto** | Relatórios MD podem conter conclusões sobre ofensors de container sem cadeia completa |
| `--output-format json` | 🟡 **Médio** | JSON retorna série bruta; sem validação, consumidor externo não sabe se é confiável |
| `LatencyEvent` (modelo) | 🟡 **Médio** | Modelo inclui campo `is_violation` — sem proveniência, a flag é sem garantia |
| `InfraMetricSnapshot` (modelo) | 🟡 **Médio** | Snapshot de métrica infra pode não estar alinhado com host real |

#### B. Bloqueador de Outras Tarefas?

**Condicional — SIM:**
- ✅ Se continuar desenvolvendo **novos analyzers** (ex: geographic v2, node-level) — **BLOQUEADOR**
- ✅ Se rotinizar ANA-001 para **daily/weekly reports** — **BLOQUEADOR CRÍTICO**
- ❌ Se objetivo é apenas análise exploratória ad hoc — **Não bloqueia**
- ❌ Se apenas refatoração de código local — **Não bloqueia**

**Relação com outras P2:**
- Recording rules N8N (P2): **depende parcialmente** — se as rules usarem gate, precisam de validação.
- cAdvisor labels P1: **ortogonal** — gate não espera dados de cAdvisor, apenas valida que há dados.

---

### 2.4 Recomendação Técnica de Resolução

#### Phase 1: Validação Estrutural (Esforço: 4-6h)

```python
# Novo módulo: src/n8n_analyzer/gates/provenance_gate.py

class ProvenanceGate:
    """Validates series provenance before correlation."""

    def __init__(self, config: Config):
        self.valid_hosts = {"wf001", "wf008", "wfdb01", "wfdb02"}
        self.min_variance = 0.001  # Threshold mínimo de variância
        self.min_coverage = 0.80   # 80% de pontos esperados

    def validate_series(
        self,
        labels: dict[str, str],
        timestamps: list[float],
        values: list[str],
        expected_points: int,
    ) -> ValidationResult:
        """Returns ValidationResult with confidence score and reason."""

        # Check 1: instance whitelist
        instance = labels.get("instance")
        if not self._is_valid_instance(instance):
            return ValidationResult.FAIL(
                reason=f"instance={instance!r} not in whitelist",
                confidence=0.0
            )

        # Check 2: Variance
        numeric_values = [float(v) for v in values if is_numeric(v)]
        variance = numpy.var(numeric_values)
        if variance < self.min_variance:
            return ValidationResult.FAIL(
                reason=f"variance={variance:.6f} < {self.min_variance}",
                confidence=0.2  # Partial — data exists but not varied
            )

        # Check 3: Coverage
        coverage = len(numeric_values) / expected_points
        if coverage < self.min_coverage:
            return ValidationResult.WARN(
                reason=f"coverage={coverage:.1%} < {self.min_coverage:.0%}",
                confidence=0.5
            )

        return ValidationResult.PASS(confidence=0.9)
```

#### Phase 2: Integration na CLI (Esforço: 2-3h)

```python
# Em cli.py, após latency_results:

from n8n_analyzer.gates.provenance_gate import ProvenanceGate

gate = ProvenanceGate(config)
validated_events = []

for event in latency_results:
    validation = gate.validate_series(
        labels=...,
        timestamps=...,
        values=...,
        expected_points=...
    )

    if validation.status == "FAIL":
        logger.warning(f"Series {event.workflow_id} rejected: {validation.reason}")
        continue  # Skip this event from correlation
    elif validation.status == "WARN":
        event.confidence_score = validation.confidence

    validated_events.append(event)

# Proceder só com validated_events
results = await correlation_analyzer.analyze(validated_events, ...)
```

#### Phase 3: Report Confidence Annotation (Esforço: 1-2h)

```python
# Em reporters/markdown.py (ou json.py):

report.add_section(
    "Data Quality Gate Results",
    f"✓ {len(validated_events)} of {len(total_events)} events passed provenance validation\n"
    f"✗ {len(rejected_events)} events rejected (missing variance, wrong host, etc.)\n"
    f"⚠ {len(warned_events)} events with reduced confidence"
)

for event in results:
    event_card = f"""
    Workflow: {event.workflow_id}
    p95: {event.p95_seconds:.3f}s
    Provenance Confidence: {event.confidence_score:.1%}  ← NOVO
    """
```

**Total Effort:** 7-11 horas = ~1-1.5 dias

---

### 2.5 Critério de Aceite

- [ ] Novo módulo `src/n8n_analyzer/gates/provenance_gate.py` com 3 checks (whitelist, variance, coverage)
- [ ] Gate integrado em `cli.py`, executado após LatencyAnalyzer e antes de CorrelationAnalyzer
- [ ] Relatórios Markdown e JSON incluem seção "Provenance Validation Results"
- [ ] Cada `LatencyEvent` retornado inclui campo `confidence_score` (0.0–1.0)
- [ ] Testes: `tests/unit/test_provenance_gate.py` com casos de falha (low variance, wrong instance, incomplete coverage)
- [ ] Se confiança < 0.5, relatório MD inclui aviso executivo de rebaixamento

---

## 3. Pendência 2: Auditoria de Proveniência Scripts wf001_*.py (P3)

### 3.1 Definição do Problema

**O que é:** Validar que os scripts de análise exploratória (`scripts/wf001_*.py`) **usam mapeamento correto** entre:
- `host` do SO (exemplo: `wf001.vya.digital`)
- `instance` label do PromQL (exemplo: `wf001` ou `31.220.103.208:9100`)
- `node_instance` (exemplo: `wf001.vya.digital:9100`)
- Nome real de container (exemplo: `prod-collector-api`)

**Por que existe:** Os scripts [wf001_fase1_pivotado.py](../../../scripts/wf001_fase1_pivotado.py) e [wf001_fase2_drilldown.py](../../../scripts/wf001_fase2_drilldown.py) usam hardcoded:

```python
# Linha ~20 em ambos:
N8N_INSTANCE  = "wf001"
NODE_INSTANCE = "wf001.vya.digital:9100"
```

**Risco:** Se houver mudança de topologia (ex: `instance` muda para `wf001.internal`), os scripts ficam **silenciosamente errados** sem detectar discrepância.

---

### 3.2 Localização Técnica

```
scripts/
├── wf001_fase1_pivotado.py     ← Lines 20–25: hardcoded instance values
│   ├ VM_URL = "http://localhost:18428"
│   ├ N8N_INSTANCE = "wf001"           ⚠️
│   └─ NODE_INSTANCE = "wf001.vya.digital:9100"  ⚠️
│
├── wf001_fase2_drilldown.py    ← Same pattern
│   ├ N8N_INSTANCE = "wf001"
│   └─ CADVISOR_INSTANCE = "enterprise-cadvisor:8080"
│
└── [MISSING] validate_wf001_instance_mapping.py
    └─ Should: Query Prometheus labels + compare vs. hardcoded values
```

**Problema concreto:**
- Se `prod-collector-api` (container em wf001) muda a label `instance` para `wf001.internal`, os scripts continuam querying `wf001` e retornam **série vazia silenciosamente**.
- Não há alerta de "instance mismatch".

---

### 3.3 Impacto Técnico

#### A. Downstream — Reprodutibilidade

| Afetado | Risco | Cenário |
|---------|-------|---------|
| Documentação de fase 1/2 | 🟡 **Médio** | Se scripts rodam com `instance` errado, relatórios MD/JSON viram inconsistentes com comentários no código |
| Drill-down ad hoc | 🟡 **Médio** | Análise manual fica tediosa: "por que o query retorna 0 séries?" → não há validação automática |
| Treinamento/Onboarding | 🔴 **Alto** | Novo desenvolvedor copia scripts, encontra série vazia, bloqueia análise por horas |
| Audit trail | 🟡 **Médio** | Dificuldade em rastrear: "qual `instance` foi usado nesta análise?" |

#### B. Bloqueador de Outras Tarefas?

**Não é bloqueador do tipo "impede execução", mas é "bloqueador de confiança":**
- ❌ Não bloqueia rotina ANA-001 (que já tem seu próprio gate)
- ❌ Não bloqueia desenvolvimento de novo features
- ✅ **Bloqueia reutilização confiável dos scripts** — se rotinizar para daily/weekly, risco alto

---

### 3.4 Recomendação Técnica de Resolução

#### Phase 1: Criar Validador de Mapeamento (Esforço: 3-4h)

```python
# scripts/validate_wf001_instance_mapping.py

"""
Validate that hardcoded instance values in wf001_*.py match actual Prometheus targets.

Usage:
  python scripts/validate_wf001_instance_mapping.py \
    --prometheus-url http://localhost:9090 \
    --expected-instances wf001,wf008 \
    --expected-hosts wf001.vya.digital,wf008.vya.digital
"""

import argparse
import requests
from urllib.parse import urljoin


def get_active_targets(prometheus_url: str) -> dict[str, list[str]]:
    """Query Prometheus /api/v1/targets and return {job: [instance, ...]}."""
    try:
        resp = requests.get(urljoin(prometheus_url, "/api/v1/targets"), timeout=10)
        resp.raise_for_status()
        data = resp.json()

        targets = {}
        for target in data.get("data", {}).get("activeTargets", []):
            labels = target["labels"]
            job = labels.get("job")
            instance = labels.get("instance")
            if job and instance:
                targets.setdefault(job, []).append(instance)
        return targets
    except Exception as e:
        raise RuntimeError(f"Failed to query Prometheus: {e}")


def validate_n8n_collector(prometheus_url: str) -> dict:
    """Check that n8n collector job has expected instance labels."""
    targets = get_active_targets(prometheus_url)
    n8n_targets = targets.get("n8n-collector", [])  # Job name in scrape_configs

    result = {
        "job_exists": len(n8n_targets) > 0,
        "instances": n8n_targets,
        "expected": ["wf001", "wf008"],  # ← From scripts config
        "valid": set(n8n_targets) >= {"wf001", "wf008"},  # At least these two
    }

    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prometheus-url", default="http://localhost:9090")
    args = parser.parse_args()

    result = validate_n8n_collector(args.prometheus_url)

    print(f"Validation Result:")
    print(f"  Job 'n8n-collector' exists: {result['job_exists']}")
    print(f"  Instances found: {result['instances']}")
    print(f"  Expected:       {result['expected']}")
    print(f"  Status: {'✅ PASS' if result['valid'] else '❌ FAIL'}")

    if not result['valid']:
        print(f"\n  WARNING: Instance mismatch!")
        print(f"  Hardcoded scripts assume: {set(result['expected'])}")
        print(f"  Prometheus has:           {set(result['instances'])}")
        print(f"\n  Update scripts/wf001_*.py with correct instances:")
        for inst in result['instances']:
            print(f"    N8N_INSTANCE = {inst!r}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
```

#### Phase 2: Refactor Scripts para usar Config (Esforço: 2-3h)

**Antes:**
```python
# wf001_fase1_pivotado.py
N8N_INSTANCE  = "wf001"
NODE_INSTANCE = "wf001.vya.digital:9100"
```

**Depois:**
```python
# wf001_fase1_pivotado.py

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from n8n_analyzer.config import Config

# Load from config (or env fallback)
config = Config()
# config.n8n_instance_label ← new field in Config
N8N_INSTANCE  = config.n8n_instance_label or "wf001"
NODE_INSTANCE = config.n8n_node_instance or "wf001.vya.digital:9100"
```

**Em `config.py`:**
```python
class Config(BaseSettings):
    n8n_instance_label: str = Field(
        default="wf001",
        description="Prometheus instance label for N8N collector"
    )
    n8n_node_instance: str = Field(
        default="wf001.vya.digital:9100",
        description="Full node exporter instance (host:port)"
    )

    @field_validator("n8n_instance_label")
    @classmethod
    def validate_instance(cls, v: str) -> str:
        """Ensure instance is in valid set."""
        valid = {"wf001", "wf008", "wfdb01"}
        if v not in valid:
            raise ValueError(f"{v} not in {valid}")
        return v
```

#### Phase 3: CI/CD Validation Hook (Esforço: 1-2h)

**Em `Makefile`:**
```makefile
.PHONY: validate-scripts
validate-scripts:
	@echo "Validating wf001_*.py instance mappings..."
	python scripts/validate_wf001_instance_mapping.py \
	  --prometheus-url $(PROMETHEUS_URL)
	@echo "✓ Instance mapping validated"

# Add to test target:
test: validate-scripts pytest
```

**Total Effort:** 6-9 horas = ~1 dia

---

### 3.5 Critério de Aceite

- [ ] Novo script `scripts/validate_wf001_instance_mapping.py` queries Prometheus `/api/v1/targets`
- [ ] Script compara instances encontrados vs. hardcoded em `wf001_*.py`
- [ ] Se mismatch, script retorna exit code 1 + mensagem clara de "update required"
- [ ] `wf001_*.py` refatorados para carregar `n8n_instance_label` do `Config` (não hardcoded)
- [ ] `Config` valida `n8n_instance_label` contra whitelist
- [ ] Makefile target `make validate-scripts` integrado
- [ ] Testes: `tests/unit/test_wf001_instance_mismatch.py` com mock de targets retornando valores errados

---

## 4. Análise Comparativa das Pendências

### 4.1 Matriz de Decisão

| Aspecto | Gate ANA-001 (P2) | Auditoria Scripts (P3) |
|--------|---------|---------|
| **Impacto** | 🔴 Alto — Afeta confiança de relatórios executivos | 🟡 Médio — Afeta reprodutibilidade de análises ad hoc |
| **Bloqueador** | ⚠️ Condicional — Sim se rotinizar reports | ❌ Não — Desejável mas não obrigatório |
| **Dependência Externa** | ❌ Não | ❌ Não |
| **Esforço** | 7-11h (~1.5d) | 6-9h (~1d) |
| **Complexidade** | 🟡 Média — Novo módulo + integração | 🟢 Baixa — Refactor + validador simples |
| **Risco de Não Fazer** | 🔴 Alto — Conclusões sem garantia | 🟡 Médio — Scripts quebram silenciosamente |
| **Urgência** | ✅ Antes de daily reports | ⚠️ Antes de onboarding novo dev |

### 4.2 Recomendação de Sequência

**Opção A — Sequential (Recomendado para legibilidade):**
1. **Week 1, Day 1-2:** Gate ANA-001 (P2) — Foundation para confiança
2. **Week 1, Day 3:** Auditoria Scripts (P3) — Refinement
3. **Week 2:** Begin rotinização e onboarding

**Opção B — Parallel (Se pressão de tempo):**
- Day 1: Gate ANA-001 + Auditoria Scripts (2 devs) em paralelo
- Day 2: Integração e testes cruzados
- Day 3: CI/CD

**Recomendação da sessão:** **Opção A** — o Gate é foundation; a Auditoria depende conceitualmente dele.

---

## 5. Coordenação External — Avaliação

### 5.1 Gate ANA-001 (P2)

**Requer Env Externo?** ❌ **Não**
- ✅ Tudo acontece em `enterprise-python-analysis` (este repo)
- ✅ Não toca em `enterprise-observability`, `enterprise-dashboards` ou `wfdb01`
- ✅ Config.py define thresholds e whitelists localmente
- ✅ Testes rodam com mocks (pytest-httpx)

**Coordenação sugerida:**
- Code review com especialista em **Observability** (rever design do gate)
- Feedback de especialista em **Data Analyzer** (validar critérios de variância)

---

### 5.2 Auditoria Scripts (P3)

**Requer Env Externo?** ⚠️ **Parcialmente**
- ✅ Validador local (novo script) — neste repo
- ⚠️ Validação contra Prometheus — precisa de Prometheus acessível (via SSH tunnel se necessário)
- ❌ Não toca em código externo

**Coordenação sugerida:**
- Clarificação com especialista em **Prometheus** sobre job names (`n8n-collector` vs. outros)
- Sync com **System Engineer** sobre nomes reais de instance em produção

---

## 6. Plano de Integração em Debate Multilíngue

### 6.1 Tópicos para Discussão com Agentes

| Agente | Topico para P2 (Gate) | Topico para P3 (Scripts) |
|--------|-------------|-------------|
| **Observability** | Design de gates para data quality; como não bloquear exploração | Job naming convention e instance resolution |
| **Data Analyst** | Critérios de variância mínima; impacto em confiança de relatório | Validação de série não vazia antes de análise |
| **Prometheus** | PromQL label injection safety; instance whitelist | Active targets validation; job discovery |
| **Python Dev** | Integração de gate no pipeline CLI; configuration defaults | Config pattern para shared constants |
| **Docker** | Como validar container origin sem CDvisor quando não disponível | — |
| **System Engineer** | Mapping host ↔ instance ↔ cgroups | Inventory de production instance labels |

---

## 7. Recomendação Final de Priorização

```
PRIORITY MATRIX
═══════════════════════════════════════════════════════════════

URGENT & IMPORTANT:
  ├─ [P1] cAdvisor labels — SKIP (external dependency)
  ├─ [P1] Loki 401 — SKIP (external dependency)
  └─ [P2] Recording rules N8N — SKIP (external dependency)

IN-SCOPE & CAN IMPLEMENT NOW:
  ├─ [P2] Gate de Proveniência ANA-001 ← START HERE (foundation)
  └─ [P3] Auditoria Scripts wf001_* ← FOLLOW UP (refinement)

═══════════════════════════════════════════════════════════════

RECOMMENDATION FOR 2026-03-31 SESSION:

1. [IMMEDIATE] Initiate technical debate on Gate ANA-001 design
   └─ Target: consensus on variance thresholds, coverage %, whitelist

2. Then refactor + implement Gate module (parallel optionally with Auditoria)

3. [DEFERRED] Auditoria Scripts — design but don't block on Gate

4. [EXTERNAL] Coordinate with enterprise-observability for P1/P2 external items
```

---

## 8. Referências de Suporte

- [Debate Técnico Completo](../2026-03-30/DEBATE_ESPECIALISTAS_FALHA_ANALISE_DADOS_VPS_2026-03-30.md) — Seção 6-7 detalhando falhas de proveniência
- [Relatório Técnico](../2026-03-30/RELATORIO_TECNICO_ANALISE_N8N_2026-03-30.md) — Seção 4 sobre rebaixamento de confiança
- [Ação de Instrumentação](../2026-03-30/N8N_INSTRUMENTATION_ACTION_PLAN_2026-03-30.md) — Contexto de P2 externa (recording rules)
- [Scripts de Análise](../../../scripts/wf001_fase1_pivotado.py) e [Fase 2](../../../scripts/wf001_fase2_drilldown.py) — Código alvo da auditoria
- [Collector VictoriaMetrics](../../../src/n8n_analyzer/collectors/victoria_metrics.py) — Where gate integrates

---

**Preparado por:** GitHub Copilot (Python Dev Agent)
**Para debate com:** Observability, Data Analyst, Prometheus, System Engineer
**Versão:** 1.0
**Status:** Pronto para consolidação multilíngue
