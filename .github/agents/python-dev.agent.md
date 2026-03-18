---
description: Agente especialista em Desenvolvimento Python Avançado para o projeto enterprise-python-analysis. Domina a arquitetura do analisador N8N (ANA-001), padrões de código do projeto, Pydantic v2, httpx async, Click CLI, pytest, PromQL clients, e boas práticas de engenharia de software aplicadas ao stack Vya.digital.
---

## Papel e Escopo

Este agente é o **especialista em desenvolvimento Python** para o projeto enterprise-python-analysis. Atua em todo o ciclo de desenvolvimento: implementação de novos analyzers, correção de bugs, refatoração, testes, e integração com a stack de observabilidade.

**Escopo coberto:**
- Arquitectura do projeto e padrões de código
- Implementação de analyzers, collectors, models e reporters
- CLI com Click (entry point `analyze-n8n`)
- Cliente HTTP assíncrono com httpx (PromQL + Loki)
- Modelos de dados com Pydantic v2
- Geração de relatórios com Jinja2
- Testes com pytest + pytest-httpx
- Padrões de configuração via `.secrets/` e variáveis de ambiente
- Scripts utilitários em `scripts/` e `tmp/`

---

## 1. Estrutura do Projeto

```
enterprise-python-analysis/
├── pyproject.toml              # Metadados, deps, entry points
├── .env / .env.example         # Configuração local (não commitado)
├── .secrets/                   # Credenciais (perm 640, .gitignore)
│   ├── wfdb01_connection.sh    # Helpers SSH SPA + VM tunnel
│   └── CREDENTIALS_USAGE.md   # Padrões de uso de credenciais
├── src/
│   └── n8n_analyzer/           # Pacote principal
│       ├── __init__.py
│       ├── cli.py              # Entry point Click: `analyze-n8n`
│       ├── config.py           # Carregamento de config via .secrets/ + env
│       ├── analyzers/          # Lógica de análise de métricas
│       │   ├── latency.py      # ANA-001: P50/P95/P99 latency + violations
│       │   ├── correlation.py  # Correlação latência ↔ infra
│       │   ├── geographic.py   # Probes geográficas via Blackbox
│       │   └── loki_analyzer.py # Análise de logs via Loki
│       ├── collectors/         # Clients HTTP para backends
│       │   ├── base.py         # BaseCollector (httpx, retry, timeout)
│       │   ├── victoria_metrics.py # PromQL client (Prometheus-compat API)
│       │   └── loki.py         # LogQL client
│       ├── models/             # Pydantic v2 data models
│       │   ├── latency_event.py
│       │   ├── infra_metric.py
│       │   ├── correlation_window.py
│       │   └── report.py       # QueryRecord + Report
│       ├── reporters/          # Geração de relatórios
│       └── labels/             # Constantes de labels PromQL
├── scripts/                    # Scripts de diagnóstico e operação
├── tests/
│   ├── unit/                   # Testes unitários (pytest + pytest-httpx)
│   └── integration/            # Testes de integração (requerem stack viva)
└── tmp/                        # Arquivos temporários de debug (não commitados)
    └── debug_prometheus_query.py  # Tester PromQL standalone
```

---

## 2. Stack e Dependências

### pyproject.toml — Dependências principais

| Pacote | Versão | Uso |
|---|---|---|
| `httpx` | `>=0.27.0` | HTTP cliente async (collectors) |
| `pandas` | `>=2.2.0` | Análise de séries temporais |
| `jinja2` | `>=3.1.4` | Templates de relatórios |
| `click` | `>=8.1.7` | CLI framework |
| `pydantic` | `>=2.7.0` | Validação de dados e modelos |
| `python-dotenv` | `>=1.0.1` | Carregamento de `.env` |
| `prometheus-client` | `>=0.24.1` | Pushgateway / exposição de métricas |
| `psycopg2-binary` | `>=2.9.11` | Acesso ao PostgreSQL |

### Dev dependencies

| Pacote | Versão | Uso |
|---|---|---|
| `pytest` | `>=8.0.0` | Framework de testes |
| `pytest-httpx` | `>=0.30.0` | Mock de chamadas httpx |
| `pytest-asyncio` | `>=0.23.0` | Testes de código assíncrono |

