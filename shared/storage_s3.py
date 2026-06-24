"""S3 storage helpers — upload/list parquet and JSON in the data lake bucket."""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd

    from config.settings import Settings


def is_configured(settings: Settings) -> bool:
    return bool(settings.aws_access_key_id and settings.aws_secret_access_key)


def _client(settings: Settings):
    import boto3
    return boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
    )


def upload_parquet(settings: Settings, df: pd.DataFrame, key: str) -> str:
    """Upload DataFrame as parquet. Returns s3://bucket/key."""
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    _client(settings).upload_fileobj(buf, settings.aws_s3_bucket, key)
    return f"s3://{settings.aws_s3_bucket}/{key}"


def upload_json(settings: Settings, data: dict[str, Any], key: str) -> str:
    """Upload dict as JSON. Returns s3://bucket/key."""
    buf = io.BytesIO(json.dumps(data, indent=2, default=str).encode())
    _client(settings).upload_fileobj(buf, settings.aws_s3_bucket, key)
    return f"s3://{settings.aws_s3_bucket}/{key}"


def list_objects(settings: Settings, prefix: str = "") -> list[dict[str, Any]]:
    """List objects under prefix. Returns list of S3 object dicts."""
    paginator = _client(settings).get_paginator("list_objects_v2")
    results: list[dict[str, Any]] = []
    for page in paginator.paginate(Bucket=settings.aws_s3_bucket, Prefix=prefix):
        results.extend(page.get("Contents", []))
    return results


def read_parquet(settings: Settings, key: str) -> pd.DataFrame:
    """Download and read a parquet file from S3."""
    import pandas as pd
    buf = io.BytesIO()
    _client(settings).download_fileobj(settings.aws_s3_bucket, key, buf)
    buf.seek(0)
    return pd.read_parquet(buf)
