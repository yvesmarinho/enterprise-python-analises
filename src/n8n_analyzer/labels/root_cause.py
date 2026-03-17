"""RootCauseLabel enum and classify() logic for ANA-001 latency findings."""

from __future__ import annotations

from enum import Enum


class RootCauseLabel(str, Enum):
    """Structured root-cause taxonomy for N8N latency violations."""

    QUEUE_DEPTH_SPIKE = "QUEUE_DEPTH_SPIKE"
    DB_SLOW_QUERY = "DB_SLOW_QUERY"
    EXTERNAL_API_TIMEOUT = "EXTERNAL_API_TIMEOUT"
    NETWORK_LATENCY = "NETWORK_LATENCY"
    N8N_INTERNAL_ERROR = "N8N_INTERNAL_ERROR"
    UNKNOWN = "UNKNOWN"


def classify(
    event: object,
    snapshots: list[object],
    log_errors: list[dict] | None = None,
) -> RootCauseLabel:
    """Assign a root-cause label to a LatencyEvent.

    Decision priority (first match wins):
    1. redis_list_length spike           → QUEUE_DEPTH_SPIKE
    2. pg_stat_activity_max_tx_duration  → DB_SLOW_QUERY
    3. external_api_response_seconds     → EXTERNAL_API_TIMEOUT
    4. co-occurring Loki ERROR entry     → N8N_INTERNAL_ERROR
    5. source_host contains "wf008"      → NETWORK_LATENCY (Brazil probe)
    6. no evidence                       → UNKNOWN

    See T023 for the full classification logic implementation.
    """
    # Import here to avoid circular imports at module load time
    from n8n_analyzer.models.infra_metric import InfraMetricSnapshot  # noqa: PLC0415

    if log_errors is None:
        log_errors = []

    # Check each snapshot against known metric patterns
    for snap in snapshots:
        if not isinstance(snap, InfraMetricSnapshot):
            continue
        if "redis_list_length" in snap.metric_name:
            return RootCauseLabel.QUEUE_DEPTH_SPIKE
        if "pg_stat_activity" in snap.metric_name or "pg_slow" in snap.metric_name:
            return RootCauseLabel.DB_SLOW_QUERY
        if "external_api" in snap.metric_name or "chatwoot" in snap.metric_name:
            return RootCauseLabel.EXTERNAL_API_TIMEOUT

    if log_errors:
        return RootCauseLabel.N8N_INTERNAL_ERROR

    # Network latency: if the event originates from the Brazil probe (wf008)
    source = getattr(event, "source_host", "")
    if "wf008" in source:
        return RootCauseLabel.NETWORK_LATENCY

    return RootCauseLabel.UNKNOWN
