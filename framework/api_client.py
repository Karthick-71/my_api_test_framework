"""Thin HTTP client used by every API test.

- one pooled `requests.Session`
- retries on connection errors and 502/503/504 for idempotent calls only
- response time captured on every call
- request/response logged with the API key redacted
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from framework.logger import get_logger

log = get_logger(__name__)


@dataclass
class ApiResponse:
    method: str
    url: str
    status_code: int
    elapsed_ms: float
    headers: dict = field(repr=False)
    text: str = field(repr=False)

    @property
    def json(self) -> Any:
        try:
            return json.loads(self.text) if self.text else None
        except ValueError:
            return None

    @property
    def data(self) -> Any:
        body = self.json
        return body.get("data") if isinstance(body, dict) else None

    @property
    def message(self) -> Optional[str]:
        body = self.json
        return body.get("message") if isinstance(body, dict) else None


class ApiClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout_s: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_s = timeout_s
        self.session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=(502, 503, 504),
            allowed_methods=frozenset({"GET", "HEAD", "OPTIONS", "DELETE"}),
            raise_on_status=False,
        )
        self.session.mount("http://", HTTPAdapter(max_retries=retry))
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.headers.update({"Accept": "application/json", "User-Agent": "api-test-framework/2.0"})

    def with_key(self, api_key: Optional[str]) -> ApiClient:
        """Same target, different credentials (used by auth tests)."""
        return ApiClient(self.base_url, api_key, self.timeout_s)

    def request(self, method: str, path: str, *, json_body: Any = None, params: dict | None = None) -> ApiResponse:
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {"X-API-Key": self.api_key} if self.api_key else {}

        started = time.perf_counter()
        resp = self.session.request(
            method.upper(), url, json=json_body, params=params, headers=headers, timeout=self.timeout_s
        )
        elapsed_ms = (time.perf_counter() - started) * 1000

        log.info("%s %s -> %s (%.0f ms)", method.upper(), url, resp.status_code, elapsed_ms)
        if json_body is not None:
            log.debug("request body: %s", json.dumps(json_body)[:2000])
        log.debug("response body: %s", resp.text[:2000])

        return ApiResponse(method.upper(), url, resp.status_code, elapsed_ms, dict(resp.headers), resp.text)

    def get(self, path: str, **kw) -> ApiResponse:
        return self.request("GET", path, **kw)

    def post(self, path: str, body: Any = None, **kw) -> ApiResponse:
        return self.request("POST", path, json_body=body, **kw)

    def delete(self, path: str, **kw) -> ApiResponse:
        return self.request("DELETE", path, **kw)

    def close(self) -> None:
        self.session.close()
