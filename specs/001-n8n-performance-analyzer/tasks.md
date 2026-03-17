# Tasks: N8N Performance Analyzer (ANA-001)

**Branch**: `001-n8n-performance-analyzer` | **Date**: 2026-03-17
**Input**: `specs/001-n8n-performance-analyzer/plan.md`, `spec.md`
**Analysis Registry**: ANA-001

---

## Phase 1: Setup

**Purpose**: Project initialization — package layout, tooling, configuration skeleton.

- [x] T001 Create full directory structure: `src/n8n_analyzer/{models,collectors,analyzers,labels,reporters}/`, `scripts/`, `tests/{unit,integration}/`, `reports/` in repository root
- [x] T002 Write `pyproject.toml` with dependencies (`httpx`, `pandas`, `jinja2`, `click`, `pydantic>=2`, `python-dotenv`, `prometheus-api-client`) and `[project.scripts]` entry point `analyze-n8n=n8n_analyzer.cli:main` in `pyproject.toml`
- [x] T003 [P] Create `.env.example` listing all required env vars: `VICTORIA_METRICS_URL`, `LOKI_URL`, `PROMETHEUS_URL`, `POSTGRES_DSN`, `REQUEST_TIMEOUT_SECONDS`, `CORRELATION_WINDOW_SECONDS` in `.env.example`
- [x] T004 [P] Add `reports/` and `.secrets/` to `.gitignore`; create `reports/.gitkeep` to track the output directory in `.gitignore` and `reports/.gitkeep`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that ALL user stories depend on. No story work can begin until this phase is complete.

**⚠️ CRITICAL**: Complete T005–T013 before starting any Phase 3+ task.

- [x] T005 Implement `src/n8n_analyzer/config.py`: load all settings from `.secrets/` env files and environment variables using `python-dotenv`; raise `ConfigError` with a clear message if any required variable is missing or any `.secrets/` file has permissions other than `640`; no credential values in log output
- [x] T006 [P] Implement `src/n8n_analyzer/collectors/base.py`: abstract `BaseCollector` with `httpx.AsyncClient`, configurable timeout (default 30 s), one-retry on transient failure, `PartialDataError` exception class used for partial report mode
- [x] T007 [P] Create all `__init__.py` files for every sub-package under `src/n8n_analyzer/` (models, collectors, analyzers, labels, reporters) to make the package importable
- [x] T008 [P] Implement all four Pydantic v2 data models in `src/n8n_analyzer/models/`:
  - `src/n8n_analyzer/models/latency_event.py` — `LatencyEvent` (workflow_id, workflow_name, node_name, node_type, executed_at: datetime UTC, duration_seconds: float, source_host: str)
  - `src/n8n_analyzer/models/correlation_window.py` — `CorrelationWindow` (center_ts: datetime UTC, window_seconds: int, events: list[LatencyEvent])
  - `src/n8n_analyzer/models/infra_metric.py` — `InfraMetricSnapshot` (metric_name, value: float, timestamp: datetime UTC, source_label: str)
  - `src/n8n_analyzer/models/report.py` — `PerformanceReport` (analysis_id: Literal["ANA-001"], time_range_from, time_range_to, generated_at, latency_events, infra_snapshots, geographic_breakdown, severity_summary, findings: list[Finding]); `Finding` (root_cause_label: RootCauseLabel, evidence: list[InfraMetricSnapshot], description: str)
- [x] T009 Implement `src/n8n_analyzer/collectors/victoria_metrics.py`: `VictoriaMetricsCollector(BaseCollector)` with `query_range(promql, start, end, step)` method calling `/api/v1/query_range`; returns list of `(labels_dict, timestamps, values)` tuples; host-label grouping by `instance` label
- [x] T010 Implement `src/n8n_analyzer/collectors/loki.py`: `LokiCollector(BaseCollector)` with `query_range(logql, start, end)` method calling `/loki/api/v1/query_range`; returns list of log lines with timestamps; raises `PartialDataError` on connection failure (not SystemExit)
- [x] T011 [P] Implement `src/n8n_analyzer/labels/root_cause.py`: `RootCauseLabel` enum (`QUEUE_DEPTH_SPIKE`, `DB_SLOW_QUERY`, `EXTERNAL_API_TIMEOUT`, `NETWORK_LATENCY`, `N8N_INTERNAL_ERROR`, `UNKNOWN`) and stub `classify(event: LatencyEvent, snapshots: list[InfraMetricSnapshot]) -> RootCauseLabel` returning `UNKNOWN` for now (filled in Phase 4)
- [x] T012 Build CLI skeleton in `src/n8n_analyzer/cli.py` using `click`: `@click.command()` with options `--from` (ISO-8601), `--to` (ISO-8601), `--output-format` (choice: markdown, json; default: markdown), `--step-global` (default: 5m), `--step-drilldown` (default: 1m), `--output-dir` (default: reports/); validate date range and load config at startup; exit 1 with clear message on `ConfigError`
- [x] T013 Create entry-point script `scripts/analyze_n8n_performance.py`: single-file shim that calls `from n8n_analyzer.cli import main; main()`; include comment `# ANA-001 N8N Performance Analyzer` at the top of the file

