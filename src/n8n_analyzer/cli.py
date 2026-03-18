"""CLI — Click interface for the N8N Performance Analyzer (ANA-001).

Entry point: analyze-n8n (via pyproject.toml [project.scripts])
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

from n8n_analyzer.config import Config, ConfigError


def _parse_iso(ctx: click.Context, param: click.Parameter, value: str) -> datetime:
    """Parse an ISO-8601 date string and return a UTC-aware datetime."""
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        elif dt.utcoffset() is not None and dt.utcoffset().total_seconds() != 0:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        raise click.BadParameter(f"Expected ISO-8601 date, got: {value!r}") from None


@click.command(name="analyze-n8n")
@click.option(
    "--from", "from_dt",
    required=True,
    metavar="DATETIME",
    callback=_parse_iso,
    is_eager=False,
    help="Analysis start time (ISO-8601, UTC). Example: 2026-01-01 or 2026-01-01T00:00:00Z",
)
@click.option(
    "--to", "to_dt",
    required=True,
    metavar="DATETIME",
    callback=_parse_iso,
    is_eager=False,
    help="Analysis end time (ISO-8601, UTC). Example: 2026-03-17 or 2026-03-17T23:59:59Z",
)
@click.option(
    "--output-format",
    type=click.Choice(["markdown", "json"], case_sensitive=False),
    default="markdown",
    show_default=True,
    help="Report output format.",
)
@click.option(
    "--step-global",
    default="5m",
    show_default=True,
    help="PromQL step for the global range scan (e.g. 5m, 15m).",
)
@click.option(
    "--step-drilldown",
    default="1m",
    show_default=True,
    help="PromQL step for drilldown into spike windows (e.g. 1m, 30s).",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, writable=True, path_type=Path),
    default=Path("reports"),
    show_default=True,
    help="Directory to write the report file(s).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Validate configuration and print resolved settings without running analysis.",
)
def main(
    from_dt: datetime,
    to_dt: datetime,
    output_format: str,
    step_global: str,
    step_drilldown: str,
    output_dir: Path,
    dry_run: bool,
) -> None:
    """ANA-001 N8N Performance Analyzer.

    Queries VictoriaMetrics and Loki for N8N workflow execution data and
    generates a structured performance report identifying latency violations
    and their root causes.
    """
    if from_dt >= to_dt:
        raise click.UsageError("--from must be earlier than --to")

    # Load and validate configuration (raises ConfigError on bad config)
    try:
        config = Config()
    except ConfigError as exc:
        click.echo(f"Configuration error:\n{exc}", err=True)
        sys.exit(1)

    if dry_run:
        click.echo("=== DRY RUN — resolved configuration (credentials redacted) ===\n")
        click.echo(config.safe_repr())
        click.echo(f"from             = {from_dt.isoformat()}")
        click.echo(f"to               = {to_dt.isoformat()}")
        click.echo(f"output_format    = {output_format}")
        click.echo(f"step_global      = {step_global}")
        click.echo(f"step_drilldown   = {step_drilldown}")
        click.echo(f"output_dir       = {output_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        asyncio.run(
            _run_analysis(
                config=config,
                from_dt=from_dt,
                to_dt=to_dt,
                output_format=output_format,
                step_global=step_global,
                step_drilldown=step_drilldown,
                output_dir=output_dir,
            )
        )
    except KeyboardInterrupt:
        click.echo("\nAnalysis interrupted.", err=True)
        sys.exit(1)


async def _run_analysis(
    *,
    config: Config,
    from_dt: datetime,
    to_dt: datetime,
    output_format: str,
    step_global: str,
    step_drilldown: str,
    output_dir: Path,
) -> None:
    """Orchestrate the full analysis pipeline."""

    from n8n_analyzer.analyzers.correlation import CorrelationAnalyzer
    from n8n_analyzer.analyzers.geographic import GeographicAnalyzer
    from n8n_analyzer.analyzers.latency import LatencyAnalyzer
    from n8n_analyzer.analyzers.loki_analyzer import LokiAnalyzer
    from n8n_analyzer.collectors.base import PartialDataError
    from n8n_analyzer.collectors.loki import LokiCollector
    from n8n_analyzer.collectors.victoria_metrics import VictoriaMetricsCollector
    from n8n_analyzer.labels.root_cause import classify
    from n8n_analyzer.models.correlation_window import CorrelationWindow  # noqa: F401
    from n8n_analyzer.models.report import (
        Finding,
        PerformanceReport,
        SeveritySummary,
    )
    from n8n_analyzer.reporters import build_filename
    from n8n_analyzer.reporters.json_reporter import JsonReporter
    from n8n_analyzer.reporters.markdown import MarkdownReporter

    now_utc = datetime.now(tz=timezone.utc)
    report = PerformanceReport(
        analysis_id="ANA-001",
        time_range_from=from_dt,
        time_range_to=to_dt,
        generated_at=now_utc,
    )

    vm_collector = VictoriaMetricsCollector(
        config.victoria_metrics_url, config.request_timeout_seconds
    )
    loki_collector = LokiCollector(
        config.loki_url, config.request_timeout_seconds
    )

    # ── Phase A: Latency Analysis (primary — exit 1 on failure) ─────────────
    click.echo(f"[1/4] Querying latency metrics ({step_global} step)…")
    try:
        analyzer = LatencyAnalyzer(vm_collector, config)
        events, queries = await analyzer.analyze(
            from_dt, to_dt, step_global, step_drilldown
        )
        report.latency_events = events
        report.queries_executed.extend(queries)
    except Exception as exc:
        click.echo(
            f"FATAL: VictoriaMetrics query failed: [{type(exc).__name__}] {exc!r}",
            err=True,
        )
        sys.exit(1)

    # ── Phase B: Infra Correlation (secondary — partial mode on failure) ─────
    click.echo("[2/4] Running infrastructure correlation…")
    windows = _build_correlation_windows(events, config.correlation_window_seconds)
    try:
        corr_analyzer = CorrelationAnalyzer(vm_collector, config)
        snapshots, corr_queries = await corr_analyzer.analyze(windows, from_dt, to_dt)
        report.infra_snapshots = snapshots
        report.queries_executed.extend(corr_queries)
    except PartialDataError as exc:
        click.echo(f"WARNING: {exc}", err=True)
        report.unavailable_sections["Infrastructure Correlation"] = str(exc)

    # ── Phase C: Loki error logs (secondary — partial mode on failure) ───────
    click.echo("[3/4] Querying Loki error logs…")
    try:
        loki_analyzer = LokiAnalyzer(loki_collector)
        loki_result, loki_queries = await loki_analyzer.analyze(
            from_dt, to_dt, events
        )
        report.loki_error_count = loki_result["total_errors"]
        report.loki_top_errors = loki_result["top_errors"]
        report.queries_executed.extend(loki_queries)
    except PartialDataError as exc:
        click.echo(f"WARNING: {exc}", err=True)
        report.unavailable_sections["Error Log Summary"] = str(exc)

    # ── Phase D: Geographic Analysis ─────────────────────────────────────────
    click.echo("[4/4] Computing geographic breakdown…")
    try:
        geo_analyzer = GeographicAnalyzer(vm_collector, config)
        geo_result, geo_queries = await geo_analyzer.analyze(events, from_dt, to_dt)
        report.geographic_breakdown = geo_result
        report.queries_executed.extend(geo_queries)
    except PartialDataError as exc:
        click.echo(f"WARNING: {exc}", err=True)
        report.unavailable_sections["Geographic Analysis"] = str(exc)

    # ── Root-cause labelling ──────────────────────────────────────────────────
    violations = [e for e in events if e.status == "violation"]
    findings: list[Finding] = []
    for event in violations:
        relevant_snaps = [
            s for s in report.infra_snapshots
            if abs((s.timestamp - event.executed_at).total_seconds())
               <= config.correlation_window_seconds
        ]
        relevant_logs = [
            entry for entry in report.loki_top_errors
            if _within_window(entry, event, config.correlation_window_seconds)
        ]
        label = classify(event, relevant_snaps, relevant_logs)
        findings.append(
            Finding(
                root_cause_label=label,
                evidence=relevant_snaps,
                description=_describe_finding(label, event),
                related_workflow_ids=[event.workflow_id],
            )
        )
    report.findings = findings

    # ── Severity summary ──────────────────────────────────────────────────────
    report.severity_summary = SeveritySummary(
        total_violations=len(violations),
        total_clean_nodes=len([e for e in events if e.status == "clean"]),
        distinct_workflows_affected=len({e.workflow_id for e in violations}),
        distinct_node_types_affected=len({e.node_type for e in violations}),
    )

    # ── Render and write report ───────────────────────────────────────────────
    if output_format == "json":
        renderer = JsonReporter()
        content = renderer.render(report)
        ext = "json"
    else:
        renderer = MarkdownReporter()
        content = renderer.render(report)
        ext = "md"

    filename = build_filename(from_dt, to_dt, ext)
    output_path = output_dir / filename
    output_path.write_text(content, encoding="utf-8")

    click.echo(f"\nReport written to: {output_path}")
    click.echo(
        f"Summary: {report.severity_summary.total_violations} violations "
        f"across {report.severity_summary.distinct_workflows_affected} workflow(s)."
    )
    if report.unavailable_sections:
        click.echo("Partial mode — unavailable sections:", err=True)
        for section, reason in report.unavailable_sections.items():
            click.echo(f"  [{section}] {reason}", err=True)


def _build_correlation_windows(events: list, window_seconds: int) -> list:
    from n8n_analyzer.models.correlation_window import CorrelationWindow
    violations = [e for e in events if e.status == "violation"]
    if not violations:
        return []
    # Group violations within window_seconds of each other into shared windows
    windows = []
    for event in violations:
        for win in windows:
            if abs((win.center_ts - event.executed_at).total_seconds()) <= window_seconds:
                win.events.append(event)
                break
        else:
            windows.append(CorrelationWindow(
                center_ts=event.executed_at,
                window_seconds=window_seconds,
                events=[event],
            ))
    return windows


def _within_window(log_entry: dict, event: object, window_seconds: int) -> bool:
    """Return True if a log entry timestamp (nanoseconds str) is within window of event."""
    try:
        ts_ns = int(log_entry.get("timestamp", "0"))
        import datetime as dt_mod  # noqa: PLC0415
        log_ts = dt_mod.datetime.fromtimestamp(ts_ns / 1e9, tz=dt_mod.timezone.utc)
        return abs((log_ts - getattr(event, "executed_at")).total_seconds()) <= window_seconds
    except Exception:
        return False


def _describe_finding(label: "Any", event: object) -> str:
    """Generate a human-readable description for a finding (no prescriptive fix commands)."""
    from n8n_analyzer.labels.root_cause import RootCauseLabel  # noqa: PLC0415
    node = getattr(event, "node_name", "unknown")
    wf = getattr(event, "workflow_name", "unknown")
    duration = float(getattr(event, "duration_seconds", 0.0))
    descriptions: dict[Any, str] = {
        RootCauseLabel.QUEUE_DEPTH_SPIKE: (
            f"Node '{node}' in workflow '{wf}' experienced {duration:.2f}s execution time. "
            "Correlated with a Redis queue depth spike at the same time window, suggesting "
            "worker backlog as a contributing factor."
        ),
        RootCauseLabel.DB_SLOW_QUERY: (
            f"Node '{node}' in workflow '{wf}' took {duration:.2f}s. "
            "A PostgreSQL slow query (>500ms) was observed in the same time window, "
            "indicating database response time as a contributing factor."
        ),
        RootCauseLabel.EXTERNAL_API_TIMEOUT: (
            f"Node '{node}' in workflow '{wf}' took {duration:.2f}s. "
            "An external API call (Chatwoot / WhatsApp) with p95 >2s was detected "
            "in the same time window."
        ),
        RootCauseLabel.N8N_INTERNAL_ERROR: (
            f"Node '{node}' in workflow '{wf}' took {duration:.2f}s. "
            "A correlated N8N error log entry was found within the correlation window."
        ),
        RootCauseLabel.NETWORK_LATENCY: (
            f"Node '{node}' in workflow '{wf}' recorded {duration:.2f}s from the "
            "Brazil probe (wf008). This measurement includes Brazil→US East network RTT "
            "and may overstate application-side latency."
        ),
        RootCauseLabel.UNKNOWN: (
            f"Node '{node}' in workflow '{wf}' took {duration:.2f}s. "
            "No correlated infrastructure event was found in the queried data. "
            "Further investigation with additional metrics may be required."
        ),
    }
    return descriptions.get(label, f"Latency violation: {duration:.2f}s for node '{node}'.")
