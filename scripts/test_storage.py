"""Storage backend tests — LocalStorage (tmp dir) and S3Storage (moto), run as
one parametrized parity suite so both backends prove identical behaviour.

Run: python scripts/test_storage.py
Requires boto3 + moto for the S3 half; it is skipped (not failed) if missing.
"""
from __future__ import annotations

import io
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")

from PIL import Image  # noqa: E402

from src.storage.base import StorageNotFound  # noqa: E402
from src.storage.keys import bucket_for_key, normalize_key  # noqa: E402
from src.storage.local import LocalStorage  # noqa: E402

FAILS: list[str] = []


def check(name: str, cond: bool) -> None:
    print(f"[{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        FAILS.append(name)


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), (10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


def test_key_normalization() -> None:
    check("normalize strips leading slash", normalize_key("/a/b.txt") == "a/b.txt")
    check("normalize backslashes", normalize_key("a\\b\\c.txt") == "a/b/c.txt")
    check("normalize collapses dot", normalize_key("a/./b.txt") == "a/b.txt")
    check("normalize resolves ..", normalize_key("a/b/../c.txt") == "a/c.txt")
    check("normalize cannot escape root", normalize_key("../../etc/passwd") == "etc/passwd")
    check("normalize unicode en-dash", normalize_key("data/Domestic – Single/x.jpg") == "data/Domestic – Single/x.jpg")
    check(
        "bucket routing outputs -> models",
        bucket_for_key("outputs/x/run.json", data_bucket="d", models_bucket="m") == "m",
    )
    check(
        "bucket routing data -> data",
        bucket_for_key("data2/Cole/x.jpg", data_bucket="d", models_bucket="m") == "d",
    )


def run_parity(label: str, storage) -> None:
    print(f"\n=== {label} ===")
    # write/read round trips
    storage.write_bytes("outputs/run/history.json", b'{"epoch": 1}')
    storage.write_text("data2/Cole/note.txt", "hello")
    check(f"{label}: exists true", storage.exists("outputs/run/history.json"))
    check(f"{label}: exists false", not storage.exists("outputs/run/missing.json"))
    check(f"{label}: read_bytes", storage.read_bytes("data2/Cole/note.txt") == b"hello")
    check(f"{label}: read_text", storage.read_text("data2/Cole/note.txt") == "hello")
    check(f"{label}: read_json", storage.read_json("outputs/run/history.json") == {"epoch": 1})

    # missing -> StorageNotFound
    try:
        storage.read_bytes("outputs/run/missing.json")
        check(f"{label}: missing raises", False)
    except StorageNotFound:
        check(f"{label}: missing raises", True)

    # list + suffix filter (the rglob replacement)
    storage.write_bytes("outputs/run/phase1/best_model_phase1.pth", b"x" * 10)
    storage.write_bytes("outputs/run/phase1/checkpoint_epoch1.pth", b"y" * 10)
    storage.write_bytes("outputs/run/phase1/training_history.json", b"{}")
    pth = storage.list("outputs", suffix=".pth")
    check(f"{label}: list suffix count", len(pth) == 2)
    best = [k for k in pth if Path(k).name.startswith("best_model_phase")]
    check(f"{label}: list finds best_model", best == ["outputs/run/phase1/best_model_phase1.pth"])
    # slash-boundary suffix (the runs.py discovery pattern) must match on the
    # full key, not the basename — regression guard for both backends.
    hist = storage.list("outputs", suffix="/training_history.json")
    check(f"{label}: list slash-suffix", hist == ["outputs/run/phase1/training_history.json"])
    check(f"{label}: list empty prefix", storage.list("nope") == [])

    # open_image round trip
    storage.write_bytes("data2/Cole/pic.png", _png_bytes())
    img = storage.open_image("data2/Cole/pic.png")
    check(f"{label}: open_image size", img.size == (4, 4))

    # local_path returns a real, readable file
    p = storage.local_path("outputs/run/phase1/best_model_phase1.pth")
    check(f"{label}: local_path exists", p.exists() and p.read_bytes() == b"x" * 10)


def main() -> int:
    test_key_normalization()

    with tempfile.TemporaryDirectory() as tmp:
        run_parity("LocalStorage", LocalStorage(Path(tmp)))

    # S3 half via moto — skipped (not failed) if deps are unavailable.
    try:
        import boto3  # noqa: F401
        from moto import mock_aws
    except Exception as exc:  # pragma: no cover - env-dependent
        print(f"\n=== S3Storage (moto) SKIPPED: {exc} ===")
    else:
        from src.storage.s3 import S3Storage

        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket="arepas-data")
            client.create_bucket(Bucket="arepas-models")
            storage = S3Storage(
                data_bucket="arepas-data", models_bucket="arepas-models", client=client
            )
            run_parity("S3Storage", storage)
            # presigned url smoke check
            url = storage.url("data2/Cole/pic.png")
            check("S3Storage: url is https", url.startswith("https://"))

    print("\nAll passed." if not FAILS else f"\nFAILURES: {FAILS}")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    raise SystemExit(main())
