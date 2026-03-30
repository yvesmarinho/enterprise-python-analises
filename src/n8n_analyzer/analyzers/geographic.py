"""GeographicAnalyzer — per-host latency breakdown and RTT estimation.

Groups LatencyEvents by source_host, computes p50/p95/p99 per group, then
estimates the wf001→wf008 network RTT contribution using:
  1. Primary:   probe_duration_seconds from blackbox-exporter (if available)
  2. Fallback:  wf008.p50 - wf001.p50 delta from the latency events

Raises PartialDataError if VictoriaMetrics is unreachable and no events
are present for RTT estimation (FR-014).

Constitutes T028 (GeographicAnalyzer) + T029 (RTT estimator).
"""

from __future__ import annotations

import statistics
from datetime import datetime
from typing import TYPE_CHECKING

from n8n_analyzer.collectors.base import PartialDataError
from n8n_analyzer.models.report import GeographicBreakdown, QueryRecord

if TYPE_CHECKING:
    from n8n_analyzer.collectors.victoria_metrics import VictoriaMetricsCollector
    from n8n_analyzer.config import Config
    from n8n_analyzer.models.latency_event import LatencyEvent


# Step used for the blackbox probe query (matches the default scrape interval)
_PROBE_STEP = "30s"


def _percentile(data: list[float], p: float) -> float | None:
    """Return the p-th percentile of *data* (0–100 scale), or None if empty."""
    if not data:
        return None
    sorted_data = sorted(data)
    idx = (p / 100) * (len(sorted_data) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_data) - 1)
    frac = idx - lo
    return sorted_data[lo] + frac * (sorted_data[hi] - sorted_data[lo])


class GeographicAnalyzer:
    """Compute per-host latency percentiles and RTT contribution."""

    def __init__(self, vm: "VictoriaMetricsCollector", config: "Config") -> None:
        self._vm = vm
        self._config = config

    async def analyze(
        self,
        events: "list[LatencyEvent]",
        from_dt: datetime,
        to_dt: datetime,
    ) -> tuple[dict[str, GeographicBreakdown], list[QueryRecord]]:
        """Return per-host GeographicBreakdown dict and query records.

        Parameters
        ----------
        events:   All LatencyEvents (both "clean" and "violation").
        from_dt:  Analysis window start.
        to_dt:    Analysis window end.
        """
        queries: list[QueryRecord] = []

        # Group events by source_host
        host_buckets: dict[str, list[float]] = {}
        for event in events:
            host_buckets.setdefault(event.source_host, []).append(
                event.duration_seconds
            )

        if not host_buckets:
            raise PartialDataError(
                "geographic analysis",
                "No latency events available for geographic breakdown.",
            )

        # Build per-host breakdown
        breakdowns: dict[str, GeographicBreakdown] = {}
        for host, durations in host_buckets.items():
            bd = GeographicBreakdown(
                source_host=host,
                p50_seconds=_percentile(durations, 50),
                p95_seconds=_percentile(durations, 95),
                p99_seconds=_percentile(durations, 99),
                event_count=len(durations),
            )
            breakdowns[host] = bd

        # ── RTT estimation (T029) ─────────────────────────────────────────────
        probe_qr = await self._estimate_rtt(breakdowns, from_dt, to_dt)
        if probe_qr is not None:
            queries.append(probe_qr)

        return breakdowns, queries

    # ── RTT estimator ─────────────────────────────────────────────────────────

    async def _estimate_rtt(
        self,
        breakdowns: dict[str, "GeographicBreakdown"],
        from_dt: datetime,
        to_dt: datetime,
    ) -> QueryRecord | None:
        """Estimate network RTT contribution for wf008 relative to wf001.

        Primary method: query VictoriaMetrics for probe_duration_seconds
        (blackbox-exporter), filtered to the wf008 probe target.

        Fallback: derive from wf008.p50 - wf001.p50 if both are present.

        The result is stored in-place on the breakdowns dict.
        """
        # Try primary: blackbox exporter probe duration
        probe_expr = (
            'avg by (instance)(probe_duration_seconds{instance=~"wf008.*"})'
        )
        wf001_key = next((h for h in breakdowns if "wf001" in h), None)
        wf008_key = next((h for h in breakdowns if "wf008" in h), None)

        qr: QueryRecord | None = None
        rtt_seconds: float | None = None

        try:
            series_list, qr = await self._vm.query_range(
                probe_expr, from_dt, to_dt, _PROBE_STEP, is_primary=False
            )
            probe_values: list[float] = []
            for _labels, _, values in series_list:
                for val_str in values:
                    try:
                        probe_values.append(float(val_str))
                    except (ValueError, TypeError):
                        continue
            if probe_values:
                rtt_seconds = statistics.median(probe_values)
        except PartialDataError:
            # Primary source unavailable — fall back to p50 delta
            qr = None

        # Fallback: p50 delta between wf008 and wf001
        if rtt_seconds is None and wf001_key and wf008_key:
            p50_wf001 = breakdowns[wf001_key].p50_seconds
            p50_wf008 = breakdowns[wf008_key].p50_seconds
            if p50_wf001 is not None and p50_wf008 is not None:
                rtt_seconds = max(0.0, p50_wf008 - p50_wf001)

        # Assign RTT and derived application latency to wf008 breakdown
        if wf008_key and rtt_seconds is not None:
            bd = breakdowns[wf008_key]
            bd.network_contribution_seconds = rtt_seconds
            if bd.p95_seconds is not None:
                bd.application_latency_seconds = max(0.0, bd.p95_seconds - rtt_seconds)

        # For wf001, network contribution is 0 (local baseline)
        if wf001_key:
            bd = breakdowns[wf001_key]
            bd.network_contribution_seconds = 0.0
            if bd.p95_seconds is not None:
                bd.application_latency_seconds = bd.p95_seconds

        return qr
