"""End-to-end order flow: create -> read -> list -> delete -> gone."""

import pytest

from framework.assertions import expect_message, expect_schema, expect_status


@pytest.mark.smoke
@pytest.mark.tc("TC-3001", "Order lifecycle create read list delete")
def test_order_lifecycle(api, default_payloads):
    created = api.post("/api/orders", default_payloads["create_order"])
    expect_status(created, 201)
    order_id = created.data["order_id"]

    fetched = api.get(f"/api/orders/{order_id}")
    expect_status(fetched, 200)
    expect_schema(fetched, "order")
    assert fetched.data == created.data, "GET returned different data than POST created"

    listed = api.get("/api/orders")
    expect_status(listed, 200)
    expect_schema(listed, "order_list")
    assert order_id in [o["order_id"] for o in listed.data], "New order missing from order list"

    deleted = api.delete(f"/api/orders/{order_id}")
    expect_status(deleted, 200)

    gone = api.get(f"/api/orders/{order_id}")
    expect_status(gone, 404)
    expect_message(gone, "Order not found")


@pytest.mark.regression
@pytest.mark.tc("TC-3002", "Order total equals unit price times quantity")
def test_order_total(api, new_order):
    products = api.get("/api/products")
    expect_status(products, 200)
    prices = {p["product_id"]: p["price"] for p in products.data}
    order = new_order(product_id=2, quantity=4)
    assert order["total"] == round(prices[2] * 4, 2), f"Order total wrong: {order['total']} for 4 x {prices[2]}"


@pytest.mark.regression
@pytest.mark.tc("TC-3003", "Deleting an order twice returns 404")
def test_delete_twice(api, new_order):
    order_id = new_order()["order_id"]
    expect_status(api.delete(f"/api/orders/{order_id}"), 200)
    second = api.delete(f"/api/orders/{order_id}")
    expect_status(second, 404)
    expect_schema(second, "error")


@pytest.mark.regression
@pytest.mark.tc("TC-3004", "Validation error names the invalid field")
def test_validation_details(api, default_payloads):
    body = {**default_payloads["create_order"], "quantity": 0}
    resp = api.post("/api/orders", body)
    expect_status(resp, 422)
    expect_schema(resp, "error")
    fields = [d["field"] for d in resp.json["details"]]
    assert "quantity" in fields, f"422 details do not mention quantity: {fields}"
