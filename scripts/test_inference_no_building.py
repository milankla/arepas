"""Regression test: crop/paired inference skips classification when no building is detected."""

from __future__ import annotations

import asyncio
import io
import sys
from pathlib import Path

from fastapi import UploadFile
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.routers import inference
from src.image_preprocessing.detector_base import DetectionResult


class _StorageStub:
    def exists(self, key: str) -> bool:
        return key == "outputs/test/run/best_model_phase2.pth"


def _jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), "white").save(buf, format="JPEG")
    return buf.getvalue()


async def _run() -> None:
    calls = {"predict": 0}

    original_storage = inference._storage
    original_checkpoint_input_type = inference._checkpoint_input_type
    original_load_model = inference._load_model
    original_get_transform = inference._get_transform
    original_auto_crop = inference._auto_crop_pil
    original_predict_single = inference._predict_single

    try:
        inference._storage = _StorageStub()  # type: ignore[assignment]
        inference._checkpoint_input_type = lambda _run_id, _cfg: "paired"  # type: ignore[assignment]
        inference._load_model = lambda _ckpt: (object(), object(), {}, set(), {})  # type: ignore[assignment]
        inference._get_transform = lambda _cfg: (lambda img: img)  # type: ignore[assignment]
        inference._auto_crop_pil = lambda img: (img, False)  # type: ignore[assignment]

        def _predict(*_args, **_kwargs):
            calls["predict"] += 1
            return []

        inference._predict_single = _predict  # type: ignore[assignment]

        upload = UploadFile(filename="not-a-building.jpg", file=io.BytesIO(_jpeg_bytes()))
        response = await inference.run_inference(
            checkpoint_path="outputs/test/run/best_model_phase2.pth",
            images=[upload],
        )
    finally:
        inference._storage = original_storage
        inference._checkpoint_input_type = original_checkpoint_input_type  # type: ignore[assignment]
        inference._load_model = original_load_model  # type: ignore[assignment]
        inference._get_transform = original_get_transform  # type: ignore[assignment]
        inference._auto_crop_pil = original_auto_crop  # type: ignore[assignment]
        inference._predict_single = original_predict_single  # type: ignore[assignment]

    assert calls["predict"] == 0
    assert response.aggregated is None
    assert response.per_image[0].tasks == []
    assert response.per_image[0].building_detected is False
    assert response.per_image[0].message == "No building detected"


def _assert_mountain_false_positive_is_rejected() -> None:
    result = DetectionResult(
        image_path="PXL_20260126_115510607.MP.jpg",
        detected=True,
        bounding_boxes=[(8, 821, 4071, 3065)],
        confidence_scores=[0.5291681885719299],
    )

    assert not inference._is_inference_detection_usable(result, image_size=(4080, 3072))


def main() -> None:
    asyncio.run(_run())
    _assert_mountain_false_positive_is_rejected()
    print("ok")


if __name__ == "__main__":
    main()