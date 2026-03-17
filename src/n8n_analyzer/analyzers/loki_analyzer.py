"""LokiAnalyzer — query Loki for N8N error logs and correlate with violations.

Queries Loki for {container=~"n8n.*"} |= "ERROR" across the full analysis
window. Returns:
  - total error count
  - top-N error types by frequency
  - list of error entries co-occurring within ±30 s of a LatencyEvent

Raises PartialDataError on Loki unreachability (FR-012, FR-014).
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from n8n_analyzer.collectors.base import PartialDataError
from n8n_analyzer.models.report import QueryRecord

if TYPE_CHECKING:
    from n8n_analyzer.collectors.loki import LokiCollector
    from n8n_analyzer.models.latency_event import LatencyEvent


# LogQL that captures all N8N error log lines
_ERROR_LOGQL = '{container=~"n8n.*"} |= "ERROR"'

# Regex to extract the first TOKEN_ALLCAPS or "error-like" word from a log line
_ERROR_TYPE_RE = re.compile(r"\b([A-Z][A-Z0-9_]{2,}(?:Error|ERROR|Exception)?)\b")


class LokiAnalyzer:
    """Query Loki and correlate errors with latency violations."""

    def __init__(self, loki: "LokiCollector") -> None:
        self._loki = loki

    async def analyze(
        self,
        from_dt: datetime,
        to_dt: datetime,
        latency_events: list["LatencyEvent"],
        top_n: int = 10,
        correlation_window_seconds: float = 30.0,
    ) -> tuple[dict[str, Any], list[QueryRecord]]:
        """Return summary dict and list of query records.

        Returns
        -------
        tuple[dict, list[QueryRecord]]
            dict keys:
              "total_errors" : int
              "top_errors"   : list[{"error_type": str, "count": int}]
              "correlated"   : list[{"timestamp": str, "line": str, "latency_event_id": str}]
        """
        try:
            result, qr = await self._loki.query_range(
                _ERROR_LOGQL,
                from_dt,
                to_dt,
                limit=5000,
            )
        except PartialDataError:
            raise
        except Exception as exc:
            raise PartialDataError("loki", str(exc)) from exc

        # result is list[{"stream": dict, "values": list[[ns_ts, line]]}]
        all_entries: list[tuple[datetime, str]] = []
        for stream_block in result:
            for ns_ts, line in stream_block.get("values", []):
                try:
                    ts = datetime.fromtimestamp(int(ns_ts) / 1e9, tz=timezone.utc)
                    all_entries.append((ts, line))
                except (ValueError, TypeError, OverflowError):
                    continue

        total_errors = len(all_entries)

        # Count error types by extracting the first upper-case token
        counter: Counter[str] = Counter()
        for _, line in all_entries:
            m = _ERROR_TYPE_RE.search(line)
            error_type = m.group(1) if m else "UNKNOWN"
            counter[error_type] += 1

        top_errors = [
            {"error_type": et, "count": cnt}
            for et, cnt in counter.most_common(top_n)
        ]

        # Correlate: find log entries within ±window_seconds of a violation
        half = timedelta(seconds=correlation_window_seconds)
        violation_times = [
            e.executed_at for e in latency_events if e.status == "violation"
        ]
        correlated: list[dict[str, str]] = []
        for ts, line in all_entries:
            for v_ts in violation_times:
                if abs((ts - v_ts).total_seconds()) <= half.total_seconds():
                    correlated.append(
                        {
                            "timestamp": ts.isoformat(),
                            "line": line[:200],
                            "nearest_violation_ts": v_ts.isoformat(),
                        }
                    )
                    break  # one match per log line is sufficient

        summary: dict[str, Any] = {
            "total_errors": total_errors,
            "top_errors": top_errors,
            "correlated": correlated,
        }

        return summary, [qr]
