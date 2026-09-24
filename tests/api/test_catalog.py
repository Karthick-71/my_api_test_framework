import pytest

from framework.assertions import expect_message, expect_schema, expect_status


@pytest.mark.smoke
@pytest.mark.tc("TC-2001", "Health check responds without auth")
def test_health(api):
    resp = api.with_key(None).get("/health")
    expect_status(resp, 200)
    expect_schema(resp, "health")


@pytest.mark.smoke
@pytest.mark.tc("TC-2002", "List products returns priced catalogue")
def test_list_products(api):
    resp = api.get("/api/products")
    expect_status(resp, 200)
    expect_schema(resp, "product_list")


@pytest.mark.regression
@pytest.mark.tc("TC-2003", "Get existing user by id")
def test_get_user(api):
    resp = api.get("/api/users/1")
    expect_status(resp, 200)
    expect_schema(resp, "user")
    assert resp.data["user_id"] == 1


@pytest.mark.regression
@pytest.mark.tc("TC-2004", "Unknown user returns 404 error envelope")
def test_get_unknown_user(api):
    resp = api.get("/api/users/999")
    expect_status(resp, 404)
    expect_schema(resp, "error")
    expect_message(resp, "User not found")
