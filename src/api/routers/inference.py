"""
Inference API — run a trained checkpoint on uploaded images.

Endpoints:
    GET  /api/checkpoints          list available best_model_phase*.pth checkpoints
    POST /api/inference            run inference on 1–N uploaded images
"""
from __future__ import annotations

import base64
import io
import json
import re
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi import File as FastAPIFile
from fastapi import Form
from PIL import Image
from pydantic import BaseModel
from torchvision import transforms

from src.image_preprocessing.grounding_dino_detector import GroundingDINODetector
from src.loader.architectural_dataset import make_splits
from src.models.model_config import ModelConfig
from src.models.multi_task_classifier import (
    MultiTaskArchitecturalClassifier,
    checkpoint_has_paired_fusion,
    normalize_paired_fusion_state_dict,
)

router = APIRouter()

OUTPUTS_ROOT = Path("outputs")
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD  = (0.229, 0.224, 0.225)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class CheckpointInfo(BaseModel):
    id: str               # relative path under outputs/, e.g. "data2/b5_crop_v1/phase1"
    short_name: str       # e.g. "b5_crop_v4"
    checkpoint_path: str  # full relative path to .pth
    backbone: str
    phase: int
    best_overall_acc: float
    dataset_version: str
    timestamp: str
    run_name: str
    input_type: str       # "crop" | "full" | "paired"
    paired_views: bool
    paired_fusion_mode: str | None = None
    lr: float
    backbone_lr_scale: float | None
    scheduler: str
    freeze_phase1_heads: bool


class ClassConfidence(BaseModel):
    label: str
    confidence: float  # 0–100


class TaskResult(BaseModel):
    task: str
    predicted: str
    confidence: float         # 0–100, top class
    top3: list[ClassConfidence]


class ImageResult(BaseModel):
    filename: str
    tasks: list[TaskResult]
    auto_cropped: bool = False
    cropped_image_b64: str | None = None  # base64 JPEG of the auto-cropped region


class InferenceResponse(BaseModel):
    per_image: list[ImageResult]
    aggregated: list[TaskResult] | None  # only when len(per_image) > 1
    auto_cropped: bool = False


# ---------------------------------------------------------------------------
# Checkpoint discovery
# ---------------------------------------------------------------------------

def _is_crop_run(run_id: str) -> bool:
    """Return True if this run was trained on cropped images."""
    return "crop" in run_id.lower()


def _checkpoint_input_type(run_id: str, cfg: dict[str, Any]) -> str:
    if cfg.get("paired_views", False) or "pair" in run_id.lower():
        return "paired"
    return "crop" if _is_crop_run(run_id) else "full"


def _discover_checkpoints() -> list[CheckpointInfo]:
    results = []
    for ckpt_path in sorted(OUTPUTS_ROOT.rglob("best_model_phase*.pth")):
        run_dir = ckpt_path.parent
        config_path = run_dir / "run_config.json"
        if not config_path.exists():
            continue
        try:
            with open(config_path) as f:
                cfg = json.load(f)
        except Exception:
            continue

        m = re.search(r"phase(\d+)", ckpt_path.name)
        phase = int(m.group(1)) if m else cfg.get("end_phase", 1)

        rel = str(ckpt_path.relative_to(OUTPUTS_ROOT))
        run_id = str(run_dir.relative_to(OUTPUTS_ROOT))

        best_acc = 0.0
        history_path = run_dir / "training_history.json"
        if history_path.exists():
            try:
                with open(history_path) as f:
                    history = json.load(f)
                seen = {e["epoch"]: e for e in history}
                deduped = sorted(seen.values(), key=lambda e: e["epoch"])
                best_acc = max(
                    e.get("val_metrics", {}).get("overall_accuracy", 0.0)
                    for e in deduped
                )
            except Exception:
                pass

        # Derive short name: strip leading "<dataset>/" and trailing "/phase<N>"
        short_name = re.sub(r"^[^/]+/", "", run_id)   # strip "data2/"
        short_name = re.sub(r"(/phase\d+)+$", "", short_name)  # strip "/phase2" (including nested)

        input_type = _checkpoint_input_type(run_id, cfg)
        results.append(CheckpointInfo(
            id=run_id,
            short_name=short_name,
            checkpoint_path=str(ckpt_path),
            backbone=cfg.get("backbone", "unknown"),
            phase=phase,
            best_overall_acc=round(best_acc * 100, 2),
            dataset_version=cfg.get("dataset_version", ""),
            timestamp=cfg.get("timestamp", ""),
            run_name=cfg.get("run_name", ""),
            input_type=input_type,
            paired_views=input_type == "paired",
            paired_fusion_mode=cfg.get("paired_fusion_mode"),
            lr=cfg.get("lr", 1e-4),
            backbone_lr_scale=cfg.get("backbone_lr_scale", None),
            scheduler=cfg.get("scheduler", "plateau"),
            freeze_phase1_heads=cfg.get("freeze_phase1_heads", False),
        ))
    return results


