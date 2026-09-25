# API Test Framework

[![API tests](https://github.com/Karthick-71/my_api_test_framework/actions/workflows/ci.yml/badge.svg)](https://github.com/Karthick-71/my_api_test_framework/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%20%7C%203.12-1a7a45)](pyproject.toml)
[![Reports](https://img.shields.io/badge/reports-GitHub%20Pages-2d5a8c)](https://karthick-71.github.io/my_api_test_framework/)

Data-driven REST API test automation with **Python + Pytest**. Test cases live in an **Excel workbook**,
so testers can add coverage without writing code. Every CI run feeds a **cross-build test history**
that shows flaky tests and groups failures by root cause.

**Live reports:** [latest run and test history](https://karthick-71.github.io/my_api_test_framework/)

---

## What it does

| Capability | How |
|---|---|
| Excel-driven test cases | One row = one test. `to_process = No` parks a case without deleting it. |
| Default payload + overrides | Each API has a baseline body. Rows override only what they test, including nested fields (`delivery[pincode]`) and negative cases (`__remove__`, `__null__`). |
| Multi-environment | `local`, `dev`, `qa`, `staging` and `prod` via env vars or `.env`. No secrets in code. |
| Contract checks | JSON Schema validation for every response shape, success and error. |
| Response-time budgets | p95 latency check per endpoint, budget set by `RESPONSE_BUDGET_MS`. |
| Self-contained runs | Locally and in CI, the session starts the API under test on a free port with a throwaway database. |
| Reports | pytest-html (per run), JUnit XML, and a cross-build history published to GitHub Pages. |
| AWS helpers (optional) | S3 upload/download of test data and reports, Athena queries, DynamoDB reads, for checking data landed where the API wrote it. |

## Cross-build test history

A normal test report shows one build. Questions like *"has this test ever passed?"*, *"is this flaky?"*
or *"are these 20 failures 20 problems or 3?"* need history that survives the build.

CI records every `main` run with
[**Playwright Test History**](https://github.com/ParthiCM/playwright-test-history) by Parthiban Murugan (MIT).
It reads JUnit XML, so it works for this Pytest suite too:

- **Table A**: every test × every build. A solid red band means chronically broken, an alternating one flaky.
- **Table B**: failing tests grouped by failure signature. Fixing one row clears every test in it.

To make the grouping useful for Pytest, `framework/reporting/triage_junit.py` writes a second JUnit file
in which:
- each test is named `TC-1001 'Create order with valid card payment'`;
- the first line of each failure is the error itself, not the failing source line.

Assertions keep that first line stable, so `/api/orders/17` and `/api/orders/42` failing the same way count
as **one cause**. In a simulated broken build (rotated API key), 22 failing tests grouped into 8 causes.

The history store is one small JSON file per build on the [`test-history`](../../tree/test-history) branch.
It lives outside any single workflow run, so it outlives artifact expiry.

## Fault-injection runs

Some builds in the history are **fault-injection runs**: real CI runs where known defects are deliberately
switched on in the API under test, to show the suite catching them and the history report tracing them.
They are labelled in the report as `main · faults: <names>`, and the landing page says so.

| Fault | Defect it switches on | Caught by |
|---|---|---|
| `no_qty_limit` | quantity above 100 accepted | TC-1007 |
| `tax_on_total` | 18% added to the order total | TC-3002 |
| `slow_products` | `GET /api/products` takes about a second | TC-5001 |
| `users_500` | `GET /api/users/{id}` returns 500 | TC-2003, TC-2004 |
| `delete_not_idempotent` | deleting a missing order returns 200 | TC-3003 |

To start one, go to **Actions → API tests → Run workflow** and enter the faults, or run:

```bash
gh workflow run ci.yml -f faults=users_500,slow_products
```

Faults are off unless `ORDERS_FAULTS` is set, and an unknown fault name stops the API from starting.

## Project structure

```text
framework/
  config.py              environment settings (env vars / .env)
  api_client.py          requests session: retries, timing, logging
  payload.py             default payload + bracket-notation overrides
  test_data.py           Excel test-case and default-payload loader
  assertions.py          status / message / schema / latency checks with triage-friendly messages
  schemas/               JSON Schemas for every response shape
  reporting/triage_junit.py   pytest plugin: JUnit for the history report
  integrations/aws.py    optional S3 / Athena / DynamoDB helpers
sut/orders_api.py        Orders API (FastAPI + SQLite): the system under test
test_data/api_test_cases.xlsx   test cases + default payloads
tools/build_test_data.py        reviewable source of the workbook
tests/
  api/                   data-driven, lifecycle, contract and performance tests
  unit/                  framework tests (payload rules, Excel loader, plugin, AWS helpers)
ci/                      history update + Pages site build
.github/workflows/ci.yml lint → test (3.9, 3.12) → history → GitHub Pages
```

## Run it

```bash
make install        # .venv + dependencies
make test           # full suite; starts the Orders API automatically
make smoke          # fast subset
open reports/report.html
```

Against a deployed environment:

```bash
TEST_ENV=qa QA_BASE_URL=https://orders-qa.example.com QA_API_KEY=... .venv/bin/python -m pytest -m "smoke or regression"
```

Markers: `smoke`, `regression`, `contract`, `perf`, `unit`.

## Adding a test case

1. Add a row to `CREATE_ORDER_CASES` in `tools/build_test_data.py`: the id, a title, the expected status
   and the fields to override.
2. Run `make data` to regenerate the workbook.
3. Run `make test`.

Testers can also edit `test_data/api_test_cases.xlsx` directly (it has dropdowns and a README sheet).
Mirror the change in the script so the diff stays reviewable.

## Bugs the suite caught in the API under test

- **Unknown routes returned FastAPI's default `{"detail": "Not Found"}` instead of the API's error envelope.**
  The handler was registered for FastAPI's `HTTPException`, but routing errors are raised as Starlette's.
  Caught by `TC-4001`.
- **`POST /api/orders` returned HTTP 200 while its body said `"code": 201`**, in the original mock API.
  It now returns a real 201.

## CI

`.github/workflows/ci.yml` runs on every push and pull request, and daily at 09:00 IST so drift shows up
even without commits:

1. **Lint:** ruff check and ruff format.
2. **Test:** Pytest on Python 3.9 and 3.12, with reports uploaded as artifacts.
3. **Publish (main only):** record the build in the history store, then deploy the history report and this
   run's HTML report to GitHub Pages.