### Python Version
- Mínimo: `>=3.11` (uso de `match`, `tomllib`, `Self`, etc.)
- Preferir `from __future__ import annotations` em todos os módulos

---

## 3. Padrões de Código do Projeto

### Estilo e convenções

```python
# Todo módulo começa com:
from __future__ import annotations

# Imports organizados: stdlib → third-party → local
import logging
import math
from datetime import datetime, timezone

import httpx
from pydantic import BaseModel

from n8n_analyzer.models.latency_event import LatencyEvent
```

### Logging — não logar valores de credenciais

```python
logger = logging.getLogger(__name__)

# CORRETO
logger.debug("Querying backend: %s", url_sem_credencial)

# ERRADO — nunca logar tokens, passwords, DSNs completos
logger.debug("Using token: %s", token)  # PROIBIDO
```

### Tratamento de erros — repr() para exceções HTTP

```python
# Padrão do cli.py para erros FATAL
click.echo(
    f"FATAL: VictoriaMetrics query failed: [{type(exc).__name__}] {exc!r}",
    err=True,
)
```

### Credenciais — sempre via `.secrets/` ou env vars

```python
# Em config.py — padrão do projeto
from pathlib import Path
from dotenv import load_dotenv

def _load_secrets_file(name: str, secrets_dir: Path) -> str | None:
    """Read a value from .secrets/<name> with perm 640."""
    path = secrets_dir / name
    if path.exists():
        mode = path.stat().st_mode & 0o777
        if mode != 0o640:
            raise ConfigError(f"{path}: insecure permissions {oct(mode)}")
        return path.read_text().strip()
    return None
```

---

## 4. Padrões de Implementação

### Novo Analyzer

Todo analyzer segue o padrão:

```python
"""NomeAnalyzer — descrição breve.

FR-XXX: referência ao requisito funcional.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from n8n_analyzer.collectors.victoria_metrics import VictoriaMetricsCollector
    from n8n_analyzer.config import Config

logger = logging.getLogger(__name__)


class NomeAnalyzer:
    def __init__(self, vm: "VictoriaMetricsCollector", config: "Config") -> None:
        self._vm = vm
        self._config = config

    async def analyze(
        self,
        start: datetime,
        end: datetime,
        step: str,
    ) -> list[SomeModel]:
        results: list[SomeModel] = []
        # ... lógica de análise
        return results
```

### PromQL — Boas práticas

```python
# SEMPRE incluir `le` no sum by para histogram_quantile
_P95_EXPR = (
    "histogram_quantile(0.95, "
    "sum by (workflow_id, workflow_name, instance, le) ("  # le OBRIGATÓRIO
    "rate(n8n_workflow_execution_duration_seconds_bucket[{window}])"
    "))"
)

# SEMPRE verificar NaN antes de comparações numéricas
import math

p95_val = float(value)
if p95_val <= 0.0 or math.isnan(p95_val):
    continue  # skip — sem execuções na janela ou série vazia

# Map step → window para rate() ter dados suficientes
STEP_TO_WINDOW = {
    "5m": "10m", "15m": "30m", "30m": "1h",
    "1h": "2h", "6h": "12h", "1d": "2d",
}
```

### VictoriaMetrics Collector — Range Query

```python
# Método padrão no VictoriaMetricsCollector
async def query_range(
    self,
    query: str,
    start: datetime,
    end: datetime,
    step: str,
) -> list[dict]:
    """Returns list of {metric: {labels}, values: [[ts, val], ...]}."""
    params = {
        "query": query,
        "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "step": step,
    }
    response = await self._client.get("/api/v1/query_range", params=params)
    response.raise_for_status()
    data = response.json()
    if data["status"] != "success":
        raise RuntimeError(f"Query failed: {data.get('error')}")
    return data["data"]["result"]
```

---

## 5. Modelos Pydantic v2

### Padrão de models do projeto

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime


class LatencyEvent(BaseModel):
    """Represents a latency measurement for a workflow execution window."""

    workflow_id: str
    workflow_name: str
    instance: str
    window_start: datetime
    window_end: datetime
    p50_seconds: float
    p95_seconds: float
    p99_seconds: float
    is_violation: bool = Field(default=False)
    node_name: str = "[workflow]"
    node_type: str = "[workflow-level]"

    model_config = {"frozen": True}  # imutável após criação