**Checkpoint**: `python scripts/analyze_n8n_performance.py --help` must list all CLI options without error.

---

## Phase 3: User Story 1 — Full Latency Analysis (Priority: P1) 🎯 MVP

**Goal**: Query `n8n_node_execution_duration_seconds` from VictoriaMetrics, compute p50/p95/p99 per node per workflow, flag violations ≥ 1 s, auto zoom-in on spike windows with 1 m step, and produce a Markdown or JSON report in `reports/`.

**Independent Test**: Run `python scripts/analyze_n8n_performance.py --from 2026-01-01 --to 2026-03-17 --output-format markdown --output-dir reports/` and verify a non-empty `.md` report file is created in `reports/` containing p95 latency values and at least one `## Latency Violations` section (or `No violations found` if data is clean).

- [x] T014 [US1] Implement latency analyzer in `src/n8n_analyzer/analyzers/latency.py`: `LatencyAnalyzer` class with `analyze(start, end, step_global, step_drilldown) -> list[LatencyEvent]`; queries `histogram_quantile(0.50|0.95|0.99, rate(n8n_node_execution_duration_seconds_bucket[...]))` from VictoriaMetrics; converts results to `LatencyEvent` objects; flags events where p95 ≥ 1.0 s (FR-002, FR-003)
- [x] T015 [US1] Add spike window detection and drill-down re-query to `LatencyAnalyzer.analyze()`: after global scan, identify time windows containing flagged events, re-query those windows at `step_drilldown` (1 m) step to produce higher-resolution `LatencyEvent` list (FR-001) in `src/n8n_analyzer/analyzers/latency.py`
- [x] T016 [P] [US1] Implement `MarkdownReporter` in `src/n8n_analyzer/reporters/markdown.py`: `render(report: PerformanceReport) -> str` producing a report with sections: `# N8N Performance Report ANA-001`, `## Summary`, `## Latency Violations`, `## Findings`; each finding includes root-cause label + evidence table; no prescriptive fix commands (FR-008, FR-013)
- [x] T017 [P] [US1] Implement `JsonReporter` in `src/n8n_analyzer/reporters/json_reporter.py`: `render(report: PerformanceReport) -> str` serializing the `PerformanceReport` Pydantic model to JSON with ISO-8601 timestamps; same section structure as Markdown (FR-008)
- [x] T018 [US1] Implement partial report mode in both reporters: when a section's data is a `PartialDataError`, render `DATA UNAVAILABLE: <reason>` in that section body; emit `WARNING: <reason>` to stderr; report exit code remains 0; VictoriaMetrics unavailability propagates as SystemExit(1) (FR-014) in `src/n8n_analyzer/reporters/markdown.py` and `src/n8n_analyzer/reporters/json_reporter.py`
- [x] T019 [US1] Implement report filename generator in `src/n8n_analyzer/reporters/__init__.py`: function `build_filename(from_dt, to_dt, fmt) -> str` returning `n8n_perf_ANA001_<FROM>_<TO>_<GENERATED_AT>.<ext>` (FR-007)
- [x] T020 [US1] Wire US1 pipeline into CLI: `cli.py` orchestrates `LatencyAnalyzer.analyze()` → `PerformanceReport` construction → reporter selection → file write to `--output-dir` in `src/n8n_analyzer/cli.py`

**Checkpoint**: Full Latency Analysis works end-to-end; report file saved to `reports/`; `--output-format json` also produces valid JSON output.

---

## Phase 4: User Story 2 — Infrastructure Correlation (Priority: P2)

**Goal**: For each detected latency violation, query Redis queue depth, PostgreSQL query duration, and external API response times within ±30 s; assign a structured root-cause label from the taxonomy; append "Queue Latency", "Infrastructure Correlation", and "Error Log Summary" sections to the report.

**Independent Test**: Run the correlation module standalone with the mock fixture: `python -c "from n8n_analyzer.analyzers.correlation import CorrelationAnalyzer; ..."` and verify the returned `InfraMetricSnapshot` list is non-empty and at least one `Finding` carries a label other than `UNKNOWN`.

