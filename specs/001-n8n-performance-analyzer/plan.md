# Implementation Plan: N8N Performance Analyzer

**Branch**: `001-n8n-performance-analyzer` | **Date**: 2026-03-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-n8n-performance-analyzer/spec.md`
**Analysis Registry**: ANA-001

## Summary

Build a Python CLI analysis toolset (`scripts/analyze_n8n_performance.py` + `src/` modules) that queries the Enterprise Observability Stack (VictoriaMetrics + Loki) for N8N workflow execution data and produces a structured performance report. The report identifies latency violations (node execution ≥ 1s), correlates them with infrastructure events (Redis queue depth, PostgreSQL query duration, external API latency), separates geographic probe measurements, and assigns structured root-cause labels to each finding. Entry point is a single CLI script; modules are installable via `pip install -e .`.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- `httpx` — async HTTP client for VictoriaMetrics, Loki, and Redis/DB metric queries
- `pandas` — time-series data manipulation and percentile computation
- `jinja2` — Markdown/HTML report templating
- `click` — CLI argument parsing (`--from`, `--to`, `--output-format`, `--step-global`, `--step-drilldown`)
- `pydantic` v2 — data models (`LatencyEvent`, `PerformanceReport`, etc.)
- `python-dotenv` — `.secrets/` env loading
- `pytest` — unit and integration tests
- `pytest-httpx` — HTTP mock for offline/test mode

**Storage**: Output files only — Markdown/JSON reports written to `reports/`. No database writes.
**Testing**: `pytest` with `pytest-httpx` for offline mocking; real integration test against staging metrics optional.
**Target Platform**: Linux/macOS developer workstation (runs locally, queries remote observability stack)
**Project Type**: CLI analysis tool
**Performance Goals**: Full report for 30-day window in < 5 minutes (SC-001); global scan at `5m` step, drilldown at `1m`
**Constraints**: Read-only; no production writes; credentials from `.secrets/` only; all timestamps UTC; exit 0 on partial data, exit 1 only if VictoriaMetrics primary unavailable
**Scale/Scope**: ~75 days of metric data (Jan–Mar 2026); ~8 N8N containers; 2 geographic probes (wf001 US East, wf008 Brazil)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Production Safety** ✅ PASS — This feature is purely read-only. FR-010 explicitly prohibits writing to or restarting any production service. No `# PRODUCTION WRITE` tasks exist in `tasks.md`. The restricted-window rule (08:00–20:30) does not apply.
- [x] **II. Observability-First** ✅ PASS — All data is sourced from VictoriaMetrics (`/api/v1/query_range`), Loki (`/loki/api/v1/query_range`), and optionally the `monitor_user` read-only PostgreSQL account. No direct production DB writes. Every finding references metric name, time range, and data source (FR-007, T040).
- [x] **III. Security** ✅ PASS — FR-006 mandates credential loading from `.secrets/` only; T005 enforces 640 permission check at startup and raises `ConfigError` on violation. `.secrets/` is confirmed in `.gitignore` at line 16. T013 entry-point comment `# ANA-001` contains no credentials. No credential values may appear in log output per config.py design.
- [x] **IV. Reproducible Analysis** ✅ PASS — FR-001 requires explicit `--from`/`--to` parameters; FR-007 encodes the range in the output filename; T013 declares `# ANA-001` at the script top. T040 adds an `## Appendix: Queries` section embedding all executed PromQL/LogQL expressions and step values in every report. SC-005 enforces deterministic re-runs.
- [x] **V. Data Integrity** ✅ PASS — ANA-001 scope is bounded to `n8n_node_execution_duration_seconds` on wf001/wf008. FR-005 and T028–T033 label all metrics by source host (`wf001.vya.digital` vs `wf008.vya.digital`). T029 computes and stores network RTT contribution separately from application latency; the two are never summed without explicit labelling.
- [x] **VI. Analysis Registry** ✅ PASS — ANA-001 is registered in `.specify/memory/constitution.md` Analysis Registry section (status: Active, started 2026-03-17) before any implementation work begins.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

**Structure**: Single project (Option 1) — CLI tool with supporting package under `src/`.

```text
scripts/
└── analyze_n8n_performance.py     # Entry-point shim (# ANA-001 comment at top)

src/
└── n8n_analyzer/
    ├── __init__.py
    ├── cli.py                      # Click CLI: --from, --to, --output-format,
    │                               #   --step-global, --step-drilldown, --output-dir, --dry-run
    ├── config.py                   # Settings loader (.secrets/ + env); 640-permission check
    ├── models/
    │   ├── __init__.py
    │   ├── latency_event.py        # LatencyEvent (Pydantic v2, UTC-validated)
    │   ├── correlation_window.py   # CorrelationWindow
    │   ├── infra_metric.py         # InfraMetricSnapshot (UTC-validated)
    │   └── report.py               # PerformanceReport, Finding, RootCauseLabel enum
    ├── collectors/
    │   ├── __init__.py
    │   ├── base.py                 # BaseCollector (httpx, timeout 30s, 1-retry, PartialDataError)
    │   ├── victoria_metrics.py     # VictoriaMetricsCollector → /api/v1/query_range
    │   └── loki.py                 # LokiCollector → /loki/api/v1/query_range
    ├── analyzers/
    │   ├── __init__.py
    │   ├── latency.py              # LatencyAnalyzer: p50/p95/p99, spike detection, drill-down
    │   ├── correlation.py          # CorrelationAnalyzer: Redis / DB / external API windows
    │   ├── loki_analyzer.py        # LokiAnalyzer: error count, top-N types, co-occurrence
    │   └── geographic.py           # GeographicAnalyzer: wf001 vs wf008 split + RTT estimator
    ├── labels/
    │   ├── __init__.py
    │   └── root_cause.py           # RootCauseLabel enum + classify() decision logic
    └── reporters/
        ├── __init__.py             # build_filename() → n8n_perf_ANA001_<FROM>_<TO>_<TS>.<ext>
        ├── markdown.py             # MarkdownReporter: all sections inc. ## Appendix: Queries
        └── json_reporter.py        # JsonReporter: Pydantic → JSON with ISO-8601 timestamps

tests/
├── conftest.py
├── unit/                          # Pure-logic tests (no network)
└── integration/                   # pytest-httpx mocked HTTP tests

pyproject.toml                     # package metadata + deps + [project.scripts] entry point
.env.example                       # required env var names (no values)
reports/                           # output directory (git-ignored, tracked via .gitkeep)
```

**Structure Decision**: Single project. All N8N analyzer code lives under the `n8n_analyzer` package. The `scripts/` shim keeps the entry point at a predictable path without polluting the package namespace. No backend/frontend split required — this is a CLI tool with no web server component.

## Complexity Tracking

> No Constitution Check violations. This section is empty by design.
