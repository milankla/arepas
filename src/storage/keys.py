"""Logical-key handling: normalization and S3 bucket routing.

A *logical key* is a project-relative POSIX path (``data2/Cole/x.jpg``,
``outputs/combined/.../training_history.json``). Normalization makes the
backends robust to leading slashes, backslashes, and ``.``/``..`` segments —
and, importantly, prevents ``..`` from escaping the storage root (path
traversal / OWASP A01).
"""
from __future__ import annotations


def normalize_key(key: str) -> str:
    """Return a clean, root-relative POSIX key.

    - Accepts ``str`` or anything ``str()``-able (e.g. ``Path``).
    - Converts backslashes to ``/`` (Windows separators).
    - Strips leading slashes (absolute -> relative).
    - Collapses ``.`` and resolves ``..`` textually, never escaping the root
      (leading ``..`` segments are dropped rather than climbing out).
    """
    raw = str(key).replace("\\", "/")
    parts: list[str] = []
    for part in raw.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            # else: refuse to climb above the root — drop it
            continue
        parts.append(part)
    return "/".join(parts)


def bucket_for_key(key: str, *, data_bucket: str, models_bucket: str) -> str:
    """Route a logical key to its S3 bucket by top-level prefix.

    ``outputs/`` (checkpoints, run metadata) -> models bucket; everything else
    (``data``, ``data2``, ``crops``, ``config``, …) -> data bucket. Mirrors
    DEPLOYMENT_PLAN.md §4.
    """
    top = normalize_key(key).split("/", 1)[0]
    if top == "outputs":
        return models_bucket
    return data_bucket
