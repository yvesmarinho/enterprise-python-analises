from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from n8n_analyzer.analyzers.correlation import CorrelationAnalyzer
from n8n_analyzer.analyzers.geographic import GeographicAnalyzer
from n8n_analyzer.models.correlation_window import CorrelationWindow
from n8n_analyzer.models.latency_event import LatencyEvent
from n8n_analyzer.models.report import QueryRecord


class _FakeCorrelationVM:
    def __init__(self, center: datetime) -> None:
        self._center = center

    async def query_range(self, expr, from_dt, to_dt, step, _is_primary=False):
        query_record = QueryRecord(
            data_source="http://vm.local",
            expression=expr,
            step=step,
            time_from=from_dt,
            time_to=to_dt,
        )
        return [({"__name__": "redis_list_length", "instance": "wf001"}, [self._center.timestamp()], ["123.4"])], query_record


class _FakeGeographicVM:
    async def query_range(self, expr, from_dt, to_dt, step, _is_primary=False):
        query_record = QueryRecord(
            data_source="http://vm.local",
            expression=expr,
            step=step,
            time_from=from_dt,
            time_to=to_dt,
        )
        return [({"instance": "wf008"}, [1.0, 2.0], ["0.2", "0.4"])], query_record


@pytest.mark.asyncio
async def test_correlation_analyze_uses_labels_timestamps_values_order() -> None:
    center = datetime(2026, 3, 30, 17, 40, tzinfo=UTC)
    analyzer = CorrelationAnalyzer(
        vm=_FakeCorrelationVM(center),
        config=SimpleNamespace(correlation_window_seconds=30),
    )

    snapshots, queries = await analyzer.analyze(
        [CorrelationWindow(center_ts=center, window_seconds=30)],
        center,
        center,
    )

    assert len(queries) == 3
    assert len(snapshots) == 3
    assert snapshots[0].metric_name == "redis_list_length"
    assert snapshots[0].source_label == "wf001"
    assert snapshots[0].value == 123.4
    assert snapshots[0].timestamp == center


@pytest.mark.asyncio
async def test_geographic_analyze_uses_probe_values_not_timestamps() -> None:
    analyzer = GeographicAnalyzer(vm=_FakeGeographicVM(), config=SimpleNamespace())
    events = [
        LatencyEvent(
            workflow_id="wf1",
            workflow_name="Workflow 1",
            node_name="node-a",
            node_type="test",
            executed_at=datetime(2026, 3, 30, 17, 0, tzinfo=UTC),
            duration_seconds=0.09,
            source_host="wf001",
        ),
        LatencyEvent(
            workflow_id="wf2",
            workflow_name="Workflow 2",
            node_name="node-b",
            node_type="test",
            executed_at=datetime(2026, 3, 30, 17, 5, tzinfo=UTC),
            duration_seconds=0.12,
            source_host="wf008",
        ),
    ]

    breakdowns, queries = await analyzer.analyze(
        events,
        datetime(2026, 3, 30, 17, 0, tzinfo=UTC),
        datetime(2026, 3, 30, 18, 0, tzinfo=UTC),
    )

    assert len(queries) == 1
    assert breakdowns["wf001"].network_contribution_seconds == 0.0
    assert breakdowns["wf001"].application_latency_seconds == 0.09
    assert breakdowns["wf008"].network_contribution_seconds == pytest.approx(0.3)
    assert breakdowns["wf008"].application_latency_seconds == 0.0
