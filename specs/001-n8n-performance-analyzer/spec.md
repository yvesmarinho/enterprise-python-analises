# Feature Specification: N8N Performance Analyzer

**Feature Branch**: `001-n8n-performance-analyzer`  
**Created**: 2026-03-17  
**Status**: Draft  
**Analysis Registry**: ANA-001  
**Input**: User description: "gerar códigos python (preferencialmente) para analisar os dados de desempenho do serviço N8N em container. o resultado deve ser um reporte apontando todos os itens que causam lentidão nos workflow, seja hardware ou software."

## Context

This feature is part of **ANA-001 · N8N Performance Latency** (see `constitution.md`).
The N8N service is running in queue-mode (3 workers, 3 webhooks, 1 editor, 1 MCP) on
`wf001.vya.digital` (US East). A latency problem — each workflow step taking ≥ 1 second —
has been reported since January 2026. Metrics are already being collected by `prod-collector-api`
and published to the Enterprise Observability Stack (Prometheus, VictoriaMetrics, Grafana).

The goal is to produce a **Python analysis toolset** that queries existing observability
data and generates a structured performance report identifying root causes of slowness,
covering both infrastructure-level (hardware) and service-level (software) factors.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Full Latency Analysis (Priority: P1)

A senior engineer responsible for N8N operations wants to run the analyzer from the
command line, provide a time range, and receive a complete report that identifies which
workflow nodes are slow, when spikes occurred, and what correlated with them — all
without having to write any PromQL queries manually.

**Why this priority**: This is the core deliverable. Without it, the latency investigation
cannot proceed systematically. Every other story depends on having this baseline analysis.

**Independent Test**: Run `python scripts/analyze_n8n_performance.py --from 2026-01-01
--to 2026-03-17 --output reports/` and verify a non-empty report is generated that
includes at least one workflow with p95 node execution time, even in a mock/test data mode.

**Acceptance Scenarios**:

1. **Given** the observability stack is reachable and metric data exists for the requested period,  
   **When** the engineer runs the analyzer with a `--from` / `--to` date range,  
   **Then** a report is generated in `reports/` listing slow nodes (p95 ≥ 1s), occurrence timestamps, and severity.

2. **Given** no metric data exists for a requested period,  
   **When** the analyzer is run,  
   **Then** it exits gracefully with a clear message indicating the empty data range, without crashing.

3. **Given** the observability stack is unreachable,  
   **When** the analyzer is run,  
   **Then** it exits with a non-zero code and a human-readable connection error message.

---

### User Story 2 - Infrastructure Correlation Report (Priority: P2)

The engineer wants to know whether the N8N slowness correlates with host-level or
middleware-level events — such as Redis queue depth spikes, PostgreSQL query slowness,
high container CPU/memory pressure, or external API (Chatwoot, Evolution API) latency.

**Why this priority**: The problem statement explicitly excludes CPU/memory as primary
cause, but correlation is needed to rule them out definitively and point to the real
culprit. This transforms a symptom report into a root-cause report.

**Independent Test**: Run the correlation module standalone with mock metric data for
Redis, PostgreSQL, and external API response times; verify the output section
"Infrastructure Correlation" contains entries with correlation score and time offset.

**Acceptance Scenarios**:

1. **Given** Redis queue depth metrics are available,  
   **When** the analyzer runs the correlation phase,  
   **Then** the report includes a "Queue Latency" section showing queue depth at the time of each N8N latency spike.

2. **Given** PostgreSQL query duration metrics are available,  
   **When** the analyzer runs the correlation phase,  
   **Then** the report flags any DB query exceeding 500ms that occurred within ±30 seconds of an N8N latency event.

3. **Given** external API metrics (Chatwoot, WhatsApp) are available,  
   **When** the analyzer runs the correlation phase,  
   **Then** the report includes response time statistics for each external service, flagged if p95 > 2s.

---

### User Story 3 - Geographic Latency Separation (Priority: P3)

The engineer wants to understand whether the workflow slowness is a network latency
artefact caused by the Brazil (wf008) probe measuring US East (wf001) services, or a
genuine application-layer delay on the server itself.

**Why this priority**: wf008 is a Brazil-based latency probe. Without separating its
measurements from wf001's local observations, a network delay could be misattributed
as an application bottleneck.

