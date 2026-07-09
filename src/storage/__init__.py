"""Storage abstraction for Arepas.

Import the singleton backend and use logical (project-relative) keys::

    from src.storage import get_storage

    storage = get_storage()
    history = storage.read_json("outputs/combined/.../training_history.json")
    for key in storage.list("outputs", suffix=".pth"):
        ...

Backend selection (at first call, cached):
- ``AREPAS_S3_BUCKET`` set  -> :class:`S3Storage` (data bucket = that value;
  models bucket = ``AREPAS_S3_MODELS_BUCKET`` or the same; optional
  ``AREPAS_S3_PREFIX``).
- otherwise                 -> :class:`LocalStorage` rooted at the project
  root (override with ``AREPAS_LOCAL_ROOT``).
"""
from __future__ import annotations

import os
from functools import lru_cache

from .base import Storage, StorageError, StorageNotFound
from .keys import normalize_key
from .local import LocalStorage, project_root

__all__ = [
    "Storage",
    "StorageError",
    "StorageNotFound",
    "LocalStorage",
    "get_storage",
    "reset_storage",
    "normalize_key",
    "project_root",
]


@lru_cache(maxsize=1)
def get_storage() -> Storage:
    """Return the process-wide storage backend (cached after first call)."""
    bucket = os.environ.get("AREPAS_S3_BUCKET")
    if bucket:
        from .s3 import S3Storage

        return S3Storage(
            data_bucket=bucket,
            models_bucket=os.environ.get("AREPAS_S3_MODELS_BUCKET") or bucket,
            prefix=os.environ.get("AREPAS_S3_PREFIX", ""),
        )
    local_root = os.environ.get("AREPAS_LOCAL_ROOT")
    return LocalStorage(local_root or project_root())


def reset_storage() -> None:
    """Clear the cached backend (tests that flip env vars)."""
    get_storage.cache_clear()
