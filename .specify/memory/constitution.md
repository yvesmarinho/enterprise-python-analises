<!--
SYNC IMPACT REPORT
==================
Version change: 1.0.0 → 1.1.0
Bump rationale: MINOR — new section "Analysis Registry" added; Principle III
  materially expanded with .secrets/ structure and permission model; Principle V
  refactored from N8N-specific to general multi-analysis scope discipline.
Modified principles:
  - III. Security & Secrets Management → expanded with .secrets/ structure, permissions, rotation
  - V. Data Integrity & Scope Discipline → generalized for multi-analysis; N8N scope moved to Analysis Registry
Added sections:
  - Analysis Registry (active and future analyses with their scope boundaries)
Removed sections: none
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ Constitution Check gate VI added for secrets
  - .specify/templates/spec-template.md ✅ no structural changes required
  - .specify/templates/tasks-template.md ✅ no structural changes required
Follow-up TODOs:
  - TODO(WF008_CONTAINERS): Document active containers on wf008 (Brazil) — currently unknown
  - TODO(WF008_DOCKER): Add docker_user, docker_folder, docker_version for wf008
  - TODO(SECRETS_CLIENTS): Document contents/purpose of .secrets/clients/ subfolder
  - TODO(CREDENTIALS_FILLED): Verify .secrets/CREDENTIALS_FILLED.md contains no real credentials (15KB file)
  - TODO(SECRETS_PERMISSIONS): Several .secrets/ files have 664 permissions (should be 640 per .secrets/README.md)
  - TODO(N8N_QUEUE_BROKER): Confirm RabbitMQ vs Redis as the sole N8N queue broker
  - TODO(WF008_COLLECTOR): Validate prod-collector-api on wf008 pushes to same Pushgateway as wf001
-->

# Enterprise Python Analysis Constitution

## Core Principles

### I. Production Safety (NON-NEGOTIABLE)

All scripts and automation targeting production servers MUST be read-only by default.
No action that could interrupt a running service is permitted between **08:00 and 20:30
BRT/ET**. Container restarts, configuration changes, or service modifications on any
production host MUST only be executed outside the restricted window. Any script that
writes to or restarts a production container MUST carry an explicit `# PRODUCTION WRITE`
comment and require manual confirmation before execution.

**Rationale**: Production services serve real customers. Unplanned downtime impacts
revenue-critical workflows. The time window restriction protects business hours across
time zones (US East + Brazil).

### II. Observability-First

All analysis work MUST use data sourced from the Enterprise Observability Stack
(Prometheus at `https://prometheus.vya.digital`, VictoriaMetrics with 12-month
retention, Grafana at `https://grafana.vya.digital`). Direct ad-hoc queries to
production databases (wfdb02) are only permitted via the `prod-collector-api`
instrumented path or the `monitor_user` read-only database account. Every analysis
finding MUST reference the specific metric name, time range, and data source used.

**Rationale**: Reproducibility and auditability require that findings are tied to
observable, queryable data — not one-off manual inspections that cannot be re-run.

### III. Security & Secrets Management

Credentials, API keys, and SSH passphrases MUST NOT be hardcoded in any file tracked
by git. All secrets MUST reside exclusively in `.secrets/`, which MUST be excluded from
version control via `.gitignore` (confirmed entry at line 16 of root `.gitignore`).

**`.secrets/` structure and rules**:
- Credential files: `*.txt`, `.env.production`, and `CREDENTIALS_*.md` — never commit
- Client-specific secrets: `.secrets/clients/` — same exclusion rules apply
- Internal `.gitignore` inside `.secrets/` provides a second layer of protection
- File permissions MUST be `640` (owner read/write, group read only); `664` is a violation
- Owner MUST be `root:docker` on production hosts; local dev: `$USER:$USER` is acceptable
- Rotation cadence: passwords MUST be rotated every 90 days per `.secrets/README.md`

SSH access to all production servers (wf001, wf008, wfdb02, wfdb01) MUST use SPA
(Single Packet Authorization) via `fwknop`. Credentials MUST never appear in log output,
terminal history exports, or doc files tracked by git.

**Rationale**: The infrastructure spans multiple production VPS servers holding customer
data. A single leaked credential across any of the documented services (PostgreSQL,
Grafana, AlertManager, Evolution API) could compromise the entire stack.

### IV. Reproducible Analysis

Every analysis script MUST be version-controlled in this repository under `scripts/`.
Scripts MUST accept explicit time-range parameters and MUST NOT rely on implicit "now".
Output files MUST include the metric source, query used, and time range in their
header or filename. Analysis results stored under `reports/` MUST be reproducible by
re-running the corresponding script with the same parameters.

Each analysis track MUST have an entry in the **Analysis Registry** section below,
linking to its objective document and defining its scope boundary.

**Rationale**: Multiple concurrent analyses on shared infrastructure require clear
provenance. Findings must be comparable over time and attributable to specific data
sources and queries.

### V. Data Integrity & Scope Discipline

Each analysis MUST operate strictly within the scope defined in its Analysis Registry
entry. Cross-contamination between analysis tracks (e.g., mixing N8N latency data with
database performance data) is prohibited unless a correlation is explicitly declared in
the finding report.

