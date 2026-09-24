"""Generate test_data/api_test_cases.xlsx.

The workbook is what testers edit day to day. This script is its reviewable
source: a diff here shows exactly which cases changed, where a binary .xlsx
diff shows nothing. Run it after editing the tables below:

    python tools/build_test_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

OUT = Path(__file__).resolve().parent.parent / "test_data" / "api_test_cases.xlsx"

META = [
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
]
OVERRIDES = ["user_id", "product_id", "quantity", "payment_method", "delivery[address]", "delivery[pincode]"]

# (to_process, tc_id, title, auth, expected_status, expected_message, schema, overrides)
CREATE_ORDER_CASES = [
    ("Yes", "TC-1001", "Create order with valid card payment", "valid", 201, "Order created", "order", {}),
    ("Yes", "TC-1002", "Create order paid by UPI", "valid", 201, "Order created", "order", {"payment_method": "upi"}),
    (
        "Yes",
        "TC-1003",
        "Create cash-on-delivery order",
        "valid",
        201,
        "Order created",
        "order",
        {"payment_method": "cod"},
    ),
    (
        "Yes",
        "TC-1004",
        "Create order at maximum quantity 100",
        "valid",
        201,
        "Order created",
        "order",
        {"quantity": 100},
    ),
    (
        "Yes",
        "TC-1005",
        "Create order for second user and product",
        "valid",
        201,
        "Order created",
        "order",
        {"user_id": 2, "product_id": 2, "quantity": 3},
    ),
    ("Yes", "TC-1006", "Reject quantity zero", "valid", 422, "Validation failed", "error", {"quantity": 0}),
    ("Yes", "TC-1007", "Reject quantity above 100", "valid", 422, "Validation failed", "error", {"quantity": 101}),
    ("Yes", "TC-1008", "Reject non-numeric quantity", "valid", 422, "Validation failed", "error", {"quantity": "two"}),
    ("Yes", "TC-1009", "Reject unknown user", "valid", 400, "Invalid user_id", "error", {"user_id": 999}),
    ("Yes", "TC-1010", "Reject unknown product", "valid", 400, "Invalid product_id", "error", {"product_id": 999}),
    (
        "Yes",
        "TC-1011",
        "Reject unsupported payment method",
        "valid",
        422,
        "Validation failed",
        "error",
        {"payment_method": "cheque"},
    ),
    (
        "Yes",
        "TC-1012",
        "Reject malformed pincode",
        "valid",
        422,
        "Validation failed",
        "error",
        {"delivery[pincode]": "60A001"},
    ),
    (
        "Yes",
        "TC-1013",
        "Reject order without delivery address",
        "valid",
        422,
        "Validation failed",
        "error",
        {"delivery[address]": "__remove__"},
    ),
    ("Yes", "TC-1014", "Reject null user id", "valid", 422, "Validation failed", "error", {"user_id": "__null__"}),
    ("Yes", "TC-1015", "Reject request without API key", "none", 403, "Invalid or missing API key", "error", {}),
    ("Yes", "TC-1016", "Reject request with wrong API key", "invalid", 403, "Invalid or missing API key", "error", {}),
    (
        "No",
        "TC-1017",
        "Bulk order discount (feature not built yet)",
        "valid",
        201,
        "Order created",
        "order",
        {"quantity": 50},
    ),
]

DEFAULT_PAYLOADS = [
    (
        "create_order",
        "all",
        {
            "user_id": 1,
            "product_id": 1,
            "quantity": 1,
            "payment_method": "card",
            "delivery": {"address": "12 Anna Salai, Chennai", "pincode": "600002"},
        },
    ),
]

HEADER_FILL = PatternFill("solid", fgColor="1A7A45")
OVERRIDE_FILL = PatternFill("solid", fgColor="2D5A8C")


def style_header(ws, overrides_from: int | None = None) -> None:
    for idx, cell in enumerate(ws[1], start=1):
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = OVERRIDE_FILL if overrides_from and idx >= overrides_from else HEADER_FILL
        cell.alignment = Alignment(vertical="center")
    ws.freeze_panes = "C2"
    for col in ws.columns:
        width = max(len(str(c.value or "")) for c in col) + 2
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max(width, 10), 48)


def main() -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "test_cases"
    ws.append(META + OVERRIDES)
    for to_process, tc_id, title, auth, status, message, schema, overrides in CREATE_ORDER_CASES:
        ws.append(
            [to_process, tc_id, title, "create_order", "POST", "/api/orders", auth, status, message, schema]
            + [overrides.get(col, "") for col in OVERRIDES]
        )
    style_header(ws, overrides_from=len(META) + 1)

    yes_no = DataValidation(type="list", formula1='"Yes,No"', allow_blank=False)
    auth = DataValidation(type="list", formula1='"valid,none,invalid"', allow_blank=True)
    ws.add_data_validation(yes_no)
    ws.add_data_validation(auth)
    yes_no.add(f"A2:A{ws.max_row + 200}")
    auth.add(f"G2:G{ws.max_row + 200}")

    ws2 = wb.create_sheet("default_payloads")
    ws2.append(["api_name", "environment", "payload"])
    for api_name, env, payload in DEFAULT_PAYLOADS:
        ws2.append([api_name, env, json.dumps(payload)])
    style_header(ws2)

    ws3 = wb.create_sheet("README")
    for line in [
        "How to use this workbook",
        "test_cases: one row per case. Set to_process to No to park a case without deleting it.",
        "Blue columns are payload overrides applied on top of default_payloads. Leave blank to keep the default.",
        "Nested fields use brackets: delivery[pincode]. Special values: __remove__, __null__, __empty__.",
        'Numbers and true/false are sent as JSON types. Wrap in quotes ("5") to send a string.',
        "auth: valid (default) | none (no API key) | invalid (wrong key).",
        "Source of truth is tools/build_test_data.py. Edit there and re-run it, then commit both files.",
    ]:
        ws3.append([line])
    ws3["A1"].font = Font(bold=True, size=13)
    ws3.column_dimensions["A"].width = 110

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"wrote {OUT.relative_to(OUT.parent.parent)} ({len(CREATE_ORDER_CASES)} cases)")


if __name__ == "__main__":
    main()
