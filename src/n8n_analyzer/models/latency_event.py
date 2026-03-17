"""LatencyEvent — a single N8N node execution that exceeded the latency threshold."""

from datetime import datetime

from pydantic import BaseModel, field_validator


class LatencyEvent(BaseModel):
    """A node execution recorded from the observability stack."""

    workflow_id: str
    workflow_name: str
    node_name: str
    node_type: str
    executed_at: datetime
    duration_seconds: float
    source_host: str
    # Status: "violation" if p95 >= 1s, "clean" otherwise
    status: str = "clean"

    @field_validator("executed_at")
    @classmethod
    def must_be_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("executed_at must be timezone-aware (UTC)")
        offset = v.utcoffset()
        if offset is not None and offset.total_seconds() != 0:
            raise ValueError("executed_at must be UTC (utcoffset=0)")
        return v

    model_config = {"frozen": True}
