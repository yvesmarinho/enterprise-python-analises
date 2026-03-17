"""LokiCollector — queries /loki/api/v1/query_range for N8N container error logs."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from n8n_analyzer.collectors.base import BaseCollector, PartialDataError
from n8n_analyzer.models.report import QueryRecord

logger = logging.getLogger(__name__)

# Type alias: list of {"timestamp": str (nanoseconds), "line": str}
LogLine = dict[str, str]
LokiResult = list[LogLine]


class LokiCollector(BaseCollector):
    """Query Loki /loki/api/v1/query_range endpoint for log data.

    Always raises PartialDataError on connection failure — Loki is a secondary
    data source; the analyzer continues in partial mode without it (FR-014).
    """

    async def query_range(
        self,
        logql: str,
        start: datetime,
        end: datetime,
        limit: int = 5000,
    ) -> tuple[LokiResult, QueryRecord]:
        """Execute a LogQL range query.

        Args:
            logql: LogQL expression, e.g. '{container=~"n8n.*"} |= "ERROR"'.
            start: Query start time (UTC).
            end: Query end time (UTC).
            limit: Maximum number of log lines to return.

        Returns:
            (log_lines, query_record) where log_lines is a list of
            {"timestamp": "<nanoseconds>", "line": "<log text>"} dicts.

        Raises:
            PartialDataError: On any connection or Loki-side error.
        """
        params: dict[str, Any] = {
            "query": logql,
            "start": str(int(start.timestamp() * 1e9)),  # nanoseconds
            "end": str(int(end.timestamp() * 1e9)),
            "limit": str(limit),
            "direction": "forward",
        }

        query_record = QueryRecord(
            data_source=self.base_url,
            expression=logql,
            step="—",  # Loki log queries do not use a numeric step
            time_from=start,
            time_to=end,
        )

        try:
            body = await self._get("/loki/api/v1/query_range", params=params)
        except Exception as exc:
            raise PartialDataError(self.base_url, f"Loki unreachable: {exc}") from exc

        if body.get("status") != "success":
            error_msg = body.get("error", "unknown error")
            raise PartialDataError(self.base_url, f"Loki status!=success: {error_msg}")

        log_lines: LokiResult = []
        for stream in body.get("data", {}).get("result", []):
            for entry in stream.get("values", []):
                log_lines.append({"timestamp": str(entry[0]), "line": str(entry[1])})

        logger.debug("Loki query returned %d log lines", len(log_lines))
        return log_lines, query_record
