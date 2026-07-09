"""Local filesystem backend — the default on a dev machine.

Maps every logical key to ``ROOT / key`` where ROOT is the project root (the
folder that holds ``data*/``, ``crops/``, ``outputs/``). Behaviour is identical
to the direct ``Path`` access the code used before this abstraction existed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .base import Storage, StorageNotFound
from .keys import normalize_key


def project_root() -> Path:
    """Return the project root (…/arepas), three levels up from this file."""
    return Path(__file__).resolve().parents[2]


class LocalStorage(Storage):
    """Reads and writes under a single filesystem root."""

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root).resolve() if root is not None else project_root()

    def _abs(self, key: str) -> Path:
        return self.root / normalize_key(key)

    def exists(self, key: str) -> bool:
        return self._abs(key).exists()

    def read_bytes(self, key: str) -> bytes:
        path = self._abs(key)
        try:
            return path.read_bytes()
        except (FileNotFoundError, IsADirectoryError) as exc:
            raise StorageNotFound(key) from exc

    def write_bytes(self, key: str, data: bytes) -> None:
        path = self._abs(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def list(self, prefix: str, suffix: Optional[str] = None) -> list[str]:
        base = self._abs(prefix)
        if not base.exists():
            return []
        if base.is_dir():
            candidates = [p for p in base.rglob("*") if p.is_file()]
        else:
            # `prefix` points at a file, not a dir — treat as a single match.
            candidates = [base]
        keys: list[str] = []
        for path in candidates:
            key = normalize_key(str(path.relative_to(self.root)))
            # Match the suffix against the full logical key (not just the
            # basename) so slash-boundary suffixes like "/training_history.json"
            # work and behaviour matches S3Storage.list exactly.
            if suffix is None or key.endswith(suffix):
                keys.append(key)
        return sorted(keys)

    def local_path(self, key: str) -> Path:
        path = self._abs(key)
        if not path.exists():
            raise StorageNotFound(key)
        return path

    def url(self, key: str) -> str:
        # Served by the FastAPI static mounts (/images/*, /crops/*). The caller
        # owns the /images vs /crops routing; here we just yield an absolute
        # root-relative path.
        return "/" + normalize_key(key)
