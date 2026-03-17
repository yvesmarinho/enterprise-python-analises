"""PerformanceReport and Finding — the final output artifact for ANA-001."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, field_validator

from n8n_analyzer.labels.root_cause import RootCauseLabel
from n8n_analyzer.models.infra_metric import InfraMetricSnapshot
from n8n_analyzer.models.latency_event import LatencyEvent


class GeographicBreakdown(BaseModel):
    """Per-host latency percentile statistics."""

    source_host: str
    p50_seconds: float | None = None
    p95_seconds: float | None = None
    p99_seconds: float | None = None
    network_contribution_seconds: float | None = None
    application_latency_seconds: float | None = None
    event_count: int = 0


class Finding(BaseModel):
    """A single root-cause finding with supporting evidence."""

    root_cause_label: RootCauseLabel
    evidence: list[InfraMetricSnapshot] = []
    description: str
    # Associated latency event IDs for correlation
    related_workflow_ids: list[str] = []


class SeveritySummary(BaseModel):
    """Counts of violation severity levels."""

    total_violations: int = 0
    total_clean_nodes: int = 0
    distinct_workflows_affected: int = 0
    distinct_node_types_affected: int = 0


class QueryRecord(BaseModel):
    """Record of a PromQL/LogQL query executed during the analysis."""

    data_source: str
    expression: str
    step: str
    time_from: datetime
    time_to: datetime


class PerformanceReport(BaseModel):
    """The complete output artifact for one ANA-001 analysis run."""

    analysis_id: Literal["ANA-001"] = "ANA-001"
    time_range_from: datetime
    time_range_to: datetime
    generated_at: datetime
    latency_events: list[LatencyEvent] = []
    infra_snapshots: list[InfraMetricSnapshot] = []
    geographic_breakdown: dict[str, GeographicBreakdown] = {}
    severity_summary: SeveritySummary = SeveritySummary()
    findings: list[Finding] = []
    # Partial-mode sections that failed; key = section name, value = reason string
    unavailable_sections: dict[str, str] = {}
    # All queries executed during this run (for ## Appendix: Queries)
    queries_executed: list[QueryRecord] = []
    # Loki error analysis
    loki_error_count: int | None = None
    loki_top_errors: list[dict[str, Any]] = []

    @field_validator("time_range_from", "time_range_to", "generated_at")
    @classmethod
    def must_be_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("datetime fields must be UTC")
        offset = v.utcoffset()
        if offset is not None and offset.total_seconds() != 0:
            raise ValueError("datetime fields must be UTC (utcoffset=0)")
        return v

    def violations(self) -> list[LatencyEvent]:
        return sorted(
            [e for e in self.latency_events if e.status == "violation"],
            key=lambda e: (e.executed_at, e.source_host),
        )

    def clean_nodes(self) -> list[LatencyEvent]:
        return sorted(
            [e for e in self.latency_events if e.status == "clean"],
            key=lambda e: (e.executed_at, e.source_host),
        )
