"""Shared fixtures.

For TEST_ENV=local (the default) the session starts the Orders API itself on a
free port with a throwaway database, so `pytest` works on a fresh clone and in
CI with no other setup. For dev/qa/staging/prod it uses BASE_URL and API_KEY.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

import pytest
import requests

from framework.api_client import ApiClient
from framework.config import ROOT, Settings, load_settings
from framework.test_data import load_default_payloads

LOCAL_API_KEY = "local-test-key"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_healthy(url: str, proc: subprocess.Popen, timeout_s: float = 20) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"Orders API exited early with code {proc.returncode}")
        try:
            if requests.get(f"{url}/health", timeout=1).status_code == 200:
                return
        except requests.ConnectionError:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"Orders API did not become healthy within {timeout_s:.0f}s")


@pytest.fixture(scope="session")
def settings(tmp_path_factory) -> Settings:
    cfg = load_settings()
    if not cfg.is_local or cfg.base_url:
        yield cfg
        return

    port = _free_port()
    log_path = Path(os.getenv("SUT_LOG", ROOT / "reports" / "sut.log"))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "ORDERS_API_KEY": LOCAL_API_KEY,
        "ORDERS_DB": str(tmp_path_factory.mktemp("sut") / "orders.db"),
    }
    with open(log_path, "w") as log:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "sut.orders_api:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        base_url = f"http://127.0.0.1:{port}"
        try:
            _wait_healthy(base_url, proc)
            yield replace(cfg, base_url=base_url, api_key=LOCAL_API_KEY)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


@pytest.fixture(scope="session")
def api(settings) -> ApiClient:
    client = ApiClient(settings.base_url, settings.api_key, settings.timeout_s)
    yield client
    client.close()


@pytest.fixture(scope="session")
def default_payloads(settings) -> dict:
    return load_default_payloads(settings.test_data_file, settings.env)


@pytest.fixture
def new_order(api, default_payloads):
    """Create an order for a test and delete it afterwards, even if the test fails."""
    created = []

    def _create(**overrides):
        body = {**default_payloads["create_order"], **overrides}
        resp = api.post("/api/orders", body)
        assert resp.status_code == 201, f"Setup failed: could not create order ({resp.status_code})"
        created.append(resp.data["order_id"])
        return resp.data

    yield _create
    for order_id in created:
        api.delete(f"/api/orders/{order_id}")
