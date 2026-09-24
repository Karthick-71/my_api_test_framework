import statistics

import pytest

from framework.assertions import expect_json_content, expect_schema, expect_status, expect_within

JSON_ROUTES = ["/health", "/api/products", "/api/orders", "/api/users/1", "/api/orders/999999"]


@pytest.mark.contract
@pytest.mark.parametrize(
    "path",
    [
        pytest.param(p, id=p, marks=pytest.mark.tc(f"TC-40{i:02d}", f"JSON content type for GET {p}"))
        for i, p in enumerate(JSON_ROUTES, start=11)
    ],
)
def test_json_everywhere(api, path):
    expect_json_content(api.get(path))


@pytest.mark.contract
@pytest.mark.tc("TC-4001", "Unknown route returns error envelope")
def test_unknown_route(api):
    resp = api.get("/api/does-not-exist")
    expect_status(resp, 404)
    expect_schema(resp, "error")


@pytest.mark.perf
@pytest.mark.tc("TC-5001", "Product list stays within response budget")
def test_products_response_budget(api, settings):
    samples = [api.get("/api/products") for _ in range(20)]
    for resp in samples:
        expect_status(resp, 200)
    p95 = statistics.quantiles([r.elapsed_ms for r in samples], n=20)[-1]
    slowest = max(samples, key=lambda r: r.elapsed_ms)
    assert p95 <= settings.response_budget_ms, (
        f"p95 response time above {settings.response_budget_ms} ms budget for GET /api/products"
        f"\n  p95: {p95:.0f} ms, slowest: {slowest.elapsed_ms:.0f} ms"
    )
    expect_within(samples[0], settings.response_budget_ms * 3)  # first call includes connection setup
