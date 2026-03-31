"""
Audit logging for wf001 analysis scripts.
==========================================
Records execution context (hostname, git SHA, Python version, timestamps)
to tmp/scripts.audit_log in JSONL format (one JSON object per line).

Usage::

    from _audit import audit_start, audit_end

    def main():
        args = parser.parse_args()
        _ctx = audit_start(__file__, args)
        try:
            # ... script body ...
            audit_end(__file__, _ctx, outcome="ok", output_files=[...])
        except Exception:
            audit_end(__file__, _ctx, outcome="error")
            raise
"""

import json
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_AUDIT_LOG = _PROJECT_ROOT / "tmp" / "scripts.audit_log"


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=_PROJECT_ROOT,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _git_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=_PROJECT_ROOT,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _write(record: dict) -> None:
    _AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with _AUDIT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, default=str) + "\n")


def audit_start(script_path: str, args: object) -> dict:
    """Log script start. Returns a context dict to pass to audit_end."""
    script_name = Path(script_path).name
    args_dict = vars(args) if hasattr(args, "__dict__") else str(args)
    ctx = {
        "event": "start",
        "script": script_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "python_version": platform.python_version(),
        "git_sha": _git_sha(),
        "git_branch": _git_branch(),
        "pid": os.getpid(),
        "args": args_dict,
    }
    _write(ctx)
    print(
        f"[audit] {script_name} started | host={ctx['hostname']} "
        f"python={ctx['python_version']} sha={ctx['git_sha']} pid={ctx['pid']}",
        file=sys.stderr,
    )
    return ctx


def audit_end(
    script_path: str,
    start_ctx: dict,
    *,
    outcome: str,
    output_files: list[str] | None = None,
) -> None:
    """Log script end. outcome must be 'ok' or 'error'."""
    script_name = Path(script_path).name
    ts = datetime.now(timezone.utc)
    start_ts = datetime.fromisoformat(start_ctx["timestamp"])
    elapsed = round((ts - start_ts).total_seconds(), 2)
    record = {
        "event": "end",
        "script": script_name,
        "timestamp": ts.isoformat(),
        "hostname": start_ctx.get("hostname"),
        "git_sha": start_ctx.get("git_sha"),
        "git_branch": start_ctx.get("git_branch"),
        "pid": start_ctx.get("pid"),
        "outcome": outcome,
        "output_files": output_files or [],
        "elapsed_s": elapsed,
    }
    _write(record)
    status_icon = "✅" if outcome == "ok" else "❌"
    print(
        f"[audit] {status_icon} {script_name} {outcome} | elapsed={elapsed}s "
        f"| outputs={output_files or []}",
        file=sys.stderr,
    )
