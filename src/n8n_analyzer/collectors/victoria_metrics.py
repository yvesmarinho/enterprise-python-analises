"""VictoriaMetricsCollector — queries /api/v1/query_range via MetricsQL/PromQL."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from n8n_analyzer.collectors.base import BaseCollector, PartialDataError
from n8n_analyzer.models.report import QueryRecord

logger = logging.getLogger(__name__)

# Type alias: list of (labels_dict, list[timestamp_float], list[value_str])
RangeResult = list[tuple[dict[str, str], list[float], list[str]]]


class VictoriaMetricsCollector(BaseCollector):
    """Query VictoriaMetrics /api/v1/query_range endpoint.

    Uses MetricsQL (compatible with PromQL) for all expressions.
    Note: prometheus-api-client is NOT used — it does not support MetricsQL
    extensions (e.g. keep_last_value, limitk, outlierIQR) available in VM.
    """

    async def query_range(
        self,
        promql: str,
        start: datetime,
        end: datetime,
        step: str,
        label_filter: dict[str, str] | None = None,
        is_primary: bool = False,
    ) -> tuple[RangeResult, QueryRecord]:
        """Execute a range query and return parsed results plus a QueryRecord.

        Args:
            promql: PromQL/MetricsQL expression.
            start: Query start time (UTC).
            end: Query end time (UTC).
            step: Resolution step, e.g. "5m" or "1m".
            label_filter: Optional dict of additional label selectors to inject.
                          E.g. {"instance": "wf001.*|wf008.*"} adds a label filter.
            is_primary: If True, raise httpx errors directly (SystemExit path).
                        If False, raise PartialDataError instead.

        Returns:
            (results, query_record) where results is a list of
            (labels, timestamps, values) tuples grouped by metric series.
        """
        # Inject label filter into the expression if provided
        expr = self._inject_label_filter(promql, label_filter)

        params: dict[str, Any] = {
            "query": expr,
            "start": start.timestamp(),
            "end": end.timestamp(),
            "step": step,
        }

        query_record = QueryRecord(
            data_source=self.base_url,
            expression=expr,
            step=step,
            time_from=start,
            time_to=end,
        )

        try:
            body = await self._get("/api/v1/query_range", params=params)
        except Exception as exc:
            if is_primary:
                raise
            raise PartialDataError(self.base_url, str(exc)) from exc

        if body.get("status") != "success":
            error_msg = body.get("error", "unknown error")
            if is_primary:
                raise RuntimeError(f"VictoriaMetrics query failed: {error_msg}")
            raise PartialDataError(self.base_url, f"VictoriaMetrics status!=success: {error_msg}")

        results: RangeResult = []
        for series in body.get("data", {}).get("result", []):
            labels: dict[str, str] = series.get("metric", {})
            timestamps = [float(v[0]) for v in series.get("values", [])]
            values = [str(v[1]) for v in series.get("values", [])]
            results.append((labels, timestamps, values))

        logger.debug("VM query returned %d series for: %s", len(results), expr[:80])
        return results, query_record

    @staticmethod
    def _inject_label_filter(expr: str, label_filter: dict[str, str] | None) -> str:
        """Naively append label selectors into the first metric selector in expr.

        This is a best-effort helper for simple expressions. For complex subqueries
        callers should pre-build the full expression with filters embedded.
        """
        if not label_filter:
            return expr
        filter_parts = ", ".join(
            f'{k}=~"{v}"' for k, v in label_filter.items()
        )
        # If the expression already has label braces, insert before closing }
        if "{" in expr and "}" in expr:
            return expr.replace("}", f", {filter_parts}}}", 1)
        # Otherwise find the first metric name and add braces
        # This handles simple bare metric names like: n8n_node_execution_duration_seconds_bucket
        import re  # noqa: PLC0415
        return re.sub(r"(\w+)", rf"\1{{{filter_parts}}}", expr, count=1)
