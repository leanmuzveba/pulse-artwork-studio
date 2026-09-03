"""Read objects from S3-compatible storage (internal endpoint)."""

from __future__ import annotations

import boto3
from botocore.client import Config as BotoConfig

from worker.config import get_settings


def _client():
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.s3_endpoint_url,
        aws_access_key_id=s.s3_access_key,
        aws_secret_access_key=s.s3_secret_key,
        region_name=s.s3_region,
        config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def download_bytes(bucket: str, key: str) -> bytes:
    obj = _client().get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()
