"""Optional AWS helpers for test data and results.

Typical uses in a pipeline:
- S3: pull the test-case workbook before a run, push reports after it
- Athena: verify that records an API wrote landed in the data lake
- DynamoDB: verify a record the API is supposed to persist

boto3 is imported lazily and is not in requirements.txt. Install it with
`pip install -r requirements-aws.txt`. Credentials come from the standard AWS
chain (env vars, ~/.aws profile, or an IAM role in CI) and never from code.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

from framework.logger import get_logger

log = get_logger(__name__)

TERMINAL_STATES = ("SUCCEEDED", "FAILED", "CANCELLED")


def aws_session(profile: Optional[str] = None, region: Optional[str] = None):
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("boto3 is not installed: pip install -r requirements-aws.txt") from exc
    return boto3.Session(profile_name=profile, region_name=region)


class S3Helper:
    def __init__(self, client):
        self.client = client

    def upload(self, local_path: str | Path, bucket: str, key: str) -> None:
        self.client.upload_file(str(local_path), bucket, key)
        log.info("uploaded %s -> s3://%s/%s", local_path, bucket, key)

    def upload_dir(self, local_dir: str | Path, bucket: str, prefix: str) -> int:
        """Upload every file under local_dir, e.g. a run's reports/ folder. Returns the file count."""
        base = Path(local_dir)
        files = [p for p in base.rglob("*") if p.is_file()]
        for path in files:
            self.upload(path, bucket, f"{prefix.rstrip('/')}/{path.relative_to(base).as_posix()}")
        return len(files)

    def download(self, bucket: str, key: str, local_path: str | Path) -> Path:
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(bucket, key, str(local_path))
        log.info("downloaded s3://%s/%s -> %s", bucket, key, local_path)
        return Path(local_path)

    def read_text(self, bucket: str, key: str) -> str:
        return self.client.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")

    def list_keys(self, bucket: str, prefix: str = "") -> list[str]:
        keys: list[str] = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            keys.extend(obj["Key"] for obj in page.get("Contents", []))
        return keys

    def exists(self, bucket: str, key: str) -> bool:
        try:
            self.client.head_object(Bucket=bucket, Key=key)
            return True
        except Exception as exc:  # botocore ClientError, kept generic so boto3 stays optional
            if getattr(exc, "response", {}).get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return False
            raise

    def presigned_url(self, bucket: str, key: str, expires_s: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires_s
        )


class AthenaHelper:
    def __init__(self, client, sleep=time.sleep):
        self.client = client
        self._sleep = sleep

    def run(self, query: str, database: str, output_s3: str, timeout_s: float = 120, poll_s: float = 2) -> list[dict]:
        """Run a query, wait for it (bounded, unlike an open-ended poll), return rows as dicts."""
        qid = self.client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={"Database": database},
            ResultConfiguration={"OutputLocation": output_s3},
        )["QueryExecutionId"]

        waited = 0.0
        while True:
            status = self.client.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]
            state = status["State"]
            if state in TERMINAL_STATES:
                break
            if waited >= timeout_s:
                raise TimeoutError(f"Athena query {qid} still {state} after {timeout_s:.0f}s")
            self._sleep(poll_s)
            waited += poll_s

        if state != "SUCCEEDED":
            raise RuntimeError(f"Athena query {qid} {state}: {status.get('StateChangeReason', 'no reason given')}")
        return self.rows(self.client.get_query_results(QueryExecutionId=qid)["ResultSet"])

    @staticmethod
    def rows(result_set: dict) -> list[dict]:
        rows = result_set.get("Rows", [])
        if not rows:
            return []
        header = [c.get("VarCharValue", "") for c in rows[0]["Data"]]
        return [{header[i]: c.get("VarCharValue") for i, c in enumerate(r["Data"])} for r in rows[1:]]


class DynamoDBHelper:
    def __init__(self, client):
        self.client = client

    def get_item(self, table: str, key: dict) -> Optional[dict]:
        item = self.client.get_item(TableName=table, Key=key).get("Item")
        return self.to_python(item) if item else None

    def query(
        self, table: str, key_condition: str, values: dict, filter_expression: Optional[str] = None
    ) -> list[dict]:
        params: dict[str, Any] = {
            "TableName": table,
            "KeyConditionExpression": key_condition,
            "ExpressionAttributeValues": values,
        }
        if filter_expression:
            params["FilterExpression"] = filter_expression
        items: list[dict] = []
        while True:
            page = self.client.query(**params)
            items.extend(self.to_python(i) for i in page.get("Items", []))
            if "LastEvaluatedKey" not in page:
                return items
            params["ExclusiveStartKey"] = page["LastEvaluatedKey"]

    @classmethod
    def to_python(cls, item: dict) -> dict:
        """Convert DynamoDB's typed JSON ({'S': 'x'}, {'N': '1'} ...) into plain Python values."""
        return {k: cls._value(v) for k, v in item.items()}

    @classmethod
    def _value(cls, v: dict) -> Any:
        ((kind, raw),) = v.items()
        if kind == "S":
            return raw
        if kind == "N":
            return int(raw) if raw.lstrip("-").isdigit() else float(raw)
        if kind == "BOOL":
            return raw
        if kind == "NULL":
            return None
        if kind == "L":
            return [cls._value(x) for x in raw]
        if kind == "M":
            return {k: cls._value(x) for k, x in raw.items()}
        if kind in ("SS", "NS"):
            return set(raw) if kind == "SS" else {float(x) for x in raw}
        return raw
