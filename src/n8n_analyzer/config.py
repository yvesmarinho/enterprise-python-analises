"""Config — load settings from .secrets/ and environment variables.

Constitution Principle III: all credentials must come from .secrets/ (perm 640).
No credential values may appear in log output.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


class ConfigError(Exception):
    """Raised when required configuration is missing or insecure."""


# Required environment variable names
# Stack architecture (from docker-compose.yaml in docs/Prometheus/):
#   Prometheus  — public HTTPS (Traefik), 15d retention, scrapes all targets.
#   VictoriaMetrics — internal only (http://victoriametrics:8428, no Traefik),
#                     12-month retention, receives remote_write from Prometheus.
# From a local analysis machine:
#   - PROMETHEUS_URL is always reachable (https://prometheus.vya.digital).
#   - VICTORIA_METRICS_URL requires SSH tunnel or running from inside wfdb01 network.
# ANA-001 uses VICTORIA_METRICS_URL when set (longer history); falls back to
# PROMETHEUS_URL (public, max 15d) when not set or unreachable.
_REQUIRED_VARS: list[str] = []

# Optional vars with defaults
_DEFAULTS = {
    "PROMETHEUS_URL": "https://prometheus.vya.digital",
    "LOKI_URL": "https://loki.vya.digital",
    "REQUEST_TIMEOUT_SECONDS": "30",
    "CORRELATION_WINDOW_SECONDS": "30",
}


def _check_secrets_permissions(secrets_dir: Path) -> None:
    """Raise ConfigError listing any .secrets/ files with permissions != 640."""
    if not secrets_dir.exists():
        return
    violations: list[str] = []
    for path in secrets_dir.iterdir():
        if path.is_file():
            mode = path.stat().st_mode & 0o777
            if mode != 0o640:
                violations.append(f"  {path.name}: {oct(mode)} (expected 0o640)")
    if violations:
        raise ConfigError(
            ".secrets/ permission violation(s) — fix with `chmod 640 .secrets/*`:\n"
            + "\n".join(violations)
        )


def _load_secrets_env(secrets_dir: Path) -> None:
    """Load .env* files from .secrets/ into the environment without logging values."""
    if not secrets_dir.exists():
        return
    for env_file in sorted(secrets_dir.glob("*.env*")):
        load_dotenv(env_file, override=False)
    # Also load .env.production if present
    production_env = secrets_dir / ".env.production"
    if production_env.exists():
        load_dotenv(production_env, override=False)


class Config:
    """Resolved configuration for one analyzer run."""

    def __init__(self, *, secrets_dir: Path | None = None, check_permissions: bool = True) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        if secrets_dir is None:
            secrets_dir = repo_root / ".secrets"

        # 1. Load .env.example (non-sensitive defaults) if present
        env_example = repo_root / ".env.example"
        if env_example.exists():
            load_dotenv(env_example, override=False)

        # 2. Load local .env (developer override, non-committed)
        local_env = repo_root / ".env"
        if local_env.exists():
            load_dotenv(local_env, override=True)

        # 3. Load from .secrets/
        if check_permissions:
            _check_secrets_permissions(secrets_dir)
        _load_secrets_env(secrets_dir)

        # 4. Apply defaults for optional vars
        for key, default in _DEFAULTS.items():
            os.environ.setdefault(key, default)

        # 5. Validate required vars
        missing = [k for k in _REQUIRED_VARS if not os.environ.get(k)]
        if missing:
            raise ConfigError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                "Set them in .secrets/.env.production or export them before running."
            )

        # 6. Assign (values never logged)
        # VictoriaMetrics: internal-only (no public DNS). Only reachable via
        # SSH tunnel to wfdb01 or when running directly on the server.
        # Falls back to Prometheus (public, 15d retention) when not set.
        vm_url = os.environ.get("VICTORIA_METRICS_URL", "").rstrip("/")
        prometheus_url_val = os.environ.get("PROMETHEUS_URL", "").rstrip("/")
        self.victoria_metrics_url: str = vm_url or prometheus_url_val
        self.prometheus_url: str = prometheus_url_val
        if not self.victoria_metrics_url:
            raise ConfigError(
                "Neither VICTORIA_METRICS_URL nor PROMETHEUS_URL is set."
                " Set at least one in .secrets/ or as an environment variable."
            )
        self.using_prometheus_fallback: bool = (not vm_url) and bool(prometheus_url_val)
        self.loki_url: str = os.environ.get("LOKI_URL", "").rstrip("/")
        self.prometheus_url: str = os.environ.get("PROMETHEUS_URL", "").rstrip("/")
        self.postgres_dsn: str | None = os.environ.get("POSTGRES_DSN")
        self.request_timeout_seconds: int = int(
            os.environ.get("REQUEST_TIMEOUT_SECONDS", "30")
        )
        self.correlation_window_seconds: int = int(
            os.environ.get("CORRELATION_WINDOW_SECONDS", "30")
        )

    def safe_repr(self) -> str:
        """Return config summary with all credential values redacted (for --dry-run)."""
        postgres_dsn_repr = "<set>" if self.postgres_dsn else "<not set>"
        vm_note = " (fallback: using Prometheus)" if self.using_prometheus_fallback else " (VictoriaMetrics)"
        return (
            f"victoria_metrics_url = {self.victoria_metrics_url}{vm_note}\n"
            f"prometheus_url       = {self.prometheus_url or '<not set>'}\n"
            f"loki_url             = {self.loki_url}\n"
            f"postgres_dsn         = {postgres_dsn_repr}\n"
            f"request_timeout      = {self.request_timeout_seconds}s\n"
            f"correlation_window   = {self.correlation_window_seconds}s\n"
        )