- [x] T021 [P] [US2] Implement `CorrelationAnalyzer` in `src/n8n_analyzer/analyzers/correlation.py`: for each `CorrelationWindow`, query VictoriaMetrics for `redis_list_length` (queue depth), `pg_stat_activity_max_tx_duration` (DB query duration ≥ 500 ms), and `external_api_response_seconds` (external API p95 > 2 s) over the window; return list of `InfraMetricSnapshot` (FR-004); raise `PartialDataError` per missing source (FR-014)
- [x] T022 [P] [US2] Implement `LokiAnalyzer` in `src/n8n_analyzer/analyzers/loki_analyzer.py`: query Loki with LogQL `{container=~"n8n.*"} |= "ERROR"` for the full analysis range; return error count, top-N error types by frequency, and list of error entries co-occurring within ±30 s of a `LatencyEvent` (FR-012); raise `PartialDataError` on Loki unreachable
- [x] T023 [US2] Implement root-cause classification logic in `src/n8n_analyzer/labels/root_cause.py`: fill `classify(event, snapshots, log_errors)` method: map `redis_list_length` spike → `QUEUE_DEPTH_SPIKE`, DB duration ≥ 500 ms → `DB_SLOW_QUERY`, external API p95 > 2 s → `EXTERNAL_API_TIMEOUT`, co-occurring Loki error → `N8N_INTERNAL_ERROR`, no evidence → `UNKNOWN`; label must be supported by at least one snapshot or log entry (SC-008)
- [x] T024 [US2] Add "Queue Latency", "Infrastructure Correlation" sections to `MarkdownReporter.render()` in `src/n8n_analyzer/reporters/markdown.py`; each section rendered per violation with evidence table; `DATA UNAVAILABLE` rendered if source raised `PartialDataError`
- [x] T025 [US2] Add "Error Log Summary" section to `MarkdownReporter.render()` in `src/n8n_analyzer/reporters/markdown.py`: total error count, top-3 error types with frequency, timestamps of errors co-occurring with latency violations (SC-007)
- [x] T026 [US2] Add correlation sections ("Queue Latency", "Infrastructure Correlation", "Error Log Summary") to `JsonReporter.render()` in `src/n8n_analyzer/reporters/json_reporter.py` maintaining same structure as Markdown
- [x] T027 [US2] Wire correlation + Loki analysis into CLI pipeline in `src/n8n_analyzer/cli.py`: after `LatencyAnalyzer.analyze()`, build `CorrelationWindow` list, run `CorrelationAnalyzer` and `LokiAnalyzer`, call `RootCauseClassifier.classify()` per event, update `PerformanceReport.findings`

**Checkpoint**: Report "Infrastructure Correlation" section populated; at least one finding has a root-cause label other than `UNKNOWN` when Redis/DB metrics are available.

---

## Phase 5: User Story 3 — Geographic Latency Separation (Priority: P3)

**Goal**: Separate all metrics by source host (`instance` label: wf001 vs wf008); estimate and subtract the wf001→wf008 network RTT contribution; render a "Geographic Analysis" section with per-host sub-rows and a "network contribution" estimate.

**Independent Test**: Run the analyzer with both hosts as sources; verify the report contains a `## Geographic Analysis` section with separate rows labelled `wf001.vya.digital` and `wf008.vya.digital`; verify the "network contribution" field is present and numeric.

- [x] T028 [P] [US3] Implement `GeographicAnalyzer` in `src/n8n_analyzer/analyzers/geographic.py`: split `LatencyEvent` list by `source_host` into two groups (wf001, wf008); compute p50/p95/p99 per group; return dict `{host: GeographicBreakdown}` where `GeographicBreakdown` holds the per-host percentile stats (FR-005)
- [x] T029 [US3] Implement RTT-baseline estimator in `src/n8n_analyzer/analyzers/geographic.py`: query VictoriaMetrics `probe_duration_seconds` (blackbox exporter) or derive from wf008 vs wf001 p50 delta as a baseline proxy; compute `network_contribution_seconds = wf008_p50 - wf001_p50`; store in `GeographicBreakdown` (US3 acceptance scenario 2)
- [x] T030 [US3] Extend `VictoriaMetricsCollector.query_range()` to accept optional `label_filter: dict` for adding `instance=~"wf001.*|wf008.*"` selector; returns results grouped by `instance` label in `src/n8n_analyzer/collectors/victoria_metrics.py`
- [x] T031 [US3] Add `## Geographic Analysis` section to `MarkdownReporter.render()` in `src/n8n_analyzer/reporters/markdown.py`: separate metric tables per source host, "network contribution" row, and residual "application latency" row
- [x] T032 [US3] Add `geographic_analysis` key to `JsonReporter.render()` output in `src/n8n_analyzer/reporters/json_reporter.py`
- [x] T033 [US3] Wire geographic analysis into CLI pipeline in `src/n8n_analyzer/cli.py`: after latency analysis, pass events into `GeographicAnalyzer` and attach result to `PerformanceReport.geographic_breakdown`

