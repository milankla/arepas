"""S3 backend — used when ``AREPAS_S3_BUCKET`` is set.

Logical keys are mapped to ``s3://<bucket>/<prefix>/<key>`` where the bucket is
chosen by :func:`~src.storage.keys.bucket_for_key` (``outputs/`` -> models
bucket, everything else -> data bucket) and ``<prefix>`` is an optional global
key prefix (``AREPAS_S3_PREFIX``).

``boto3`` is imported lazily so a dev machine that never touches S3 does not
need it installed.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Optional

from .base import Storage, StorageError, StorageNotFound
from .keys import bucket_for_key, normalize_key


class S3Storage(Storage):
    """Reads and writes S3 objects across the data and models buckets."""

    def __init__(
        self,
        *,
        data_bucket: str,
        models_bucket: Optional[str] = None,
        prefix: str = "",
        presign_expiry: int = 3600,
        client=None,
        cache_dir: Optional[Path] = None,
    ) -> None:
        self.data_bucket = data_bucket
        self.models_bucket = models_bucket or data_bucket
        self.prefix = normalize_key(prefix) if prefix else ""
        self.presign_expiry = presign_expiry
        self._client = client
        self.cache_dir = Path(cache_dir) if cache_dir else Path(tempfile.gettempdir()) / "arepas-s3-cache"

    # -- boto3 plumbing ------------------------------------------------------

    @property
    def client(self):
        if self._client is None:
            import boto3  # lazy: only needed when S3 is actually used

            self._client = boto3.client("s3")
        return self._client

    def _bucket(self, key: str) -> str:
        return bucket_for_key(
            key, data_bucket=self.data_bucket, models_bucket=self.models_bucket
        )

    def _object_key(self, key: str) -> str:
        norm = normalize_key(key)
        return f"{self.prefix}/{norm}" if self.prefix else norm

    def _logical_key(self, object_key: str) -> str:
        if self.prefix and object_key.startswith(self.prefix + "/"):
            return object_key[len(self.prefix) + 1:]
        return object_key

    # -- primitives ----------------------------------------------------------

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.client.head_object(Bucket=self._bucket(key), Key=self._object_key(key))
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return False
            raise StorageError(str(exc)) from exc

    def read_bytes(self, key: str) -> bytes:
        from botocore.exceptions import ClientError

        try:
            resp = self.client.get_object(Bucket=self._bucket(key), Key=self._object_key(key))
            return resp["Body"].read()
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                raise StorageNotFound(key) from exc
            raise StorageError(str(exc)) from exc

    def write_bytes(self, key: str, data: bytes) -> None:
        self.client.put_object(Bucket=self._bucket(key), Key=self._object_key(key), Body=data)

    def list(self, prefix: str, suffix: Optional[str] = None) -> list[str]:
        bucket = self._bucket(prefix)
        object_prefix = self._object_key(prefix)
        # Ensure directory-style prefixes match on a path boundary.
        if object_prefix and not object_prefix.endswith("/"):
            object_prefix += "/"
        paginator = self.client.get_paginator("list_objects_v2")
        keys: list[str] = []
        for page in paginator.paginate(Bucket=bucket, Prefix=object_prefix):
            for obj in page.get("Contents", []):
                logical = self._logical_key(obj["Key"])
                if suffix is None or logical.endswith(suffix):
                    keys.append(logical)
        return sorted(keys)

    def local_path(self, key: str) -> Path:
        """Download ``key`` once to a cached temp file and return its path.

        Cache path is keyed by bucket+object; the object is re-downloaded only
        if the cached size differs from S3's reported size. Downloads land in a
        ``.part`` file and are atomically renamed, so a crashed download never
        leaves a truncated file behind.
        """
        from botocore.exceptions import ClientError

        bucket = self._bucket(key)
        object_key = self._object_key(key)
        digest = hashlib.sha256(f"{bucket}/{object_key}".encode()).hexdigest()[:16]
        target = self.cache_dir / digest / normalize_key(key).rsplit("/", 1)[-1]
        target.parent.mkdir(parents=True, exist_ok=True)

        try:
            head = self.client.head_object(Bucket=bucket, Key=object_key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                raise StorageNotFound(key) from exc
            raise StorageError(str(exc)) from exc

        remote_size = head.get("ContentLength")
        if target.exists() and target.stat().st_size == remote_size:
            return target

        part = target.with_suffix(target.suffix + ".part")
        self.client.download_file(bucket, object_key, str(part))
        os.replace(part, target)
        return target

    def url(self, key: str) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket(key), "Key": self._object_key(key)},
            ExpiresIn=self.presign_expiry,
        )
