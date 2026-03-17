"""CorrelationWindow — time interval around LatencyEvents used for infra queries."""

from datetime import datetime

from pydantic import BaseModel, field_validator

from n8n_analyzer.models.latency_event import LatencyEvent


class CorrelationWindow(BaseModel):
    """A time window centered on a latency spike, used to query correlated metrics."""

    center_ts: datetime
    window_seconds: int = 30
    events: list[LatencyEvent] = []

    @field_validator("center_ts")
    @classmethod
    def must_be_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("center_ts must be timezone-aware (UTC)")
        if v.utcoffset().total_seconds() != 0:
            raise ValueError("center_ts must be UTC (utcoffset=0)")
        return v

    model_config = {"frozen": False}
