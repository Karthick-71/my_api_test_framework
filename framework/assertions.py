"""Assertions with failure messages written for triage.

The first line of every failure message is stable across runs: no order ids,
timestamps or durations, just the kind of problem. That lets the history
report group failures by cause instead of listing one row per test.
Volatile details go on the following lines.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from urllib.parse import urlparse

from jsonschema import Draft202012Validator

from framework.api_client import ApiResponse

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"


def _context(resp: ApiResponse) -> str:
    return f"\n  request: {resp.method} {resp.url}\n  body: {resp.text[:500]}"


def expect_status(resp: ApiResponse, expected: int) -> None:
    if resp.status_code != expected:
        raise AssertionError(
            f"Expected HTTP {expected} but got {resp.status_code} for {resp.method} {_route(resp)}" + _context(resp)
        )


def expect_message(resp: ApiResponse, expected: str) -> None:
    if resp.message != expected:
        raise AssertionError(f"Expected message {expected!r} but got {resp.message!r}" + _context(resp))


def expect_json_content(resp: ApiResponse) -> None:
    ctype = resp.headers.get("content-type", resp.headers.get("Content-Type", ""))
    if "application/json" not in ctype:
        raise AssertionError(f"Expected a JSON response but got content-type {ctype!r}" + _context(resp))


def expect_within(resp: ApiResponse, budget_ms: float) -> None:
    if resp.elapsed_ms > budget_ms:
        raise AssertionError(
            f"Response slower than {budget_ms:.0f} ms budget for {resp.method} {_route(resp)}"
            f"\n  took: {resp.elapsed_ms:.0f} ms"
        )


@cache
def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / f"{name}.json").read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def expect_schema(resp: ApiResponse, name: str) -> None:
    errors = sorted(_validator(name).iter_errors(resp.json), key=lambda e: list(e.path))
    if errors:
        first = errors[0]
        where = "/".join(str(p) for p in first.path) or "<root>"
        raise AssertionError(
            f"Response does not match schema '{name}' at {where}: {first.validator} check failed"
            f"\n  detail: {first.message}" + _context(resp)
        )


def _route(resp: ApiResponse) -> str:
    """URL path with numeric ids collapsed, so /api/orders/17 and /api/orders/42 group together."""
    path = urlparse(resp.url).path
    return "/".join("{id}" if part.isdigit() else part for part in path.split("/"))