**Checkpoint**: Report `## Geographic Analysis` section present; `network_contribution_seconds` and `application_latency_seconds` fields populated; each metric row labelled by host.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Hardening, reproducibility, and final validation across all user stories.

- [x] T034 [P] Add `--dry-run` flag to CLI in `src/n8n_analyzer/cli.py`: print resolved config (without credential values) and exit 0 — useful for validating `.secrets/` setup before a live run
- [x] T035 [P] Move `.secrets/` permission check into startup sequence in `src/n8n_analyzer/config.py`: iterate every file under `.secrets/` and emit `ConfigError` listing files with permissions ≠ `640`
- [x] T036 [P] Set `SC-005` determinism: ensure `PerformanceReport` serialization excludes `generated_at` from equality checks; sort all lists deterministically (by `executed_at` then `source_host`) in `src/n8n_analyzer/models/report.py`
- [x] T037 Add `utc` validation to all `datetime` fields in Pydantic models: custom `@field_validator` that raises if `tzinfo` is None or not UTC in `src/n8n_analyzer/models/latency_event.py`, `infra_metric.py`, `report.py`
- [x] T038 Run end-to-end dry-run validation: `python scripts/analyze_n8n_performance.py --dry-run` completes without error; `python scripts/analyze_n8n_performance.py --help` shows all options; `pip install -e .` installs the package cleanly
- [x] T039 Benchmark report generation for SC-001: run `time python scripts/analyze_n8n_performance.py --from 2026-01-01 --to 2026-01-31 --output-dir /tmp/bench/` and assert total elapsed time is < 5 minutes; document result in a comment at top of `reports/.gitkeep` or in `docs/` if CI is unavailable (SC-001)
- [x] T040 [P] [US1] Add `## Appendix: Queries` section to `MarkdownReporter.render()` in `src/n8n_analyzer/reporters/markdown.py` and a `queries` key to `JsonReporter.render()` in `src/n8n_analyzer/reporters/json_reporter.py`; each entry MUST list: PromQL/LogQL expression used, step value, time range (from/to), and data source URL — satisfying Constitution Principle IV (Reproducible Analysis)

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    └── Phase 2 (Foundational)  ← blocks everything below
            ├── Phase 3 (US1 — P1) 🎯 MVP
            ├── Phase 4 (US2 — P2)  [requires Phase 3 complete]
            ├── Phase 5 (US3 — P3)  [requires Phase 3 complete; independent from US2]
            └── Phase 6 (Polish)    [requires Phase 3 complete; best after all stories done]
```

### User Story Dependencies

| Story | Depends On | Can Parallelize With |
|-------|------------|----------------------|
| US1 (P1) | Phase 2 complete | — (first story) |
| US2 (P2) | Phase 2 + US1 complete | US3 after T028 |
| US3 (P3) | Phase 2 + US1 complete | US2 after T021 |

### Within Each User Story

- Foundation (Phase 2) tasks before any story task
- Within a story: models → collectors → analyzers → reporters → CLI wire-up
- `[P]` tasks within each phase can be started simultaneously

---

## Parallel Execution Examples

### Phase 2: Run in parallel after T005

```bash
# Terminal 1
git checkout -b feat/foundation-collectors
# Implement T006, T009, T010

# Terminal 2
git checkout -b feat/foundation-models
# Implement T007, T008, T011
```

### Phase 3 (US1): Run in parallel after T015

```bash
# Terminal 1 — reporters
# Implement T016 (MarkdownReporter), T018, T019

# Terminal 2 — JSON reporter
# Implement T017 (JsonReporter)
```

### Phase 4+5: Run in parallel after Phase 3 complete

```bash
# Terminal 1 — US2
# Implement T021–T027

# Terminal 2 — US3
# Implement T028–T033
```

---

## Implementation Strategy

### MVP Scope (US1 only — Phases 1–3)

Complete T001–T020 to deliver:
- `scripts/analyze_n8n_performance.py` executable
- `pip install -e .` installs the `analyze-n8n` command
- Latency violation report (Markdown + JSON) generated for any date range
- Partial mode for missing secondary sources
- Exit code 1 on VictoriaMetrics unavailability

US2 and US3 are layered onto the MVP without breaking it.

### Incremental Delivery

| Increment | Tasks | Deliverable |
|-----------|-------|-------------|
| 1 — MVP | T001–T020 | Full latency report, CLI, pip install |
| 2 — Correlation | T021–T027 | Root-cause labels + infra correlation section |
| 3 — Geography | T028–T033 | Geographic analysis section |
| 4 — Polish | T034–T040 | Hardened, deterministic, fully validated, SC-001 benchmarked |