All collected data MUST be timestamped in ISO-8601 format. When an analysis uses
collectors deployed in multiple geographic regions (e.g., wf001 US East and wf008
Brazil), metrics MUST be labelled by source host. Geographic latency contributions MUST
be documented separately and not attributed to the service under analysis.

**Rationale**: This project hosts multiple independent analyses. Scope discipline
prevents findings from one analysis contaminating another and ensures geographic
network latency is not misattributed as application-level latency.

## Analysis Registry

This section is the authoritative list of all analysis tracks in this project.
Each new analysis MUST be registered here before work begins.

### ANA-001 · N8N Performance Latency

| Field            | Value |
|------------------|-------|
| **Status**       | Active |
| **Started**      | 2026-01-xx (reported) / 2026-03-17 (formal analysis) |
| **Objective doc**| `docs/obejetivo_analises.md` |
| **Scope**        | Workflow step execution latency in N8N v2.6.4 on wf001 |
| **Out of scope** | CPU/memory consumption, database sizing, infrastructure capacity |
| **Target host**  | wf001.vya.digital (31.220.103.208) + wf008 as latency probe |
| **Primary metric**| `n8n_node_execution_duration_seconds` |
| **Threshold**    | p95 > 1.0 s per node execution = confirmed latency event |
| **Queue broker** | Redis (broker confirmed); RabbitMQ used by related workflow services |
| **Database**     | PostgreSQL 16.10 on wfdb02.vya.digital |
| **Connections**  | Chatwoot (chat-vya-digital), WhatsApp (evolution_api_wea004) |
| **N8N URL**      | `https://workflow.vya.digital` |
| **Reports dir**  | `reports/` (date-stamped filenames) |

**Analysis workflow**:
1. Query Prometheus/VictoriaMetrics for `n8n_node_execution_duration_seconds` from
   January 2026 → present
2. Compare against pre-January/2026 baseline (VictoriaMetrics 12-month retention)
3. Correlate spikes with: Redis queue depth, PostgreSQL query duration,
   Chatwoot and Evolution API response times
4. Document findings with metric source + PromQL query + time range
5. Any configuration or version change (e.g., N8N upgrade from v2.6.4) MUST be
   proposed with a documented rollback plan before execution after 20:30

### ANA-002 · [Future Analysis]

TODO: Register next analysis here when work begins.

## Operational Constraints

### Infrastructure Inventory

| Server | Role                | Region       | Key Services                           |
|--------|---------------------|--------------|----------------------------------------|
| wf001  | N8N + App host      | US East (NY) | N8N queue-mode, Redis, RabbitMQ        |
| wf008  | Collector (mirror)  | Brazil (SP)  | prod-collector-api (latency probe)     |
| wfdb01 | Observability stack | US East (NY) | Prometheus, VictoriaMetrics, Grafana   |
| wfdb02 | Database server     | US East (NY) | PostgreSQL 16.10 (N8N DB), MySQL 8.4.6 |

### Maintenance Window

- **Allowed anytime**: read-only data collection, metric queries, log inspection
- **Restricted (08:00–20:30)**: any container restart, configuration change, service
  interruption on any production host
- **Allowed after 20:30**: container modifications, configuration tuning, version upgrades

### Secrets Inventory Summary

| Location | Type | Git-excluded |
|----------|------|--------------|
| `.secrets/*.txt` | Service passwords/keys | ✅ via root `.gitignore` |
| `.secrets/.env.production` | Runtime env vars | ✅ via root `.gitignore` |
| `.secrets/CREDENTIALS_*.md` | Credential docs | ✅ via root `.gitignore` |
| `.secrets/clients/` | Client-specific secrets | ✅ via root `.gitignore` |
| `.secrets/.gitignore` | Inner safety net | ✅ self-excluding |

## Script Conventions

- Scripts live in `scripts/`; output reports go to `reports/`
- Metric queries use PromQL/MetricsQL and MUST be documented inline
- No script may call `docker restart` or equivalent without an explicit `--dry-run` guard
- Scripts MUST load secrets from `.secrets/` and MUST NOT prompt for credentials at runtime
- Each script MUST declare at the top: analysis track ID (e.g., `# ANA-001`), time range
  parameters, and data source

## Governance

This Constitution supersedes all informal practices for the `enterprise-python-analysis`
project. Amendments require:
1. A documented rationale for the change
2. A version bump following semantic versioning:
   - **MAJOR**: removal or redefinition of a principle
   - **MINOR**: new principle, new section, or material content expansion
   - **PATCH**: wording clarification, typo fix, non-semantic refinement
3. Update of `LAST_AMENDED_DATE` on the version line below
4. Propagation check across all templates in `.specify/templates/`
5. New analysis tracks MUST be registered in the Analysis Registry before work begins

All analysis plans generated by Speckit agents MUST pass all Constitution Check gates
in `plan-template.md` before proceeding to implementation. Runtime guidance is in
`docs/Prometheus/PROMETHEUS_SETUP.md` and `docs/N8N/debug_information.txt`.

**Version**: 1.1.0 | **Ratified**: 2026-03-17 | **Last Amended**: 2026-03-17
