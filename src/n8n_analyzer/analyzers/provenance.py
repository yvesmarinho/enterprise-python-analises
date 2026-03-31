"""ProvenanceGate — validates that analysis data originates from expected sources.

TASK-001: Gate de Proveniência ANA-001.

Ensures each VictoriaMetrics series satisfies two provenance rules:

  1. **Instance rule**: the ``instance`` label must match at least one of the
     ``allowed_instances`` regex patterns (e.g. ``["wf001", "wf008"]``).
     Pass ``allowed_instances=None`` to disable this check.

  2. **Job rule**: when the ``job`` label *is present* (it may be stripped by
     PromQL ``sum by`` aggregations), it must match ``expected_job`` exactly.
     Pass ``expected_job=None`` to disable this check.

Series that fail either rule are excluded from downstream analysis and
recorded as :class:`ProvenanceViolation` entries for audit / reporting.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Type alias matching VictoriaMetricsCollector.RangeResult
RangeResult = list[tuple[dict[str, str], list[float], list[str]]]


@dataclass(frozen=True)
class ProvenanceViolation:
    """A single series that failed the provenance gate."""

    labels: dict[str, str]
    reason: str


class ProvenanceGate:
    """Filter VictoriaMetrics series by expected ``job`` and ``instance`` labels.

    Args:
        allowed_instances: Regex patterns for valid ``instance`` label values.
            A series is accepted when *any* pattern matches the ``instance``
            label (via :func:`re.search`).  Pass ``None`` to skip the check.
        expected_job: When set, any series that carries a ``job`` label must
            match this value exactly.  Series *without* a ``job`` label (which
            is common after ``sum by`` aggregation) are always accepted.
    """

    def __init__(
        self,
        *,
        allowed_instances: list[str] | None = None,
        expected_job: str | None = None,
    ) -> None:
        self._instance_patterns: list[re.Pattern[str]] = (
            [re.compile(p) for p in allowed_instances]
            if allowed_instances is not None
            else []
        )
        self._expected_job = expected_job
        self._check_instances = allowed_instances is not None

    # ── public API ────────────────────────────────────────────────────────────

    def validate(
        self,
        results: RangeResult,
        *,
        source: str = "",
    ) -> tuple[RangeResult, list[ProvenanceViolation]]:
        """Filter *results* and return ``(clean_series, violations)``.

        Args:
            results: Raw series from
                :meth:`~n8n_analyzer.collectors.victoria_metrics.VictoriaMetricsCollector.query_range`.
            source: Human-readable source label used in log messages only.

        Returns:
            ``clean_series`` — accepted series to pass to downstream analysers.
            ``violations``   — series that were rejected (logged as warnings).
        """
        clean: RangeResult = []
        violations: list[ProvenanceViolation] = []

        for series in results:
            labels, _timestamps, _values = series
            violation = self._check(labels)
            if violation is None:
                clean.append(series)
            else:
                violations.append(violation)
                logger.warning(
                    "Provenance violation%s — labels=%r  reason=%r",
                    f" (source={source})" if source else "",
                    labels,
                    violation.reason,
                )

        if violations:
            logger.warning(
                "ProvenanceGate: %d/%d series rejected%s",
                len(violations),
                len(results),
                f" from {source}" if source else "",
            )

        return clean, violations

    # ── internal ──────────────────────────────────────────────────────────────

    def _check(self, labels: dict[str, str]) -> ProvenanceViolation | None:
        """Return a :class:`ProvenanceViolation` if *labels* fail, else ``None``."""
        # Job check: only enforced when the label is present in this series
        if self._expected_job is not None:
            job = labels.get("job")
            if job is not None and job != self._expected_job:
                return ProvenanceViolation(
                    labels=labels,
                    reason=(
                        f"job={job!r} does not match expected {self._expected_job!r}"
                    ),
                )

        # Instance check
        if self._check_instances:
            instance = labels.get("instance", "")
            if not any(p.search(instance) for p in self._instance_patterns):
                return ProvenanceViolation(
                    labels=labels,
                    reason=(
                        f"instance={instance!r} does not match allowed patterns "
                        f"{[p.pattern for p in self._instance_patterns]!r}"
                    ),
                )

        return None
