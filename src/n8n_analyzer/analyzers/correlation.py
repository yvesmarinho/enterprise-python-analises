"""CorrelationAnalyzer — query infra metrics within violation windows.

For each CorrelationWindow (centered on a latency violation), queries:
  - redis_list_length      → queue-depth spike indicator
  - pg_stat_activity_max_tx_duration → DB slow-query indicator
  - external_api_response_seconds    → external API timeout indicator

Returns a flat list[InfraMetricSnapshot] and a list[QueryRecord].
Each unavailable source raises PartialDataError (FR-014).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from n8n_analyzer.collectors.base import PartialDataError
from n8n_analyzer.models.infra_metric import InfraMetricSnapshot
from n8n_analyzer.models.report import QueryRecord

if TYPE_CHECKING:
    from n8n_analyzer.collectors.victoria_metrics import VictoriaMetricsCollector
    from n8n_analyzer.config import Config
    from n8n_analyzer.models.correlation_window import CorrelationWindow


# Metric queries for the three infra sources
_REDIS_EXPR = "redis_list_length"
_PG_EXPR = "pg_stat_activity_max_tx_duration"
_EXTERNAL_API_EXPR = (
    "histogram_quantile(0.95, sum by (job)(rate(external_api_response_seconds_bucket[5m])))"
)

# Thresholds for labelling a snapshot as indicative
_REDIS_THRESHOLD = 100.0        # depth > 100 = spike
_PG_DURATION_MS = 500.0         # > 500 ms active transaction
_EXTERNAL_API_P95 = 2.0         # p95 > 2 s


class CorrelationAnalyzer:
    """Query infrastructure metrics within violation windows."""

    def __init__(self, vm: "VictoriaMetricsCollector", config: "Config") -> None:
        self._vm = vm
        self._config = config

    async def analyze(
        self,
        windows: "list[CorrelationWindow]",
        global_from: datetime,
        global_to: datetime,
    ) -> tuple[list[InfraMetricSnapshot], list[QueryRecord]]:
        """Return infra snapshots over all windows plus query records."""
        snapshots: list[InfraMetricSnapshot] = []
        queries: list[QueryRecord] = []

        if not windows:
            return snapshots, queries

        # Derive a step that covers the window size (30s window → "30s" step)
        step = f"{int(self._config.correlation_window_seconds)}s"

        # Query each metric across the full global range; filter to windows later.
        # This avoids N×3 queries when many windows share overlapping ranges.
        results = await asyncio.gather(
            self._query_one(_REDIS_EXPR, global_from, global_to, step),
            self._query_one(_PG_EXPR, global_from, global_to, step),
            self._query_one(_EXTERNAL_API_EXPR, global_from, global_to, step),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                # At least one infra source failed; raise PartialDataError so
                # CLI can mark section as unavailable without aborting the run.
                raise PartialDataError(
                    "infrastructure correlation",
                    str(result),
                )
            series_list, qr = result
            queries.append(qr)
            snapshots.extend(
                self._filter_to_windows(series_list, windows)
            )

        return snapshots, queries

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _query_one(
        self,
        expr: str,
        from_dt: datetime,
        to_dt: datetime,
        step: str,
    ) -> tuple[list, QueryRecord]:
        """Query VictoriaMetrics; propagate exceptions to gather()."""
        series_list, qr = await self._vm.query_range(
            expr, from_dt, to_dt, step, is_primary=False
        )
        return series_list, qr

    def _filter_to_windows(
        self,
        series_list: list,
        windows: "list[CorrelationWindow]",
    ) -> list[InfraMetricSnapshot]:
        """Convert time-series to InfraMetricSnapshot, keeping only timestamps
        that fall within at least one correlation window."""
        snaps: list[InfraMetricSnapshot] = []
        half = timedelta(seconds=self._config.correlation_window_seconds)

        for labels, timestamps, values in series_list:
            metric_name = labels.get("__name__", "unknown")
            instance = labels.get("instance", labels.get("job", "vm"))

            for ts_str, val_str in zip(timestamps, values):
                try:
                    ts = datetime.fromtimestamp(float(ts_str), tz=timezone.utc)
                    val = float(val_str)
                except (ValueError, TypeError):
                    continue

                # Only keep data points within a violation window
                if not any(
                    abs((ts - w.center_ts).total_seconds()) <= half.total_seconds()
                    for w in windows
                ):
                    continue

                snaps.append(
                    InfraMetricSnapshot(
                        metric_name=metric_name,
                        value=val,
                        timestamp=ts,
                        source_label=instance,
                    )
                )

        return snaps
