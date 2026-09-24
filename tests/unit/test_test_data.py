import pytest
from openpyxl import Workbook

from framework.config import load_settings
from framework.test_data import load_default_payloads, load_test_cases

HEADER = [
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
    "quantity",
    "delivery[pincode]",
]


def _workbook(tmp_path, rows, payload_rows=()):
    wb = Workbook()
    ws = wb.active
    ws.title = "test_cases"
    ws.append(HEADER)
    for r in rows:
        ws.append(r)
    ws2 = wb.create_sheet("default_payloads")
    ws2.append(["api_name", "environment", "payload"])
    for r in payload_rows:
        ws2.append(r)
    path = tmp_path / "cases.xlsx"
    wb.save(path)
    return path


@pytest.mark.unit
def test_only_rows_marked_yes_are_loaded(tmp_path):
    path = _workbook(
        tmp_path,
        [
            ["Yes", "TC-1", "a", "create_order", "post", "/api/orders", "", 201, "", "", "3", ""],
            ["No", "TC-2", "b", "create_order", "POST", "/api/orders", "valid", 201, "", "", "", ""],
        ],
    )
    cases = load_test_cases(path)
    assert [c.tc_id for c in cases] == ["TC-1"]
    assert cases[0].method == "POST" and cases[0].auth == "valid"
    assert cases[0].overrides == {"quantity": "3"}  # blank override cells are ignored


@pytest.mark.unit
def test_leading_zeros_survive_as_text(tmp_path):
    path = _workbook(tmp_path, [["Yes", "TC-1", "a", "x", "POST", "/", "valid", 422, "", "", "", "060001"]])
    assert load_test_cases(path)[0].overrides["delivery[pincode]"] == "060001"


@pytest.mark.unit
def test_duplicate_ids_are_rejected(tmp_path):
    row = ["Yes", "TC-1", "a", "x", "POST", "/", "valid", 201, "", "", "", ""]
    with pytest.raises(ValueError, match="duplicate tc_id"):
        load_test_cases(_workbook(tmp_path, [row, row]))


@pytest.mark.unit
def test_bad_auth_mode_is_rejected(tmp_path):
    row = ["Yes", "TC-1", "a", "x", "POST", "/", "admin", 201, "", "", "", ""]
    with pytest.raises(ValueError, match="auth must be one of"):
        load_test_cases(_workbook(tmp_path, [row]))


@pytest.mark.unit
def test_environment_specific_payload_wins(tmp_path):
    path = _workbook(
        tmp_path,
        [],
        [
            ["create_order", "all", '{"quantity": 1}'],
            ["create_order", "qa", '{"quantity": 2}'],
        ],
    )
    assert load_default_payloads(path, "qa")["create_order"] == {"quantity": 2}
    assert load_default_payloads(path, "dev")["create_order"] == {"quantity": 1}


@pytest.mark.unit
def test_committed_workbook_is_valid():
    cases = load_test_cases(load_settings("local").test_data_file)
    assert len(cases) >= 10
    assert all(c.tc_id.startswith("TC-") for c in cases)
