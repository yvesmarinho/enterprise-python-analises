"""LatencyAnalyzer — query VictoriaMetrics for N8N node execution latency.

FR-001: global scan at step_global, auto drill-down at step_drilldown on spike windows.
FR-002: compute p50, p95, p99 per node per workflow.
FR-003: flag events where p95 >= 1.0s as  violations.
SC-002: all nodes (clean + violations) are collected.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from n8n_analyzer.collectors.victoria_metrics import VictoriaMetricsCollector
    from n8n_analyzer.config import Config

from n8n_analyzer.models.latency_event import LatencyEvent
from n8n_analyzer.models.report import QueryRecord

logger = logging.getLogger(__name__)

# Latency violation threshold in seconds (FR-003)
VIOLATION_THRESHOLD_SECONDS = 1.0

# PromQL expressions — use histogram_quantile over the full bucket metric
_QUANTILE_EXPR = (
    "histogram_quantile({quantile}, "
    "sum by (workflow_id, workflow_name, node_name, node_type, instance) ("
    "rate(n8n_node_execution_duration_seconds_bucket[{window}])"
    "))"
)


class LatencyAnalyzer:
    """Analyze N8N node execution latency from VictoriaMetrics."""

    def __init__(
        self,
        vm: "VictoriaMetricsCollector",
        config: "Config",
    ) -> None:
        self._vm = vm
        self._config = config

    async def analyze(
        self,
        start: datetime,
        end: datetime,
        step_global: str,
        step_drilldown: str,
    ) -> tuple[list[LatencyEvent], list[QueryRecord]]:
        """Run full latency analysis.

        Phase 1: global range scan at step_global.
        Phase 2: for any spike windows found, re-query at step_drilldown.

        Returns:
            (events, query_records)
            events: all LatencyEvent objects (violations + clean nodes)
            query_records: list of QueryRecord for the ## Appendix: Queries section
        """
        all_queries: list[QueryRecord] = []

        # ── Phase 1: Global scan ──────────────────────────────────────────────
        logger.info("Latency global scan: %s → %s @ %s", start.isoformat(), end.isoformat(), step_global)
        window = _step_to_range_window(step_global)
        p95_results, q_record = await self._vm.query_range(
            _QUANTILE_EXPR.format(quantile="0.95", window=window),
            start, end, step_global,
            is_primary=True,
        )
        all_queries.append(q_record)

        p50_results, q50 = await self._vm.query_range(
            _QUANTILE_EXPR.format(quantile="0.50", window=window),
            start, end, step_global,
            is_primary=True,
        )
        all_queries.append(q50)

        p99_results, q99 = await self._vm.query_range(
            _QUANTILE_EXPR.format(quantile="0.99", window=window),
            start, end, step_global,
            is_primary=True,
        )
        all_queries.append(q99)

        # Build per-(workflow, node, host) series index for p50 and p99 lookups
        p50_index = _build_series_index(p50_results)
        p99_index = _build_series_index(p99_results)

        # Convert p95 series → LatencyEvent list, flag violations
        global_events: list[LatencyEvent] = []
        for labels, timestamps, values in p95_results:
            series_events = _series_to_events(labels, timestamps, values, p50_index, p99_index)
            global_events.extend(series_events)

        logger.info("Global scan: %d node-time events (%d violations)",
                    len(global_events),
                    sum(1 for e in global_events if e.status == "violation"))

        # ── Phase 2: Spike window drill-down ──────────────────────────────────
        spike_windows = _detect_spike_windows(global_events, step_global)
        drilldown_events: list[LatencyEvent] = []

        for win_start, win_end in spike_windows:
            logger.info(
                "Drilldown: %s → %s @ %s",
                win_start.isoformat(), win_end.isoformat(), step_drilldown,
            )
            dd_window = _step_to_range_window(step_drilldown)
            dd_p95, dq95 = await self._vm.query_range(
                _QUANTILE_EXPR.format(quantile="0.95", window=dd_window),
                win_start, win_end, step_drilldown,
                is_primary=True,
            )
            all_queries.append(dq95)

            dd_p50, dq50 = await self._vm.query_range(
                _QUANTILE_EXPR.format(quantile="0.50", window=dd_window),
                win_start, win_end, step_drilldown,
                is_primary=True,
            )
            all_queries.append(dq50)

            dd_p99, dq99 = await self._vm.query_range(
                _QUANTILE_EXPR.format(quantile="0.99", window=dd_window),
                win_start, win_end, step_drilldown,
                is_primary=True,
            )
            all_queries.append(dq99)

            dd_p50_idx = _build_series_index(dd_p50)
            dd_p99_idx = _build_series_index(dd_p99)

            for labels, timestamps, values in dd_p95:
                drilldown_events.extend(
                    _series_to_events(labels, timestamps, values, dd_p50_idx, dd_p99_idx)
                )

        # Merge: replace global events in spike windows with drilldown events
        # (keep global clean events that are outside spike windows)
        spike_ts_set = {
            ts
            for win_start, win_end in spike_windows
            for e in global_events
            if win_start <= e.executed_at <= win_end
            for ts in [e.executed_at]
        }
        merged = (
            [e for e in global_events if e.executed_at not in spike_ts_set]
            + drilldown_events
        )
        merged.sort(key=lambda e: (e.executed_at, e.source_host))

        logger.info(
            "Final event set: %d total (%d violations, %d clean)",
            len(merged),
            sum(1 for e in merged if e.status == "violation"),
            sum(1 for e in merged if e.status == "clean"),
        )
        return merged, all_queries


# ── Helpers ──────────────────────────────────────────────────────────────────

def _step_to_range_window(step: str) -> str:
    """Convert a step string to a Prometheus rate() window.

    Use 2× the step to avoid gaps at boundaries.
    E.g. "5m" → "10m", "1m" → "2m", "30s" → "1m".
    """
    step = step.strip()
    if step.endswith("m"):
        minutes = int(step[:-1]) * 2
        return f"{minutes}m"
    if step.endswith("s"):
        seconds = int(step[:-1]) * 2
        return f"{seconds}s" if seconds < 60 else f"{seconds // 60}m"
    if step.endswith("h"):
        hours = int(step[:-1]) * 2
        return f"{hours}h"
    return step


def _build_series_index(
    results: list[tuple[dict, list[float], list[str]]]
) -> dict[tuple, dict[float, float]]:
    """Build a (workflow_id, node_name, instance) → {timestamp: value} index."""
    index: dict[tuple, dict[float, float]] = {}
    for labels, timestamps, values in results:
        key = (
            labels.get("workflow_id", ""),
            labels.get("node_name", ""),
            labels.get("instance", ""),
        )
        ts_map: dict[float, float] = {}
        for ts, val in zip(timestamps, values):
            try:
                ts_map[ts] = float(val)
            except (ValueError, TypeError):
                ts_map[ts] = 0.0
        index[key] = ts_map
    return index


def _series_to_events(
    labels: dict[str, str],
    timestamps: list[float],
    values: list[str],
    p50_index: dict,
    p99_index: dict,
) -> list[LatencyEvent]:
    """Convert a single p95 metric series into a list of LatencyEvent objects."""
    workflow_id = labels.get("workflow_id", "unknown")
    workflow_name = labels.get("workflow_name", workflow_id)
    node_name = labels.get("node_name", "unknown")
    node_type = labels.get("node_type", "unknown")
    source_host = labels.get("instance", "unknown")

    series_key = (workflow_id, node_name, source_host)
    p50_map = p50_index.get(series_key, {})
    p99_map = p99_index.get(series_key, {})

    events: list[LatencyEvent] = []
    for ts, raw_val in zip(timestamps, values):
        try:
            p95_val = float(raw_val)
        except (ValueError, TypeError):
            continue
        if p95_val <= 0.0:
            continue  # VM returns NaN as "NaN" string — skip

        executed_at = datetime.fromtimestamp(ts, tz=timezone.utc)
        # Use p95 as the representative duration; p50/p99 stored differently if needed
        status = "violation" if p95_val >= VIOLATION_THRESHOLD_SECONDS else "clean"

        events.append(LatencyEvent(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            node_name=node_name,
            node_type=node_type,
            executed_at=executed_at,
            duration_seconds=p95_val,
            source_host=source_host,
            status=status,
        ))

    return events


def _detect_spike_windows(
    events: list[LatencyEvent],
    step: str,
) -> list[tuple[datetime, datetime]]:
    """Identify contiguous time windows containing violation events.

    Merges adjacent violation timestamps that are within 2× step of each other
    and returns a list of (window_start, window_end) UTC datetime pairs with
    ±1 step padding on each side.
    """
    violations = sorted(
        {e.executed_at for e in events if e.status == "violation"}
    )
    if not violations:
        return []

    step_delta = _parse_step_to_timedelta(step)
    padding = step_delta * 2

    # Merge into contiguous groups
    groups: list[list[datetime]] = [[violations[0]]]
    for ts in violations[1:]:
        if ts - groups[-1][-1] <= step_delta * 3:
            groups[-1].append(ts)
        else:
            groups.append([ts])

    windows: list[tuple[datetime, datetime]] = []
    for group in groups:
        win_start = max(
            group[0] - padding,
            datetime(2000, 1, 1, tzinfo=timezone.utc),
        )
        win_end = group[-1] + padding
        windows.append((win_start, win_end))

    return windows


def _parse_step_to_timedelta(step: str) -> timedelta:
    """Parse a step string like '5m', '30s', '1h' into a timedelta."""
    step = step.strip()
    if step.endswith("m"):
        return timedelta(minutes=int(step[:-1]))
    if step.endswith("s"):
        return timedelta(seconds=int(step[:-1]))
    if step.endswith("h"):
        return timedelta(hours=int(step[:-1]))
    return timedelta(minutes=5)
