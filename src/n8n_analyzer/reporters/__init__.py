"""Reporters sub-package — build_filename and report renderer exports."""

from __future__ import annotations

from datetime import datetime


def build_filename(from_dt: datetime, to_dt: datetime, ext: str) -> str:
    """Return a deterministic report filename including the analysis date range.

    Format: n8n_perf_ANA001_<FROM>_<TO>_<GENERATED_AT>.<ext>
    Dates use YYYYMMDD; timestamp uses YYYYMMDDTHHmmss format.

    Example: n8n_perf_ANA001_20260101_20260317_20260317T172412.md
    """
    from_str = from_dt.strftime("%Y%m%d")
    to_str = to_dt.strftime("%Y%m%d")
    now_str = datetime.now().strftime("%Y%m%dT%H%M%S")
    return f"n8n_perf_ANA001_{from_str}_{to_str}_{now_str}.{ext}"
