"""Excel-driven test cases.

The workbook has two sheets:

`test_cases`: one row per test case. Fixed columns describe the case, and any
other non-empty column is a payload override (see framework/payload.py).
Rows with to_process != "Yes" are skipped, so a case can be parked without
deleting it.

    to_process | tc_id   | title | api_name     | method | endpoint    | auth  |
    expected_status | expected_message | schema | quantity | delivery[pincode] ...

`default_payloads`: the baseline request body per API and environment
("all" matches every environment).

    api_name | environment | payload (JSON)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd

META_COLUMNS = (
    "to_process",
    "tc_id",
    "title",
    "api_name",
    "method",
    "endpoint",
    "auth",
    "expected_status",
    "expected_message",
    "schema",
)
AUTH_MODES = ("valid", "none", "invalid")


@dataclass(frozen=True)
class ApiTestCase:
    tc_id: str
    title: str
    api_name: str
    method: str
    endpoint: str
    auth: str
    expected_status: int
    expected_message: Optional[str]
    schema: Optional[str]
    overrides: dict = field(default_factory=dict)


def _blank(value) -> bool:
    return value is None or (isinstance(value, float) and pd.isna(value)) or str(value).strip() in ("", "nan")


def _read_sheet(path: Path, sheet: str) -> pd.DataFrame:
    # dtype=str keeps "007" as "007" and lets payload.coerce decide types later.
    return pd.read_excel(path, sheet_name=sheet, dtype=str, engine="openpyxl")


def load_test_cases(path: Path, sheet: str = "test_cases") -> list[ApiTestCase]:
    df = _read_sheet(path, sheet)
    missing = [c for c in META_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}:{sheet} is missing columns: {', '.join(missing)}")

    cases, seen = [], set()
    for row_no, row in enumerate(df.to_dict("records"), start=2):  # row 1 is the header
        if str(row["to_process"]).strip().lower() != "yes":
            continue

        tc_id = str(row["tc_id"]).strip()
        if tc_id in seen:
            raise ValueError(f"{path.name}:{sheet} row {row_no}: duplicate tc_id {tc_id}")
        seen.add(tc_id)

        auth = str(row["auth"]).strip().lower() if not _blank(row["auth"]) else "valid"
        if auth not in AUTH_MODES:
            raise ValueError(f"{path.name}:{sheet} row {row_no}: auth must be one of {AUTH_MODES}, got {auth!r}")

        overrides = {k: v for k, v in row.items() if k not in META_COLUMNS and not _blank(v)}
        cases.append(
            ApiTestCase(
                tc_id=tc_id,
                title=str(row["title"]).strip(),
                api_name=str(row["api_name"]).strip(),
                method=str(row["method"]).strip().upper(),
                endpoint=str(row["endpoint"]).strip(),
                auth=auth,
                expected_status=int(float(row["expected_status"])),
                expected_message=None if _blank(row["expected_message"]) else str(row["expected_message"]).strip(),
                schema=None if _blank(row["schema"]) else str(row["schema"]).strip(),
                overrides=overrides,
            )
        )
    return cases


def load_default_payloads(path: Path, env: str, sheet: str = "default_payloads") -> dict[str, dict]:
    """{api_name: payload} for `env`. An env-specific row beats an "all" row."""
    df = _read_sheet(path, sheet)
    payloads: dict[str, dict] = {}
    for rank in ("all", env):  # later rank wins
        for row in df.to_dict("records"):
            if str(row["environment"]).strip().lower() == rank:
                payloads[str(row["api_name"]).strip()] = json.loads(row["payload"])
    return payloads
