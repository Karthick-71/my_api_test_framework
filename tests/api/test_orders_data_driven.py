"""POST /api/orders driven by test_data/api_test_cases.xlsx.

Each row with to_process = Yes becomes one test. Adding a case means adding a
row: no code change.
"""

import pytest

from framework.assertions import expect_message, expect_schema, expect_status
from framework.config import load_settings
from framework.payload import apply_overrides
from framework.test_data import load_test_cases

CASES = load_test_cases(load_settings().test_data_file)


def _client_for(api, auth: str):
    return {"valid": api, "none": api.with_key(None), "invalid": api.with_key("wrong-key")}[auth]


@pytest.mark.regression
@pytest.mark.parametrize(
    "case",
    [pytest.param(c, id=c.tc_id, marks=pytest.mark.tc(c.tc_id, c.title)) for c in CASES],
)
def test_create_order(api, default_payloads, case):
    payload = apply_overrides(default_payloads[case.api_name], case.overrides)

    resp = _client_for(api, case.auth).request(case.method, case.endpoint, json_body=payload)

    try:
        expect_status(resp, case.expected_status)
        if case.expected_message:
            expect_message(resp, case.expected_message)
        if case.schema:
            expect_schema(resp, case.schema)
    finally:
        if resp.status_code == 201 and resp.data:
            api.delete(f"/api/orders/{resp.data['order_id']}")
