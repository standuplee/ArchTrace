import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from archtrace.config import Settings


def client(settings: Settings):
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.access_key,
        aws_secret_access_key=settings.secret_key,
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 3}),
    )


def ensure_buckets(s3):
    existing = {bucket["Name"] for bucket in s3.list_buckets()["Buckets"]}
    for name in ("raw", "warehouse"):
        if name not in existing:
            s3.create_bucket(Bucket=name)


def put_once(s3, key: str, body: bytes):
    try:
        s3.put_object(Bucket="raw", Key=key, Body=body, IfNoneMatch="*")
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "PreconditionFailed":
            raise


def archive(s3, path: Path, snapshot: str) -> dict:
    """Small fixture ingestion only; production bulk files will use streaming I/O."""
    body = path.read_bytes()
    sha = hashlib.sha256(body).hexdigest()
    key = f"objects/sha256/{sha}"
    put_once(s3, key, body)
    manifest_key = f"manifests/synthetic_title/snapshot={snapshot}/{sha}.json"
    manifest = {
        "dataset": "synthetic_title",
        "is_synthetic": True,
        "original_filename": path.name,
        "size_bytes": len(body),
        "sha256": sha,
        "raw_uri": f"s3://raw/{key}",
        "snapshot_ym": snapshot,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "source": "repository synthetic fixture; not building HUB data",
        "ingestion_id": f"synthetic_title:{snapshot}:{sha}",
        "manifest_uri": f"s3://raw/{manifest_key}",
    }
    put_once(s3, manifest_key, json.dumps(manifest, ensure_ascii=False).encode())
    return json.loads(s3.get_object(Bucket="raw", Key=manifest_key)["Body"].read())


def read_raw(s3, manifest: dict) -> bytes:
    body = s3.get_object(Bucket="raw", Key=manifest["raw_uri"].removeprefix("s3://raw/"))[
        "Body"
    ].read()
    if hashlib.sha256(body).hexdigest() != manifest["sha256"]:
        raise ValueError("Raw checksum mismatch")
    return body