**Independent Test**: Run the analyzer with both wf001 and wf008 as sources; verify
the output report contains a "Geographic Analysis" section with separate metric rows
per source host, and a computed "network contribution" estimate.

**Acceptance Scenarios**:

1. **Given** metrics from both wf001 (US East) and wf008 (Brazil) are available,  
   **When** the analyzer runs,  
   **Then** the report clearly labels each metric by source host and presents them in separate subsections.

2. **Given** the average Brazil→US RTT baseline is measurable from probe data,  
   **When** the report is generated,  
   **Then** it subtracts the network contribution and reports the residual as "application latency".

---

### Edge Cases

- Metric data exists for only part of the requested date range — analyzer should process what is available and note the gap.
- A workflow has zero executions in the range — it should be omitted from the report, not cause an error.
- VictoriaMetrics returns partial results due to retention limits — the report should state the actual available range.
- Credentials in `.secrets/` are missing or malformed — the analyzer exits with a clear config error before making any network requests.
- Time-zone mismatch between local system and metric timestamps — all queries and output MUST use UTC.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The analyzer MUST accept `--from` and `--to` date parameters (ISO-8601, UTC) and query only that time range.
- **FR-002**: The analyzer MUST query `n8n_node_execution_duration_seconds` from VictoriaMetrics and compute p50, p95, and p99 per node per workflow.
- **FR-003**: The analyzer MUST flag any node where p95 execution time ≥ 1 second as a latency violation.
- **FR-004**: The analyzer MUST correlate N8N latency events with Redis queue depth, PostgreSQL query duration, and external API response times within a configurable time window (default ±30s).
- **FR-005**: The analyzer MUST separate metrics by source host (`wf001` vs `wf008`) and label them accordingly in all output.
- **FR-006**: The analyzer MUST load all credentials and endpoint URLs from `.secrets/` or environment variables — no hardcoded values.
- **FR-007**: The analyzer MUST generate a structured report in `reports/` with a filename including the analysis date range and a timestamp.
- **FR-008**: The analyzer MUST include an `--output-format` option supporting at least `markdown` (default) and `json`.
- **FR-009**: All network requests to observability endpoints MUST have a configurable timeout (default 30s) and retry once on failure before aborting.
- **FR-010**: The analyzer MUST be executable without modifying any production service, container, or database.

### Key Entities

- **LatencyEvent**: A single N8N node execution that exceeded the 1-second threshold. Attributes: workflow ID, workflow name, node name, node type, execution timestamp (UTC), duration (seconds), source host.
- **CorrelationWindow**: A time interval around a LatencyEvent used to query correlated infrastructure metrics. Attributes: center timestamp, window size, associated LatencyEvents.
- **InfraMetricSnapshot**: A point-in-time reading of an infrastructure metric (Redis queue depth, DB query duration, external API latency). Attributes: metric name, value, timestamp, source label.
- **PerformanceReport**: The final output artifact. Attributes: analysis ID (ANA-001), time range, generation timestamp, list of LatencyEvents, correlated InfraMetricSnapshots, geographic breakdown, severity summary, recommendations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The report is generated within 5 minutes for a 30-day analysis window on the existing observability stack.
- **SC-002**: Every workflow node in the N8N cluster with at least one execution in the analysis period appears in the report (either clean or flagged).
- **SC-003**: The correlation section correctly identifies infrastructure events co-occurring with ≥ 80% of flagged latency violations, when such data is available.
- **SC-004**: The report unambiguously identifies at least one root-cause category (queue delay, DB slowness, external API delay, or geographic network latency) for each flagged workflow.
- **SC-005**: Running the analyzer twice with identical parameters produces a byte-for-byte identical report body (excluding generation timestamp).
- **SC-006**: All credentials are sourced from `.secrets/` — a `git diff` of the output report must contain zero credential strings.

## Assumptions

- VictoriaMetrics is configured with ≥ 12-month retention; data from January 2026 is available.
- `prod-collector-api` on both wf001 and wf008 is actively pushing metrics to the Pushgateway at the time of analysis.
- The `monitor_user` read-only PostgreSQL account on wfdb02 is accessible for query duration metrics.
- Redis metrics are available via the existing collector (queue depth exposed as a standard metric).
- External API metrics (Chatwoot, Evolution API) are exposed via `prod-collector-api` response-time histograms.
- The analysis is run from the engineer's local machine, not from a production server.
- Python 3.11+ is available in the local analysis environment.
