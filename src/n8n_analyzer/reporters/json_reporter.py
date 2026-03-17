"""JsonReporter — render PerformanceReport as a JSON document.

Serializes the Pydantic PerformanceReport model to JSON with ISO-8601 timestamps.
Partial-mode sections appear with {"status": "DATA_UNAVAILABLE", "reason": "..."}.
No prescriptive fix commands are emitted (FR-013).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from n8n_analyzer.models.report import PerformanceReport


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


class JsonReporter:
    """Render a PerformanceReport to a JSON string."""

    def render(self, report: "PerformanceReport") -> str:
        doc: dict[str, Any] = {
            "analysis_id": report.analysis_id,
            "generated_at": _iso(report.generated_at),
            "time_range": {
                "from": _iso(report.time_range_from),
                "to": _iso(report.time_range_to),
            },
            "severity_summary": {
                "total_violations": report.severity_summary.total_violations,
                "total_clean_nodes": report.severity_summary.total_clean_nodes,
                "distinct_workflows_affected": report.severity_summary.distinct_workflows_affected,
                "distinct_node_types_affected": report.severity_summary.distinct_node_types_affected,
            },
            "latency_violations": [
                {
                    "workflow_id": e.workflow_id,
                    "workflow_name": e.workflow_name,
                    "node_name": e.node_name,
                    "node_type": e.node_type,
                    "executed_at": _iso(e.executed_at),
                    "duration_seconds": e.duration_seconds,
                    "source_host": e.source_host,
                    "status": e.status,
                }
                for e in report.violations()
            ],
            "clean_nodes": [
                {
                    "workflow_id": e.workflow_id,
                    "workflow_name": e.workflow_name,
                    "node_name": e.node_name,
                    "node_type": e.node_type,
                    "executed_at": _iso(e.executed_at),
                    "duration_seconds": e.duration_seconds,
                    "source_host": e.source_host,
                    "status": e.status,
                }
                for e in report.clean_nodes()
            ],
            "findings": [
                {
                    "root_cause_label": f.root_cause_label.value,
                    "description": f.description,
                    "related_workflow_ids": f.related_workflow_ids,
                    "evidence": [
                        {
                            "metric_name": s.metric_name,
                            "value": s.value,
                            "timestamp": _iso(s.timestamp),
                            "source_label": s.source_label,
                        }
                        for s in f.evidence
                    ],
                }
                for f in report.findings
            ],
            "queue_latency": self._queue_latency_section(report),
            "infrastructure_correlation": self._infra_correlation_section(report),
            "error_log_summary": self._error_log_section(report),
            "geographic_analysis": self._geographic_section(report),
            "queries": [
                {
                    "data_source": q.data_source,
                    "expression": q.expression,
                    "step": q.step,
                    "time_from": _iso(q.time_from),
                    "time_to": _iso(q.time_to),
                }
                for q in report.queries_executed
            ],
        }
        return json.dumps(doc, indent=2, ensure_ascii=False)

    # ── Partial-mode section builders ────────────────────────────────────────

    def _unavailable(self, section: str, reason: str) -> dict:
        print(f"WARNING: [{section}] {reason}", file=sys.stderr)
        return {"status": "DATA_UNAVAILABLE", "reason": reason}

    def _queue_latency_section(self, report: "PerformanceReport") -> Any:
        section = "Queue Latency"
        if section in report.unavailable_sections:
            return self._unavailable(section, report.unavailable_sections[section])
        redis_snaps = [
            s for s in report.infra_snapshots if "redis" in s.metric_name.lower()
        ]
        return [
            {
                "timestamp": _iso(s.timestamp),
                "metric_name": s.metric_name,
                "value": s.value,
                "source_label": s.source_label,
            }
            for s in sorted(redis_snaps, key=lambda s: s.timestamp)
        ]

    def _infra_correlation_section(self, report: "PerformanceReport") -> Any:
        section = "Infrastructure Correlation"
        if section in report.unavailable_sections:
            return self._unavailable(section, report.unavailable_sections[section])
        non_redis = [
            s for s in report.infra_snapshots if "redis" not in s.metric_name.lower()
        ]
        return [
            {
                "timestamp": _iso(s.timestamp),
                "metric_name": s.metric_name,
                "value": s.value,
                "source_label": s.source_label,
            }
            for s in sorted(non_redis, key=lambda s: s.timestamp)
        ]

    def _error_log_section(self, report: "PerformanceReport") -> Any:
        section = "Error Log Summary"
        if section in report.unavailable_sections:
            return self._unavailable(section, report.unavailable_sections[section])
        if report.loki_error_count is None:
            return None
        return {
            "total_errors": report.loki_error_count,
            "top_errors": report.loki_top_errors[:3],
        }

    def _geographic_section(self, report: "PerformanceReport") -> Any:
        section = "Geographic Analysis"
        if section in report.unavailable_sections:
            return self._unavailable(section, report.unavailable_sections[section])
        if not report.geographic_breakdown:
            return {}
        return {
            host: {
                "source_host": bd.source_host,
                "p50_seconds": bd.p50_seconds,
                "p95_seconds": bd.p95_seconds,
                "p99_seconds": bd.p99_seconds,
                "network_contribution_seconds": bd.network_contribution_seconds,
                "application_latency_seconds": bd.application_latency_seconds,
                "event_count": bd.event_count,
            }
            for host, bd in sorted(report.geographic_breakdown.items())
        }
