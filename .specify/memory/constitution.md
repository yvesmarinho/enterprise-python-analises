<!--
SYNC IMPACT REPORT
==================
Version change: (none) → 1.0.0  (initial ratification)
Modified principles: N/A (first fill from template)
Added sections:
  - Core Principles (I–V)
  - Operational Constraints
  - Analysis Workflow
  - Governance
Removed sections: none
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ Constitution Check gates aligned
  - .specify/templates/spec-template.md ✅ no structural changes required
  - .specify/templates/tasks-template.md ✅ no structural changes required
Follow-up TODOs:
  - Confirm whether RabbitMQ or Redis is the sole queue broker for N8N (currently documented as Redis=Broker, RabbitMQ=workflow services)
  - Validate that prod-collector-api on wf008 is publishing to the same Pushgateway as wf001
-->

# Enterprise Python Analysis Constitution

## Core Principles

### I. Production Safety (NON-NEGOTIABLE)

All scripts and automation targeting production servers MUST be read-only by default.
No action that could interrupt a running service is permitted between **08:00 and 20:30 BRT/ET**.
Container restarts, configuration changes, or service modifications on wf001 MUST only
be executed after 20:30. Any script that writes to or restarts a production container
MUST carry an explicit `# PRODUCTION WRITE` comment and require manual confirmation before execution.

**Rationale**: N8N is a revenue-critical service. Unplanned downtime directly impacts
customer-facing workflows (Chatwoot, WhatsApp). The time restriction protects business hours.

### II. Observability-First

All performance analysis MUST use data sourced from the Enterprise Observability Stack
(Prometheus at `https://prometheus.vya.digital`, VictoriaMetrics, Grafana at
`https://grafana.vya.digital`). Direct ad-hoc queries to production databases (wfdb02)
are only permitted via the `prod-collector-api` instrumented path or the `monitor_user`
read-only database account. Every analysis finding MUST reference the specific metric name,
time range, and data source used.

**Rationale**: Reproducibility and auditability require that findings be tied to
observable, queryable data — not one-off manual inspections.

### III. Security & Secrets Management

Credentials, API keys, and SSH passphrases MUST NOT be hardcoded in any file tracked by git.
All secrets MUST reside in `.secrets/` which is excluded from version control via `.gitignore`.
SSH access to all production servers (wf001, wf008, wfdb02, wfdb01) MUST use SPA (Single
Packet Authorization) via `fwknop`. Sharing or logging credentials in plain text is
prohibited.

**Rationale**: The infrastructure spans multiple production VPS servers with sensitive
customer data. A single leaked credential could compromise the entire stack.

### IV. Reproducible Analysis

Every analysis script MUST be version-controlled in this repository. Scripts MUST accept
explicit time-range parameters rather than using implicit "now". Output files MUST include
the metric source, query used, and time range in their header or filename. Analysis results
stored under `reports/` MUST be reproducible by re-running the corresponding script with
the same parameters.

**Rationale**: Diagnostic work on intermittent performance issues (latency since
January/2026) requires that findings can be validated, compared over time, and shared
with the team without ambiguity.

### V. Data Integrity & Scope Discipline

Analysis scope is strictly limited to **workflow execution latency** — specifically steps
taking ≥1 second in N8N v2.6.4 running in scaling mode on wf001. Resource consumption
(CPU, memory) is explicitly OUT OF SCOPE unless directly correlated to latency evidence.
All collected data MUST be timestamped with ISO-8601 format. Collected logs and metrics
from wf001 (US East) and wf008 (Brazil) MUST be clearly labelled by source host to avoid
cross-contamination of geographic latency data.

**Rationale**: Scope creep wastes analysis time. The problem is workflow step latency,
not infrastructure sizing. Keeping wf001 and wf008 data separated is critical because
wf008 measurements include Brazil↔US network latency by design.

## Operational Constraints

### Infrastructure Inventory

| Server   | Role                  | Region        | Key Services                          |
|----------|-----------------------|---------------|---------------------------------------|
| wf001    | N8N + App host        | US East (NY)  | N8N queue-mode, Redis, RabbitMQ       |
| wf008    | Collector (mirror)    | Brazil (SP)   | prod-collector-api (latency probe)    |
| wfdb01   | Observability stack   | US East (NY)  | Prometheus, VictoriaMetrics, Grafana  |
| wfdb02   | Database server       | US East (NY)  | PostgreSQL 16.10 (N8N DB), MySQL 8.4.6|

### Maintenance Window
- **Allowed anytime**: read-only data collection, metric queries, log inspection
- **Restricted (08:00–20:30)**: any container restart, configuration change, service interruption
- **Allowed after 20:30**: N8N container modifications, configuration tuning, version upgrades

### Key Metric Reference
Primary metric for latency analysis: `n8n_node_execution_duration_seconds`
(labels: `workflow_id`, `workflow_name`, `node_name`, `node_type`)
Threshold: p95 > 1.0 second per node execution = confirmed latency event.

## Analysis Workflow

### Phase Order
1. **Data Collection** — Query Prometheus/VictoriaMetrics for latency metrics in the
   affected period (January 2026 → present). Use `prod-collector-api` endpoints where
   available.
2. **Baseline Comparison** — Compare pre-January/2026 metrics (if retained in
   VictoriaMetrics, configured for 12-month retention) against current values.
3. **Correlation** — Correlate latency spikes with: Redis queue depth, PostgreSQL query
   duration, external API response times (Chatwoot, WhatsApp/Evolution API).
4. **Findings Report** — Document findings in `reports/` with metric sources, queries,
   and time ranges. Never modify production configuration based on hypothesis alone.
5. **Change Proposal** — Any configuration or version change (e.g., N8N upgrade from
   v2.6.4) MUST be documented as a proposal with rollback plan before execution.

### Script Conventions
- Scripts live in `scripts/`
- Output reports go to `reports/`
- Metric queries use PromQL/MetricsQL syntax and MUST be documented inline
- No script may call `docker restart` or equivalent without explicit `--dry-run` guard

## Governance

This Constitution supersedes all informal practices and ad-hoc decisions for the
`enterprise-python-analysis` project. Amendments require:
1. A documented rationale for the change
2. A version bump following semantic versioning:
   - **MAJOR**: removal or redefinition of a principle
   - **MINOR**: new principle or section added
   - **PATCH**: wording clarification, typo fix, non-semantic refinement
3. Update of `LAST_AMENDED_DATE` on the version line below
4. Propagation check across all templates in `.specify/templates/`

All analysis plans and implementation tasks generated by Speckit agents MUST pass the
Constitution Check gate defined in `plan-template.md` before proceeding to implementation.
Runtime development guidance is in `docs/Prometheus/PROMETHEUS_SETUP.md` and
`docs/N8N/debug_information.txt`.

**Version**: 1.0.0 | **Ratified**: 2026-03-17 | **Last Amended**: 2026-03-17
