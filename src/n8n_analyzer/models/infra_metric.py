"""InfraMetricSnapshot — point-in-time reading of an infrastructure metric."""

from datetime import datetime

from pydantic import BaseModel, field_validator


class InfraMetricSnapshot(BaseModel):
    """A single metric value from Redis, DB, or external API at a given timestamp."""

    metric_name: str
    value: float
    timestamp: datetime
    source_label: str

    @field_validator("timestamp")
    @classmethod
    def must_be_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (UTC)")
        offset = v.utcoffset()
        if offset is not None and offset.total_seconds() != 0:
            raise ValueError("timestamp must be UTC (utcoffset=0)")
        return v

    model_config = {"frozen": True}
