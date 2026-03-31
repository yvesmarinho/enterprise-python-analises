"""Unit tests for ProvenanceGate (TASK-001)."""

from __future__ import annotations

import pytest

from n8n_analyzer.analyzers.provenance import ProvenanceGate, ProvenanceViolation

# ── helpers ──────────────────────────────────────────────────────────────────

def _series(labels: dict[str, str]) -> tuple[dict[str, str], list[float], list[str]]:
    return (labels, [1.0, 2.0], ["0.5", "1.2"])


_VALID = {"instance": "wf001.vya.digital:9443", "job": "n8n", "workflow_id": "wf-1"}
_WRONG_JOB = {"instance": "wf001.vya.digital:9443", "job": "cadvisor", "workflow_id": "wf-2"}
_WRONG_HOST = {"instance": "unknown-host:9443", "job": "n8n", "workflow_id": "wf-3"}
# job stripped by sum-by aggregation — common in production histogram queries
_NO_JOB = {"instance": "wf008.vya.digital:9443", "workflow_id": "wf-4"}


# ── ProvenanceViolation ───────────────────────────────────────────────────────

class TestProvenanceViolation:
    def test_is_frozen(self) -> None:
        v = ProvenanceViolation(labels={"instance": "bad"}, reason="test")
        with pytest.raises(Exception):
            v.labels = {}  # type: ignore[misc]

    def test_fields_accessible(self) -> None:
        v = ProvenanceViolation(labels={"a": "b"}, reason="r")
        assert v.labels == {"a": "b"}
        assert v.reason == "r"


# ── ProvenanceGate.validate ───────────────────────────────────────────────────

class TestProvenanceGate:
    def test_empty_results_returns_empty_clean_and_no_violations(self) -> None:
        gate = ProvenanceGate(allowed_instances=["wf001", "wf008"], expected_job="n8n")
        clean, violations = gate.validate([])
        assert clean == []
        assert violations == []

    def test_valid_series_accepted(self) -> None:
        gate = ProvenanceGate(allowed_instances=["wf001", "wf008"], expected_job="n8n")
        clean, violations = gate.validate([_series(_VALID)])
        assert len(clean) == 1
        assert violations == []

    def test_wrong_job_rejected(self) -> None:
        gate = ProvenanceGate(allowed_instances=["wf001"], expected_job="n8n")
        clean, violations = gate.validate([_series(_WRONG_JOB)])
        assert clean == []
        assert len(violations) == 1
        assert "cadvisor" in violations[0].reason

    def test_wrong_instance_rejected(self) -> None:
        gate = ProvenanceGate(allowed_instances=["wf001", "wf008"], expected_job="n8n")
        clean, violations = gate.validate([_series(_WRONG_HOST)])
        assert clean == []
        assert len(violations) == 1
        assert "unknown-host" in violations[0].reason

    def test_missing_job_label_accepted_when_job_expected(self) -> None:
        """Series without job label (stripped by sum by) must still be accepted."""
        gate = ProvenanceGate(allowed_instances=["wf001", "wf008"], expected_job="n8n")
        clean, violations = gate.validate([_series(_NO_JOB)])
        assert len(clean) == 1
        assert violations == []

    def test_instance_check_disabled_when_none(self) -> None:
        gate = ProvenanceGate(allowed_instances=None, expected_job="n8n")
        # _WRONG_HOST has no job label mismatch and instance check is disabled
        clean, violations = gate.validate([_series(_WRONG_HOST)])
        assert len(clean) == 1
        assert violations == []

    def test_job_check_disabled_when_none(self) -> None:
        gate = ProvenanceGate(allowed_instances=["wf001"], expected_job=None)
        clean, violations = gate.validate([_series(_WRONG_JOB)])
        # job check off → only instance check; wf001 instance matches
        assert len(clean) == 1
        assert violations == []

    def test_both_checks_disabled(self) -> None:
        gate = ProvenanceGate(allowed_instances=None, expected_job=None)
        results = [_series(_WRONG_JOB), _series(_WRONG_HOST)]
        clean, violations = gate.validate(results)
        assert len(clean) == 2
        assert violations == []

    def test_mixed_series_partial_rejection(self) -> None:
        gate = ProvenanceGate(allowed_instances=["wf001", "wf008"], expected_job="n8n")
        results = [_series(_VALID), _series(_WRONG_HOST)]
        clean, violations = gate.validate(results, source="vm.local")
        assert len(clean) == 1
        assert len(violations) == 1
        assert clean[0][0] == _VALID
        assert violations[0].labels == _WRONG_HOST

    def test_multiple_violations_all_recorded(self) -> None:
        gate = ProvenanceGate(allowed_instances=["wf001"], expected_job="n8n")
        results = [_series(_WRONG_JOB), _series(_WRONG_HOST)]
        clean, violations = gate.validate(results)
        assert clean == []
        assert len(violations) == 2

    def test_instance_pattern_uses_regex_search(self) -> None:
        """Pattern 'wf00[18]' should match both wf001 and wf008 hosts."""
        gate = ProvenanceGate(allowed_instances=[r"wf00[18]"])
        clean, violations = gate.validate(
            [_series(_VALID), _series(_NO_JOB)]
        )
        assert len(clean) == 2
        assert violations == []

    def test_violation_reason_describes_mismatch(self) -> None:
        gate = ProvenanceGate(allowed_instances=["wf001"])
        _, violations = gate.validate([_series(_WRONG_HOST)])
        assert violations[0].reason.startswith("instance=")

    def test_clean_series_preserves_original_tuple(self) -> None:
        """Accepted series must be returned unmodified."""
        gate = ProvenanceGate(allowed_instances=["wf001"])
        original = _series(_VALID)
        clean, _ = gate.validate([original])
        assert clean[0] is original