@router.get("/checkpoints", response_model=list[CheckpointInfo])
def list_checkpoints() -> list[CheckpointInfo]:
    return _discover_checkpoints()


# ---------------------------------------------------------------------------
# GroundingDINO detector — lazy singleton
# ---------------------------------------------------------------------------

_detector: GroundingDINODetector | None = None


def _get_detector() -> GroundingDINODetector:
    global _detector
    if _detector is None:
        _detector = GroundingDINODetector(device="auto")
    return _detector


def _auto_crop_pil(img: Image.Image) -> tuple[Image.Image, bool]:
    """Detect the building in *img* and return a cropped PIL Image.

    Returns (cropped_image, was_cropped).  Falls back to the original on
    detection failure so inference always proceeds.
    """
    detector = _get_detector()
    # GroundingDINO requires a file path; write to a temp file
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name
        img.save(tmp_path, format="JPEG", quality=95)

    try:
        result = detector.detect(tmp_path)
        if not result.detected or not result.bounding_boxes:
            return img, False
        cropped = detector.extract_building(tmp_path, bbox=result.bounding_boxes[0])
        return cropped, True
    except Exception:
        return img, False
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Model loader (cached per checkpoint path)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=4)
def _load_model(checkpoint_path: str) -> tuple[MultiTaskArchitecturalClassifier, ModelConfig, dict[str, list[str]], set[str], dict[str, Any]]:
    """Load and cache model + config from a checkpoint path."""
    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)

    run_dir = Path(checkpoint_path).parent
    run_cfg_path = run_dir / "run_config.json"
    if not run_cfg_path.exists():
        raise FileNotFoundError(f"run_config.json not found at {run_cfg_path}")

    with open(run_cfg_path) as f:
        run_cfg = json.load(f)

    model_config_path = run_cfg.get("model_config_path", "config/models/resnet50.json")
    model_config = ModelConfig.from_json(model_config_path)

    m = re.search(r"phase(\d+)", Path(checkpoint_path).name)
    active_phase = int(m.group(1)) if m else run_cfg.get("end_phase", 1)

    # Extract class lists by fitting label encoders from the CSV (fast — no images loaded)
    label_classes: dict[str, list[str]] = {}
    csv_path = run_cfg.get("csv_path", "")
    if csv_path and Path(csv_path).exists():
        try:
            train_ds, _, _ = make_splits(csv_path=csv_path, model_config=model_config)
            label_classes = {
                task: list(enc.classes_)
                for task, enc in train_ds.label_encoders.items()
            }
        except Exception:
            pass  # fall back to index-based labels

    # Use num_classes stored directly in the checkpoint (data-driven, set at training time)
    num_classes: dict[str, int] = ckpt.get("num_classes", {})

    # If not present (older checkpoints), fall back to parsing the state_dict
    state = normalize_paired_fusion_state_dict(ckpt.get("model_state_dict", ckpt))
    paired_views = bool(run_cfg.get("paired_views", False)) or checkpoint_has_paired_fusion(state)
    run_cfg = {**run_cfg, "paired_views": paired_views}
    if not num_classes:
        for key, tensor in state.items():
            if "task_heads." not in key:
                continue
            task = key.split("task_heads.")[1].split(".")[0]
            if key.endswith(".weight") and tensor.ndim == 2:
                num_classes[task] = tensor.shape[0]

    model = MultiTaskArchitecturalClassifier(
        backbone=model_config.backbone,
        weights=None,
        active_phase=active_phase,
        freeze_backbone=False,
        num_classes=num_classes if num_classes else None,
        paired_views=paired_views,
        paired_fusion_mode=run_cfg.get("paired_fusion_mode", "concat_mlp"),
        paired_gate_init=run_cfg.get("paired_gate_init", "crop_prior"),
    )
    model.load_state_dict(state, strict=False)
    model.eval()
    # trained_tasks: intersection of:
    #   - num_classes.keys()  → tasks that had labels and contributed to the loss
    #   - state_dict task heads → tasks with actual trained weights (not random init)
    # Using only num_classes would include alteration_level on old checkpoints where
    # the head was never built (phase-gated), giving random-weight predictions.
    # Using only state_dict would include building_category on old checkpoints where
    # the head was built but never trained (no labels in TRAINING_LABEL_COLS).
    state_dict_tasks: set[str] = {
        k.split("task_heads.")[1].split(".")[0]
        for k in state
        if "task_heads." in k
    }
    trained_tasks: set[str] = set(num_classes.keys()) & state_dict_tasks
    return model, model_config, label_classes, trained_tasks, run_cfg