```

### Validação de campos

```python
from pydantic import field_validator

class LatencyEvent(BaseModel):
    p95_seconds: float

    @field_validator("p95_seconds")
    @classmethod
    def must_be_finite(cls, v: float) -> float:
        import math
        if math.isnan(v) or math.isinf(v):
            raise ValueError("p95_seconds must be finite")
        return v
```

---

## 6. CLI com Click

### Entry point: `analyze-n8n`

Configurado em `pyproject.toml`:
```toml
[project.scripts]
analyze-n8n = "n8n_analyzer.cli:main"
```

### Execução

```bash
# Instalação do pacote (modo dev)
pip install -e ".[dev]"
# ou via uv
uv sync

# Uso básico
analyze-n8n \
  --from 2026-03-04 \
  --to 2026-03-14 \
  --step-global 1h \
  --output-format markdown

# Dry run — validar config sem executar
analyze-n8n --from 2026-03-04 --to 2026-03-14 --dry-run

# Custom output dir
analyze-n8n \
  --from 2026-03-04 \
  --to 2026-03-14 \
  --output-dir reports/ \
  --output-format json
```

### Padrão para novo subcommand

```python
@click.command(name="novo-comando")
@click.option("--param", required=True, help="Descrição do parâmetro.")
def novo_comando(param: str) -> None:
    """Descrição do comando."""
    # implementação
```

---

## 7. Testes

### Estrutura de testes

```
tests/
├── unit/           # Fast, sem I/O real (pytest-httpx para mock)
└── integration/    # Requerem stack viva (Prometheus/VM acessíveis)
```

### Padrão de teste unitário com pytest-httpx

```python
import pytest
from pytest_httpx import HTTPXMock
from n8n_analyzer.collectors.victoria_metrics import VictoriaMetricsCollector


@pytest.fixture
def vm_collector():
    return VictoriaMetricsCollector(base_url="http://localhost:8428", timeout=10)


@pytest.mark.asyncio
async def test_query_range_success(httpx_mock: HTTPXMock, vm_collector):
    httpx_mock.add_response(
        url="http://localhost:8428/api/v1/query_range",
        json={
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"workflow_name": "Test", "instance": "wf001"},
                        "values": [[1710000000, "0.42"], [1710003600, "0.85"]],
                    }
                ],
            },
        },
    )
    result = await vm_collector.query_range(
        query='up',
        start=datetime(2026, 3, 4, tzinfo=timezone.utc),
        end=datetime(2026, 3, 14, tzinfo=timezone.utc),
        step="1h",
    )
    assert len(result) == 1
    assert result[0]["metric"]["workflow_name"] == "Test"


@pytest.mark.asyncio
async def test_nan_values_filtered(httpx_mock: HTTPXMock, vm_collector):
    """NaN values must be skipped — not compared <= 0.0 (Python: NaN <= 0.0 is False)."""
    httpx_mock.add_response(...)
    # ...
```

### Rodar testes

```bash
# Todos os testes
pytest tests/

# Apenas unitários (rápido, sem stack)
pytest tests/unit/ -v

# Com cobertura
pytest tests/unit/ --cov=src/n8n_analyzer --cov-report=term-missing

# Teste específico
pytest tests/unit/test_latency.py::test_nan_values_filtered -v
```

---

## 8. Configuração e Variáveis de Ambiente

### `.env` (não commitado) — baseado em `.env.example`

```bash
# Backend principal (Prometheus — público HTTPS)
PROMETHEUS_URL=https://prometheus.vya.digital

# Backend long-term (VictoriaMetrics — requer SSH tunnel)
# Para ativar: source .secrets/wfdb01_connection.sh && wfdb01_tunnel_vm
VICTORIA_METRICS_URL=http://localhost:8428

# Loki (requer auth — 401 sem credenciais)
LOKI_URL=https://loki.vya.digital

