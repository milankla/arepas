"""Storage abstraction — the single interface every "where do bytes live"
decision goes through.

Two backends implement this: :class:`~src.storage.local.LocalStorage` (the
project filesystem, the default on a dev machine) and
:class:`~src.storage.s3.S3Storage` (used when ``AREPAS_S3_BUCKET`` is set).

Call sites refer to data by its existing project-relative path (the *logical
key*), e.g. ``"data2/Cole/x.jpg"``, ``"outputs/combined/.../training_history.json"``,
``"crops/combined/..."``. The backend maps that key to a real location. No call
site changes how it *names* things — only how it *opens* them.
"""
from __future__ import annotations

import abc
import io
import json
from pathlib import Path
from typing import Any, Optional

from PIL import Image


class StorageError(Exception):
    """Base class for storage-layer errors."""


class StorageNotFound(StorageError):
    """Raised when a key does not exist in the backend."""


class Storage(abc.ABC):
    """Backend-agnostic byte store keyed by project-relative logical paths."""

    # -- required primitives -------------------------------------------------

    @abc.abstractmethod
    def exists(self, key: str) -> bool:
        """Return True if ``key`` resolves to an existing object."""

    @abc.abstractmethod
    def read_bytes(self, key: str) -> bytes:
        """Return the object's bytes, or raise :class:`StorageNotFound`."""

    @abc.abstractmethod
    def write_bytes(self, key: str, data: bytes) -> None:
        """Write ``data`` at ``key`` (creating parents/prefixes as needed)."""

    @abc.abstractmethod
    def list(self, prefix: str, suffix: Optional[str] = None) -> list[str]:
        """Return sorted logical keys under ``prefix`` (recursively).

        When ``suffix`` is given, only keys ending with it are returned. This
        is the replacement for ``Path.rglob`` — S3 is flat, so it becomes a
        prefix scan plus a suffix match, and the local backend mirrors that.
        """

    @abc.abstractmethod
    def local_path(self, key: str) -> Path:
        """Return a real local filesystem path for ``key``.

        The local backend returns the file in place; the S3 backend downloads
        it once to a cached temp path. Used for APIs that need a real file
        (``torch.load`` / ``torch.save``).
        """

    @abc.abstractmethod
    def url(self, key: str) -> str:
        """Return a URL a browser can fetch ``key`` from.

        Local: the static-mount path (``/images/...``). S3: a presigned or CDN
        URL. Only used by the image-serving layer.
        """

    # -- text / json / image helpers (backend-independent) -------------------

    def read_text(self, key: str, encoding: str = "utf-8") -> str:
        return self.read_bytes(key).decode(encoding)

    def read_json(self, key: str) -> Any:
        return json.loads(self.read_text(key))

    def write_text(self, key: str, text: str, encoding: str = "utf-8") -> None:
        self.write_bytes(key, text.encode(encoding))

    def write_json(self, key: str, obj: Any, *, indent: int = 2) -> None:
        self.write_text(key, json.dumps(obj, indent=indent))

    def open_image(self, key: str) -> Image.Image:
        """Load ``key`` into a PIL image (bytes -> Image, fully read)."""
        image = Image.open(io.BytesIO(self.read_bytes(key)))
        image.load()  # force decode now so the backing buffer can be released
        return image