def _get_transform(model_config: ModelConfig) -> transforms.Compose:
    # Must match build_eval_transform exactly: direct Resize to square, no CenterCrop.
    # The model was validated with Resize((H, W)) not Resize(short_edge)+CenterCrop.
    size = model_config.image_size
    return transforms.Compose([
        transforms.Resize((size, size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=model_config.norm_mean, std=model_config.norm_std),
    ])


# ---------------------------------------------------------------------------
# Inference helpers
# ---------------------------------------------------------------------------

def _predict_single(
    model: MultiTaskArchitecturalClassifier,
    tensor: torch.Tensor | dict[str, torch.Tensor],
    label_classes: dict[str, list[str]],
    trained_tasks: set[str] | None = None,
) -> list[TaskResult]:
    """Run one image tensor through the model and return TaskResult list."""
    with torch.no_grad():
        if isinstance(tensor, dict):
            batch = {k: v.unsqueeze(0) for k, v in tensor.items()}
            logits: dict[str, torch.Tensor] = model(batch)
        else:
            logits = model(tensor.unsqueeze(0))

    results = []
    for task_name, raw in logits.items():
        # Skip task heads that were never trained (not in the checkpoint's num_classes)
        if trained_tasks is not None and task_name not in trained_tasks:
            continue
        cfg = model.get_task_config(task_name)
        classes = label_classes.get(task_name, [])

        if cfg.get("multi_label", False):
            probs = torch.sigmoid(raw[0]).tolist()
            if not classes:
                classes = [str(i) for i in range(len(probs))]
            pairs = sorted(zip(classes, probs), key=lambda x: -x[1])
            top3 = [ClassConfidence(label=l, confidence=round(p * 100, 1)) for l, p in pairs[:3]]
            predicted = top3[0].label if top3 else "?"
            confidence = top3[0].confidence if top3 else 0.0
        else:
            probs = F.softmax(raw[0], dim=0).tolist()
            if not classes:
                classes = [str(i) for i in range(len(probs))]
            pairs = sorted(zip(classes, probs), key=lambda x: -x[1])
            top3 = [ClassConfidence(label=l, confidence=round(p * 100, 1)) for l, p in pairs[:3]]
            predicted = top3[0].label if top3 else "?"
            confidence = top3[0].confidence if top3 else 0.0

        results.append(TaskResult(
            task=task_name,
            predicted=predicted,
            confidence=confidence,
            top3=top3,
        ))
    return results


def _aggregate_results(per_image: list[list[TaskResult]]) -> list[TaskResult]:
    """Average softmax probabilities across images, return aggregated TaskResult list."""
    if not per_image:
        return []

    tasks = [r.task for r in per_image[0]]
    aggregated = []

    for task_idx, task_name in enumerate(tasks):
        class_sums: dict[str, float] = {}
        for img_results in per_image:
            for item in img_results[task_idx].top3:
                class_sums[item.label] = class_sums.get(item.label, 0.0) + item.confidence

        n = len(per_image)
        avg = {label: class_sums[label] / n for label in class_sums}
        pairs = sorted(avg.items(), key=lambda x: -x[1])
        top3 = [ClassConfidence(label=l, confidence=round(c, 1)) for l, c in pairs[:3]]

        aggregated.append(TaskResult(
            task=task_name,
            predicted=top3[0].label if top3 else "?",
            confidence=top3[0].confidence if top3 else 0.0,
            top3=top3,
        ))
    return aggregated


# ---------------------------------------------------------------------------
# Inference endpoint
# ---------------------------------------------------------------------------

@router.post("/inference", response_model=InferenceResponse)
async def run_inference(
    checkpoint_path: str = Form(...),
    images: list[UploadFile] = FastAPIFile(...),
) -> InferenceResponse:
    if not images:
        raise HTTPException(status_code=422, detail="At least one image is required.")

    # Validate checkpoint path is inside outputs/ (security: prevent path traversal)
    ckpt = Path(checkpoint_path).resolve()
    outputs_resolved = OUTPUTS_ROOT.resolve()
    try:
        ckpt.relative_to(outputs_resolved)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid checkpoint path.")
    if not ckpt.exists():
        raise HTTPException(status_code=404, detail=f"Checkpoint not found: {checkpoint_path}")

    try:
        model, model_config, label_classes, trained_tasks, run_cfg = _load_model(str(ckpt))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model: {e}")

    run_id = str(ckpt.parent.relative_to(outputs_resolved))
    input_type = _checkpoint_input_type(run_id, run_cfg)
    needs_crop = input_type in {"crop", "paired"}

    transform = _get_transform(model_config)

    per_image_results: list[list[TaskResult]] = []
    image_names: list[str] = []
    cropped_b64_list: list[str | None] = []
    any_cropped = False

    for upload in images:
        raw = await upload.read()
        try:
            img = Image.open(io.BytesIO(raw)).convert("RGB")
        except Exception:
            raise HTTPException(status_code=422, detail=f"Cannot decode image: {upload.filename}")

        was_cropped = False
        cropped_b64: str | None = None
        full_img = img
        crop_img = img
        if needs_crop:
            crop_img, was_cropped = _auto_crop_pil(img)
            if was_cropped:
                any_cropped = True
                buf = io.BytesIO()
                crop_img.save(buf, format="JPEG", quality=85)
                cropped_b64 = base64.b64encode(buf.getvalue()).decode()

        tensor: torch.Tensor | dict[str, torch.Tensor]
        if input_type == "paired":
            tensor = {"full": transform(full_img), "crop": transform(crop_img)}
        else:
            tensor = transform(crop_img if input_type == "crop" else full_img)
        results = _predict_single(model, tensor, label_classes, trained_tasks)
        per_image_results.append(results)
        image_names.append(upload.filename or "image")
        cropped_b64_list.append(cropped_b64)

    per_image = [
        ImageResult(filename=name, tasks=tasks, auto_cropped=(needs_crop and any_cropped), cropped_image_b64=b64)
        for name, tasks, b64 in zip(image_names, per_image_results, cropped_b64_list)
    ]

    aggregated = _aggregate_results(per_image_results) if len(per_image_results) > 1 else None

    return InferenceResponse(
        per_image=per_image,
        aggregated=aggregated,
        auto_cropped=any_cropped,
    )