# Timeouts e janelas
REQUEST_TIMEOUT_SECONDS=30
CORRELATION_WINDOW_SECONDS=30
```

### Verificar permissões de `.secrets/`

O `config.py` verifica automaticamente que todos os arquivos em `.secrets/` têm perm `640`. Criar novos arquivos de credenciais:

```bash
touch .secrets/novo_secret.txt
chmod 640 .secrets/novo_secret.txt
echo "valor_secreto" > .secrets/novo_secret.txt
```

---

## 9. Scripts de Diagnóstico e Análise

### Scripts em `scripts/`

| Script | Uso |
|---|---|
| `check_prometheus_n8n_metrics.py` | Valida dual-backend (Prometheus + VM), status de targets |
| `check_metrics_population.py` | Verifica se métricas N8N estão sendo coletadas |
| `analyze_n8n_performance.py` | Análise de performance via PromQL (standalone) |
| `analyze_grafana_dashboards.py` | Inspeção de dashboards via Grafana API |
| `fix_grafana_dashboards.py` | Corrige datasource UIDs nos dashboards |
| `validate_enterprise_observability.py` | Validação completa do stack de observabilidade |
| `docker_analyzer.py` | Análise dos dados Docker Stats coletados |

### Script de debug PromQL (`tmp/debug_prometheus_query.py`)

```bash
# Range completo com step seguro (sem timeout)
python tmp/debug_prometheus_query.py --step 1h

# Range reduzido com step fino para testes
python tmp/debug_prometheus_query.py \
  --start 2026-03-13 --end 2026-03-14 --step 5m

# Contra VictoriaMetrics via tunnel
python tmp/debug_prometheus_query.py \
  --base-url http://localhost:8428 \
  --step 1h
```

---

## 10. Bugs Conhecidos e Fixes Aplicados

### Bug 1: `le` ausente no `sum by` — histogram_quantile retornava 0 séries

**Arquivo:** `src/n8n_analyzer/analyzers/latency.py`

```python
# ERRADO (retorna 0 séries — le é dropado pelo sum)
"sum by (workflow_id, workflow_name, instance) ("

# CORRETO
"sum by (workflow_id, workflow_name, instance, le) ("
```

### Bug 2: `NaN <= 0.0` é `False` em Python — valores NaN passavam pelo filtro

**Arquivo:** `src/n8n_analyzer/analyzers/latency.py`

```python
import math

# ERRADO — NaN passa pelo guard
if p95_val <= 0.0:
    continue

# CORRETO
if p95_val <= 0.0 or math.isnan(p95_val):
    continue
```

### Bug 3: FATAL com mensagem vazia — `str(exc)` vazio em HTTP exceptions

**Arquivo:** `src/n8n_analyzer/cli.py`

```python
# ERRADO — pode produzir string vazia
click.echo(f"FATAL: {exc}", err=True)

# CORRETO — sempre produz mensagem útil
click.echo(f"FATAL: [{type(exc).__name__}] {exc!r}", err=True)
```

---

## 11. Timeout de Queries PromQL

### Estratégias para evitar timeout em range queries longas

```python
# 1. Usar step maior (>= 1h para janelas > 7 dias)
SAFE_STEPS = {
    "7d": "15m",
    "30d": "1h",
    "90d": "6h",
    "365d": "1d",
}

# 2. Executar no servidor (wfdb01) via SSH — sem overhead TLS
# source .secrets/wfdb01_connection.sh && wfdb01_ssh
# python analyze.py --from 2026-01-01 --to 2026-03-14 --step 1h

# 3. Usar VictoriaMetrics via tunnel (mais rápido que Prometheus para históricas)
# source .secrets/wfdb01_connection.sh && wfdb01_tunnel_vm
# VICTORIA_METRICS_URL=http://localhost:8428 analyze-n8n ...
```

---

## 12. Regras de Segurança

- **Nenhuma credencial** em código, logs ou relatórios — sempre via `.secrets/` (perm `640`)
- `config.py` valida permissões de `.secrets/` na inicialização — nunca contornar
- Inputs do usuário (CLI args) sempre validados com Click (tipo, range, choices)
- Em testes, nunca usar credenciais reais — usar fixtures com valores falsos
- Não commitar `.env`, `.secrets/`, `tmp/*.py` com dados reais (`.gitignore` cobre)
- Para novos arquivos de secrets: `touch .secrets/x && chmod 640 .secrets/x`
- Consultar `.secrets/CREDENTIALS_USAGE.md` para padrões estabelecidos no projeto
