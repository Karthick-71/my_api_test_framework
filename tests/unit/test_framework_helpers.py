from datetime import datetime

import pytest

from framework.api_client import ApiResponse
from framework.assertions import _route, expect_schema, expect_status
from framework.config import load_settings
from framework.integrations.aws import AthenaHelper, DynamoDBHelper
from framework.utils import run_id, split_path


def _resp(status=200, text='{"status": "success"}', url="http://h/api/orders/42"):
    return ApiResponse("GET", url, status, 12.0, {"content-type": "application/json"}, text)


@pytest.mark.unit
def test_status_failure_message_is_stable_across_ids():
    with pytest.raises(AssertionError) as a:
        expect_status(_resp(500, url="http://h/api/orders/17"), 200)
    with pytest.raises(AssertionError) as b:
        expect_status(_resp(500, url="http://h/api/orders/42"), 200)
    first = lambda e: str(e.value).splitlines()[0]  # noqa: E731
    assert first(a) == first(b) == "Expected HTTP 200 but got 500 for GET /api/orders/{id}"


@pytest.mark.unit
def test_schema_failure_names_the_field():
    body = '{"status": "success", "code": 200, "message": "ok", "data": {"user_id": "1", "name": "K", "role": "QA"}}'
    with pytest.raises(AssertionError, match="schema 'user' at data/user_id"):
        expect_schema(_resp(text=body), "user")


@pytest.mark.unit
def test_route_collapses_numeric_ids():
    assert _route(_resp(url="http://h/api/users/7")) == "/api/users/{id}"


@pytest.mark.unit
def test_remote_env_requires_url_and_key(monkeypatch):
    for var in ("BASE_URL", "API_KEY", "QA_BASE_URL", "QA_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(ValueError, match="needs BASE_URL and API_KEY"):
        load_settings("qa")
    monkeypatch.setenv("QA_BASE_URL", "https://qa.example.com/")
    monkeypatch.setenv("QA_API_KEY", "k")
    assert load_settings("qa").base_url == "https://qa.example.com"


@pytest.mark.unit
def test_unknown_env_is_rejected():
    with pytest.raises(ValueError, match="Unknown environment"):
        load_settings("uat")


@pytest.mark.unit
def test_utils():
    assert run_id(datetime(2026, 9, 25, 14, 3, 11)) == "2026_09_25_14_03_11"
    assert split_path("/a/b/file.xlsx") == ("/a/b", "file.xlsx")
    assert split_path("C:\\data\\file.xlsx") == ("C:\\data", "file.xlsx")
    assert split_path("") == ("", "")


class _FakeAthena:
    def __init__(self, states):
        self.states = list(states)

    def start_query_execution(self, **_):
        return {"QueryExecutionId": "q1"}

    def get_query_execution(self, QueryExecutionId):
        return {"QueryExecution": {"Status": {"State": self.states.pop(0)}}}

    def get_query_results(self, QueryExecutionId):
        return {
            "ResultSet": {
                "Rows": [
                    {"Data": [{"VarCharValue": "order_id"}, {"VarCharValue": "status"}]},
                    {"Data": [{"VarCharValue": "7"}, {"VarCharValue": "CREATED"}]},
                ]
            }
        }


@pytest.mark.unit
def test_athena_waits_then_returns_rows():
    athena = AthenaHelper(_FakeAthena(["QUEUED", "RUNNING", "SUCCEEDED"]), sleep=lambda _: None)
    assert athena.run("select 1", "db", "s3://bucket/out/") == [{"order_id": "7", "status": "CREATED"}]


@pytest.mark.unit
def test_athena_times_out_instead_of_polling_forever():
    athena = AthenaHelper(_FakeAthena(["RUNNING"] * 10), sleep=lambda _: None)
    with pytest.raises(TimeoutError):
        athena.run("select 1", "db", "s3://bucket/out/", timeout_s=4, poll_s=2)


@pytest.mark.unit
def test_dynamodb_typed_json_to_python():
    item = {
        "id": {"N": "7"},
        "price": {"N": "25.75"},
        "tags": {"L": [{"S": "a"}]},
        "meta": {"M": {"ok": {"BOOL": True}, "note": {"NULL": True}}},
    }
    assert DynamoDBHelper.to_python(item) == {
        "id": 7,
        "price": 25.75,
        "tags": ["a"],
        "meta": {"ok": True, "note": None},
    }
