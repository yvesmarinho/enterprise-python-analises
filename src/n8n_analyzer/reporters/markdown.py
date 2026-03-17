"""MarkdownReporter — render PerformanceReport as a Markdown document.

Sections:
  # N8N Performance Report ANA-001
  ## Summary
  ## Latency Violations
  ## Findings
  ## Queue Latency            (Phase 4 — US2)
  ## Infrastructure Correlation (Phase 4 — US2)
  ## Error Log Summary        (Phase 4 — US2)
  ## Geographic Analysis      (Phase 5 — US3)
  ## Appendix: Queries        (T040)

Partial mode: unavailable_sections are rendered as DATA UNAVAILABLE blocks (FR-014).
No prescriptive fix commands are emitted (FR-013).
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from n8n_analyzer.models.report import PerformanceReport


class MarkdownReporter:
    """Render a PerformanceReport to Markdown text."""

    def render(self, report: "PerformanceReport") -> str:
        sections: list[str] = [
            self._header(report),
            self._summary(report),
            self._latency_violations(report),
            self._findings(report),
            self._queue_latency(report),
            self._infra_correlation(report),
            self._error_log_summary(report),
            self._geographic_analysis(report),
            self._appendix_queries(report),
        ]
        return "\n\n".join(s for s in sections if s.strip())

    # ── Sections ─────────────────────────────────────────────────────────────

    def _header(self, report: "PerformanceReport") -> str:
        return (
            f"# N8N Performance Report {report.analysis_id}\n\n"
            f"**Generated**: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"**Period**: {report.time_range_from.strftime('%Y-%m-%d')} → "
            f"{report.time_range_to.strftime('%Y-%m-%d')}"
        )

    def _summary(self, report: "PerformanceReport") -> str:
        s = report.severity_summary
        lines = [
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total latency violations | {s.total_violations} |",
            f"| Clean nodes (no violation) | {s.total_clean_nodes} |",
            f"| Distinct workflows affected | {s.distinct_workflows_affected} |",
            f"| Distinct node types affected | {s.distinct_node_types_affected} |",
        ]
        if report.unavailable_sections:
            lines.append("")
            lines.append("> **Partial mode** — the following sections use unavailable data:")
            for section, reason in report.unavailable_sections.items():
                lines.append(f"> - **{section}**: {reason}")
        return "\n".join(lines)

    def _latency_violations(self, report: "PerformanceReport") -> str:
        violations = report.violations()
        lines = ["## Latency Violations"]
        if not violations:
            lines.append("")
            lines.append("No violations found — all monitored nodes had p95 < 1.0 s.")
            return "\n".join(lines)

        lines += [
            "",
            "| Timestamp (UTC) | Workflow | Node | Node Type | p95 (s) | Source Host |",
            "|-----------------|----------|------|-----------|---------|-------------|",
        ]
        for e in violations:
            ts = e.executed_at.strftime("%Y-%m-%d %H:%M:%S")
            lines.append(
                f"| {ts} | {e.workflow_name} | {e.node_name} | {e.node_type} "
                f"| {e.duration_seconds:.3f} | {e.source_host} |"
            )

        # Also render clean nodes table (SC-002: all nodes must appear in report)
        clean = report.clean_nodes()
        if clean:
            lines += [
                "",
                "### Clean Nodes (p95 < 1.0 s)",
                "",
                "| Workflow | Node | Node Type | p95 (s) | Source Host |",
                "|----------|------|-----------|---------|-------------|",
            ]
            for e in clean:
                lines.append(
                    f"| {e.workflow_name} | {e.node_name} | {e.node_type} "
                    f"| {e.duration_seconds:.3f} | {e.source_host} |"
                )
        return "\n".join(lines)

    def _findings(self, report: "PerformanceReport") -> str:
        lines = ["## Findings"]
        if not report.findings:
            lines.append("")
            lines.append("No findings (no violations detected).")
            return "\n".join(lines)
        for i, finding in enumerate(report.findings, 1):
            lines += [
                "",
                f"### Finding {i} — `{finding.root_cause_label.value}`",
                "",
                finding.description,
            ]
            if finding.evidence:
                lines += [
                    "",
                    "**Supporting evidence**:",
                    "",
                    "| Metric | Value | Timestamp | Source |",
                    "|--------|-------|-----------|--------|",
                ]
                for snap in finding.evidence:
                    ts = snap.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    lines.append(
                        f"| {snap.metric_name} | {snap.value:.4f} | {ts} | {snap.source_label} |"
                    )
        return "\n".join(lines)

    def _queue_latency(self, report: "PerformanceReport") -> str:
        section = "Queue Latency"
        if section in report.unavailable_sections:
            reason = report.unavailable_sections[section]
            print(f"WARNING: [{section}] {reason}", file=sys.stderr)
            return f"## Queue Latency\n\n`DATA UNAVAILABLE: {reason}`"

        redis_snaps = [
            s for s in report.infra_snapshots if "redis" in s.metric_name.lower()
        ]
        if not redis_snaps:
            return ""

        lines = [
            "## Queue Latency",
            "",
            "| Timestamp (UTC) | Queue Depth | Source |",
            "|-----------------|-------------|--------|",
        ]
        for snap in sorted(redis_snaps, key=lambda s: s.timestamp):
            ts = snap.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"| {ts} | {snap.value:.0f} | {snap.source_label} |")
        return "\n".join(lines)

    def _infra_correlation(self, report: "PerformanceReport") -> str:
        section = "Infrastructure Correlation"
        if section in report.unavailable_sections:
            reason = report.unavailable_sections[section]
            print(f"WARNING: [{section}] {reason}", file=sys.stderr)
            return f"## Infrastructure Correlation\n\n`DATA UNAVAILABLE: {reason}`"

        non_redis = [
            s for s in report.infra_snapshots if "redis" not in s.metric_name.lower()
        ]
        if not non_redis:
            return ""

        lines = [
            "## Infrastructure Correlation",
            "",
            "| Timestamp (UTC) | Metric | Value | Source |",
            "|-----------------|--------|-------|--------|",
        ]
        for snap in sorted(non_redis, key=lambda s: s.timestamp):
            ts = snap.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            lines.append(
                f"| {ts} | {snap.metric_name} | {snap.value:.4f} | {snap.source_label} |"
            )
        return "\n".join(lines)

    def _error_log_summary(self, report: "PerformanceReport") -> str:
        section = "Error Log Summary"
        if section in report.unavailable_sections:
            reason = report.unavailable_sections[section]
            print(f"WARNING: [{section}] {reason}", file=sys.stderr)
            return f"## Error Log Summary\n\n`DATA UNAVAILABLE: {reason}`"

        if report.loki_error_count is None:
            return ""

        lines = [
            "## Error Log Summary",
            "",
            f"**Total N8N errors in period**: {report.loki_error_count}",
        ]
        if report.loki_top_errors:
            lines += [
                "",
                "### Top Error Types",
                "",
                "| Rank | Error Type | Count |",
                "|------|------------|-------|",
            ]
            for rank, entry in enumerate(report.loki_top_errors[:3], 1):
                lines.append(
                    f"| {rank} | {entry.get('error_type', 'unknown')} "
                    f"| {entry.get('count', 0)} |"
                )
        return "\n".join(lines)

    def _geographic_analysis(self, report: "PerformanceReport") -> str:
        section = "Geographic Analysis"
        if section in report.unavailable_sections:
            reason = report.unavailable_sections[section]
            print(f"WARNING: [{section}] {reason}", file=sys.stderr)
            return f"## Geographic Analysis\n\n`DATA UNAVAILABLE: {reason}`"

        if not report.geographic_breakdown:
            return ""

        lines = [
            "## Geographic Analysis",
            "",
            "| Source Host | p50 (s) | p95 (s) | p99 (s) | Network RTT (s) | App Latency (s) | Events |",
            "|-------------|---------|---------|---------|-----------------|-----------------|--------|",
        ]
        for host, bd in sorted(report.geographic_breakdown.items()):
            def _fmt(v: float | None) -> str:
                return f"{v:.3f}" if v is not None else "—"
            lines.append(
                f"| {bd.source_host} "
                f"| {_fmt(bd.p50_seconds)} "
                f"| {_fmt(bd.p95_seconds)} "
                f"| {_fmt(bd.p99_seconds)} "
                f"| {_fmt(bd.network_contribution_seconds)} "
                f"| {_fmt(bd.application_latency_seconds)} "
                f"| {bd.event_count} |"
            )
        return "\n".join(lines)

    def _appendix_queries(self, report: "PerformanceReport") -> str:
        if not report.queries_executed:
            return ""
        lines = [
            "## Appendix: Queries",
            "",
            "All PromQL/LogQL expressions executed during this analysis run.",
            "",
            "| # | Data Source | Expression | Step | From | To |",
            "|---|-------------|------------|------|------|----|",
        ]
        for i, q in enumerate(report.queries_executed, 1):
            expr_short = q.expression[:80].replace("|", "\\|")
            lines.append(
                f"| {i} | {q.data_source} | `{expr_short}` | {q.step} "
                f"| {q.time_from.strftime('%Y-%m-%dT%H:%M')} "
                f"| {q.time_to.strftime('%Y-%m-%dT%H:%M')} |"
            )
        return "\n".join(lines)
