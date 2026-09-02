"""S3-compatible object storage (MinIO in dev).

Uploads go direct from the browser to storage via a presigned PUT URL, so large
files never pass through the API. Presigned URLs are signed with the *public*
endpoint (the host the browser can reach); server-side checks use the *internal*
endpoint.
"""

from __future__ import annotations

import re
import unicodedata
import uuid

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings

_NOT_FOUND_CODES = {"404", "NoSuchKey", "NotFound"}


def _client(*, public: bool):
    s = get_settings()
    endpoint = s.s3_public_endpoint_url if public else s.s3_endpoint_url
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=s.s3_access_key,
        aws_secret_access_key=s.s3_secret_key,
        region_name=s.s3_region,
        config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def sanitize_filename(name: str) -> str:
    """Reduce a filename to a safe slug + extension."""
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = name.replace("\\", "/").split("/")[-1]  # strip any path
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name).strip("._") or "file"
    return name[:200]


def build_original_key(project_id: uuid.UUID, artwork_id: uuid.UUID, filename: str) -> str:
    return f"projects/{project_id}/originals/{artwork_id}/{sanitize_filename(filename)}"


def create_presigned_upload(bucket: str, key: str, content_type: str, expires: int) -> str:
    return _client(public=True).generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket, "Key": key, "ContentType": content_type},
        ExpiresIn=expires,
    )


def create_presigned_download(bucket: str, key: str, expires: int) -> str:
    return _client(public=True).generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires,
    )


def head_object(bucket: str, key: str) -> dict | None:
    """Return object metadata, or None if it does not exist. Raises on other errors."""
    try:
        resp = _client(public=False).head_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in _NOT_FOUND_CODES:
            return None
        raise
    return {
        "size_bytes": resp.get("ContentLength"),
        "content_type": resp.get("ContentType"),
        "etag": (resp.get("ETag") or "").strip('"') or None,
    }


def storage_reachable() -> bool:
    """Best-effort connectivity check (used to gate storage integration tests)."""
    try:
        _client(public=False).list_buckets()
        return True
    except (BotoCoreError, ClientError, OSError):
        return False
