"""Environment configuration.

Every value can come from an environment variable or a `.env` file, so the
same suite runs locally, in CI, or against a deployed dev/qa/staging/prod
environment without code changes. Secrets never live in this file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # python-dotenv is optional at runtime
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

ROOT = Path(__file__).resolve().parent.parent
ENVIRONMENTS = ("local", "dev", "qa", "staging", "prod")


@dataclass(frozen=True)
class Settings:
    env: str
    base_url: str
    api_key: str
    timeout_s: float
    response_budget_ms: int
    test_data_file: Path

    @property
    def is_local(self) -> bool:
        return self.env == "local"


def load_settings(env: str | None = None) -> Settings:
    """Build Settings for `env` (default: $TEST_ENV, else "local").

    For local runs the base URL and key may be empty: the test session starts
    the Orders API itself and fills them in. Remote environments must provide
    BASE_URL and API_KEY (or <ENV>_BASE_URL / <ENV>_API_KEY).
    """
    if load_dotenv is not None:
        load_dotenv(ROOT / ".env", override=False)

    env = (env or os.getenv("TEST_ENV") or "local").lower()
    if env not in ENVIRONMENTS:
        raise ValueError(f"Unknown environment '{env}'. Use one of: {', '.join(ENVIRONMENTS)}")

    prefix = env.upper()
    base_url = os.getenv(f"{prefix}_BASE_URL") or os.getenv("BASE_URL") or ""
    api_key = os.getenv(f"{prefix}_API_KEY") or os.getenv("API_KEY") or ""

    if env != "local" and not (base_url and api_key):
        raise ValueError(f"Environment '{env}' needs BASE_URL and API_KEY (or {prefix}_BASE_URL / {prefix}_API_KEY)")

    return Settings(
        env=env,
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        timeout_s=float(os.getenv("API_TIMEOUT_S", "10")),
        response_budget_ms=int(os.getenv("RESPONSE_BUDGET_MS", "800")),
        test_data_file=Path(os.getenv("TEST_DATA_FILE", ROOT / "test_data" / "api_test_cases.xlsx")),
    )
