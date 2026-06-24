#!/usr/bin/env python3
"""Generate per-label metrics for Phase 3 multi-label checkpoints.

Examples:
    .venv/bin/python scripts/phase3_per_label_report.py

    .venv/bin/python scripts/phase3_per_label_report.py \
        --checkpoint outputs/data2/phase3_v2_visual_retention/phase3/best_model_phase3.pth \
        --output-dir outputs/data2/phase3_per_label_reports/v2_only
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import torch
from sklearn.metrics import jaccard_score
from torch.utils.data import DataLoader
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.loader.architectural_dataset import MULTILABEL_COLS, make_splits
from src.models.model_config import ModelConfig
from src.models.multi_task_classifier import (
    MultiTaskArchitecturalClassifier,
    checkpoint_has_paired_fusion,
    normalize_paired_fusion_state_dict,
)

LOGGER = logging.getLogger(__name__)

DEFAULT_CHECKPOINTS = [
    "outputs/data2/phase3_full_v1/phase3/best_model_phase3.pth",
    "outputs/data2/phase3_v2_visual_retention/phase3/best_model_phase3.pth",
]

PHASE3_MULTILABEL_FIELDS = [
    "wall_features",
    "landscape_features",
    "window",
    "entrance",
    "associated_buildings",
    "roof_materials",
]


def _parse_phase3_labels(raw: Any) -> Optional[List[str]]:
    if raw is None:
        return None
    if isinstance(raw, list):
        return [str(value).strip() for value in raw if str(value).strip()]
    labels = [part.strip() for part in str(raw).split(",") if part.strip()]
    return labels or None


def _select_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _load_run_config(checkpoint_path: Path) -> Dict[str, Any]:
    run_config_path = checkpoint_path.parent / "run_config.json"
    if not run_config_path.exists():
        return {}
    with run_config_path.open() as file_obj:
        return json.load(file_obj)


def _run_name(checkpoint_path: Path, run_config: Dict[str, Any]) -> str:
    configured = str(run_config.get("run_name", "")).strip()
    if configured:
        return configured
    phase_dir = checkpoint_path.parent.name
    model_dir = checkpoint_path.parent.parent.name
    return f"{model_dir}/{phase_dir}"


def _build_loader(
    run_config: Dict[str, Any],
    split: str,
    batch_size: int,
    num_workers: int,
    prefetch_factor: int,
    checkpoint_num_classes: Dict[str, int],
) -> Tuple[DataLoader, Any]:
    model_config_path = run_config.get("model_config_path", "config/models/efficientnet_b5.json")
    model_config = ModelConfig.from_json(model_config_path)
    phase3_labels = _parse_phase3_labels(run_config.get("phase3_labels"))

    train_ds, val_ds, test_ds = make_splits(
        csv_path=run_config.get("csv_path", "data2/image_label_mapping_phase1.csv"),
        model_config=model_config,
        cropped_root=run_config.get("cropped_root"),
        paired_views=bool(run_config.get("paired_views", False)),
        include_phase3_labels=True,
        phase3_labels=phase3_labels,
    )
    dataset = {"train": train_ds, "val": val_ds, "test": test_ds}[split]

    missing_tasks = [task for task in checkpoint_num_classes if task not in dataset.num_classes]
    if missing_tasks:
        raise ValueError(
            f"Dataset for split '{split}' is missing checkpoint tasks: {missing_tasks}. "
            "Check run_config phase3_labels and csv_path."
        )

    prefetch = prefetch_factor if num_workers > 0 else None
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
        persistent_workers=num_workers > 0,
        prefetch_factor=prefetch,
    )
    return loader, dataset


def _load_model(
    checkpoint_path: Path,
    run_config: Dict[str, Any],
    device: str,
) -> Tuple[MultiTaskArchitecturalClassifier, Dict[str, int]]:
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    state = normalize_paired_fusion_state_dict(checkpoint.get("model_state_dict", checkpoint))
    num_classes = checkpoint.get("num_classes", {})
    if not num_classes:
        raise ValueError(f"Checkpoint does not contain num_classes: {checkpoint_path}")

    paired_views = bool(run_config.get("paired_views", False)) or checkpoint_has_paired_fusion(state)
    model = MultiTaskArchitecturalClassifier(
        backbone=run_config.get("backbone", "efficientnet_b5"),
        weights=None,
        active_phase=int(checkpoint.get("active_phase", run_config.get("end_phase", 3))),
        num_classes=num_classes,
        paired_views=paired_views,
        paired_fusion_mode=run_config.get("paired_fusion_mode", "concat_mlp"),
        paired_gate_init=run_config.get("paired_gate_init", "crop_prior"),
    )
    model.load_state_dict(state, strict=False)
    model.to(device).eval()
    return model, num_classes


def _collect_predictions(
    model: MultiTaskArchitecturalClassifier,
    loader: DataLoader,
    device: str,
    fields: Iterable[str],
) -> Tuple[Dict[str, torch.Tensor], Dict[str, torch.Tensor]]:
    field_set = set(fields)
    predictions: Dict[str, List[torch.Tensor]] = {}
    targets: Dict[str, List[torch.Tensor]] = {}

    with torch.no_grad():
        for images, batch_targets in tqdm(loader, desc="Evaluating", leave=False):
            if isinstance(images, dict):
                images = {key: value.to(device) for key, value in images.items()}
            else:
                images = images.to(device)
            batch_predictions = model(images)
            for field in field_set:
                if field not in batch_predictions or field not in batch_targets:
                    continue
                predictions.setdefault(field, []).append(batch_predictions[field].detach().cpu())
                targets.setdefault(field, []).append(batch_targets[field].detach().cpu())

    return (
        {field: torch.cat(values) for field, values in predictions.items()},
        {field: torch.cat(values) for field, values in targets.items()},
    )


def _safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _field_summary(pred_binary: torch.Tensor, target: torch.Tensor) -> Dict[str, float]:
    exact = (pred_binary == target).all(dim=1).float().mean().item()
    jaccard = jaccard_score(target.numpy(), pred_binary.numpy(), average="samples", zero_division=0)
    return {"exact_match": exact, "jaccard": jaccard}


def _label_metrics(pred_label: torch.Tensor, target_label: torch.Tensor) -> Dict[str, float]:
    tp = int(((pred_label == 1) & (target_label == 1)).sum().item())
    fp = int(((pred_label == 1) & (target_label == 0)).sum().item())
    fn = int(((pred_label == 0) & (target_label == 1)).sum().item())
    tn = int(((pred_label == 0) & (target_label == 0)).sum().item())
    precision = _safe_divide(tp, tp + fp)
    recall = _safe_divide(tp, tp + fn)
    f1 = _safe_divide(2 * precision * recall, precision + recall)
    return {
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "support": tp + fn,
        "predicted_positive": tp + fp,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _parse_threshold_grid(raw: str) -> List[float]:
    values = [float(part.strip()) for part in raw.split(",") if part.strip()]
    if not values:
        raise ValueError("Threshold grid must contain at least one value.")
    return sorted(set(values))


def _format_threshold_grid(thresholds: Sequence[float]) -> List[float]:
    return [round(float(threshold), 6) for threshold in thresholds]


def _calibrated_summary(
    probabilities: torch.Tensor,
    target: torch.Tensor,
    thresholds: Sequence[float],
) -> Dict[str, float]:
    threshold_tensor = torch.tensor(thresholds, dtype=probabilities.dtype).unsqueeze(0)
    pred_binary = (probabilities > threshold_tensor).float()
    summary = _field_summary(pred_binary, target)
    return {
        "exact_match": round(float(summary["exact_match"]), 6),
        "jaccard": round(float(summary["jaccard"]), 6),
        "micro_predicted_positive": int(pred_binary.sum().item()),
    }


def _calibrate_thresholds(
    run_name: str,
    split: str,
    field: str,
    label_names: List[str],
    logits: torch.Tensor,
    target: torch.Tensor,
    default_threshold: float,
    threshold_grid: Sequence[float],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    probabilities = torch.sigmoid(logits)
    rows: List[Dict[str, Any]] = []
    best_thresholds: List[float] = []
    best_f1_values: List[float] = []

    for index, label in enumerate(label_names):
        probability_label = probabilities[:, index]
        target_label = target[:, index]
        default_metrics = _label_metrics((probability_label > default_threshold).float(), target_label)

        best_threshold = threshold_grid[0]
        best_metrics = _label_metrics((probability_label > best_threshold).float(), target_label)
        for threshold in threshold_grid[1:]:
            candidate_metrics = _label_metrics((probability_label > threshold).float(), target_label)
            if (candidate_metrics["f1"], -candidate_metrics["false_positive"], threshold) > (
                best_metrics["f1"],
                -best_metrics["false_positive"],
                best_threshold,
            ):
                best_threshold = threshold
                best_metrics = candidate_metrics

        best_thresholds.append(best_threshold)
        best_f1_values.append(best_metrics["f1"])
        rows.append(
            {
                "run": run_name,
                "split": split,
                "field": field,
                "label": label,
                "support": int(default_metrics["support"]),
                "default_threshold": round(default_threshold, 6),
                "default_predicted_positive": int(default_metrics["predicted_positive"]),
                "default_precision": round(default_metrics["precision"], 6),
                "default_recall": round(default_metrics["recall"], 6),
                "default_f1": round(default_metrics["f1"], 6),
                "best_threshold": round(best_threshold, 6),
                "best_predicted_positive": int(best_metrics["predicted_positive"]),
                "best_precision": round(best_metrics["precision"], 6),
                "best_recall": round(best_metrics["recall"], 6),
                "best_f1": round(best_metrics["f1"], 6),
                "f1_delta": round(best_metrics["f1"] - default_metrics["f1"], 6),
            }
        )

    calibrated = _calibrated_summary(probabilities, target, best_thresholds)
    calibrated.update(
        {
            "run": run_name,
            "split": split,
            "field": field,
            "labels": len(label_names),
            "samples": int(target.shape[0]),
            "micro_support": int(target.sum().item()),
            "macro_f1": round(sum(best_f1_values) / len(best_f1_values), 6),
            "threshold_grid": _format_threshold_grid(threshold_grid),
        }
    )
    return rows, calibrated


def _per_label_rows(
    run_name: str,
    split: str,
    field: str,
    label_names: List[str],
    logits: torch.Tensor,
    target: torch.Tensor,
    threshold: float,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    pred_binary = (torch.sigmoid(logits) > threshold).float()
    rows: List[Dict[str, Any]] = []

    for index, label in enumerate(label_names):
        pred_label = pred_binary[:, index]
        target_label = target[:, index]
        tp = int(((pred_label == 1) & (target_label == 1)).sum().item())
        fp = int(((pred_label == 1) & (target_label == 0)).sum().item())
        fn = int(((pred_label == 0) & (target_label == 1)).sum().item())
        tn = int(((pred_label == 0) & (target_label == 0)).sum().item())
        support = tp + fn
        predicted_positive = tp + fp
        precision = _safe_divide(tp, tp + fp)
        recall = _safe_divide(tp, tp + fn)
        f1 = _safe_divide(2 * precision * recall, precision + recall)

        rows.append(
            {
                "run": run_name,
                "split": split,
                "field": field,
                "label": label,
                "support": support,
                "predicted_positive": predicted_positive,
                "true_positive": tp,
                "false_positive": fp,
                "false_negative": fn,
                "true_negative": tn,
                "precision": round(precision, 6),
                "recall": round(recall, 6),
                "f1": round(f1, 6),
            }
        )

    summary = _field_summary(pred_binary, target)
    summary.update(
        {
            "run": run_name,
            "split": split,
            "field": field,
            "labels": len(label_names),
            "samples": int(target.shape[0]),
            "micro_support": int(target.sum().item()),
            "micro_predicted_positive": int(pred_binary.sum().item()),
            "macro_precision": round(sum(row["precision"] for row in rows) / len(rows), 6),
            "macro_recall": round(sum(row["recall"] for row in rows) / len(rows), 6),
            "macro_f1": round(sum(row["f1"] for row in rows) / len(rows), 6),
            "threshold": threshold,
        }
    )
    summary["exact_match"] = round(float(summary["exact_match"]), 6)
    summary["jaccard"] = round(float(summary["jaccard"]), 6)
    return rows, summary


def generate_report(
    checkpoints: List[str],
    output_dir: Path,
    split: str,
    fields: List[str],
    threshold: float,
    batch_size: int,
    num_workers: int,
    prefetch_factor: int,
    calibrate_thresholds: bool,
    threshold_grid: Sequence[float],
) -> Tuple[Path, Path, Optional[Path], Optional[Path]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    device = _select_device()
    LOGGER.info("Using device: %s", device)

    all_rows: List[Dict[str, Any]] = []
    summaries: List[Dict[str, Any]] = []
    calibration_rows: List[Dict[str, Any]] = []
    calibration_summaries: List[Dict[str, Any]] = []

    for checkpoint_arg in checkpoints:
        checkpoint_path = Path(checkpoint_arg)
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

        run_config = _load_run_config(checkpoint_path)
        run_name = _run_name(checkpoint_path, run_config)
        LOGGER.info("Evaluating %s", run_name)
        model, num_classes = _load_model(checkpoint_path, run_config, device)
        loader, dataset = _build_loader(
            run_config=run_config,
            split=split,
            batch_size=batch_size,
            num_workers=num_workers,
            prefetch_factor=prefetch_factor,
            checkpoint_num_classes=num_classes,
        )

        active_fields = [field for field in fields if field in num_classes and field in MULTILABEL_COLS]
        if not active_fields:
            LOGGER.warning("No requested multi-label fields found for %s", run_name)
            continue

        predictions, targets = _collect_predictions(model, loader, device, active_fields)
        for field in active_fields:
            if field not in predictions or field not in targets:
                continue
            label_names = [str(label) for label in dataset.label_encoders[field].classes_]
            rows, summary = _per_label_rows(
                run_name=run_name,
                split=split,
                field=field,
                label_names=label_names,
                logits=predictions[field],
                target=targets[field],
                threshold=threshold,
            )
            all_rows.extend(rows)
            summaries.append(summary)
            if calibrate_thresholds:
                calibrated_rows, calibrated_summary = _calibrate_thresholds(
                    run_name=run_name,
                    split=split,
                    field=field,
                    label_names=label_names,
                    logits=predictions[field],
                    target=targets[field],
                    default_threshold=threshold,
                    threshold_grid=threshold_grid,
                )
                calibration_rows.extend(calibrated_rows)
                calibration_summaries.append(calibrated_summary)

    csv_path = output_dir / "phase3_per_label_metrics.csv"
    json_path = output_dir / "phase3_per_label_summary.json"

    fieldnames = [
        "run",
        "split",
        "field",
        "label",
        "support",
        "predicted_positive",
        "true_positive",
        "false_positive",
        "false_negative",
        "true_negative",
        "precision",
        "recall",
        "f1",
    ]
    with csv_path.open("w", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    with json_path.open("w") as file_obj:
        json.dump(
            {
                "checkpoints": checkpoints,
                "split": split,
                "threshold": threshold,
                "fields": fields,
                "summaries": summaries,
            },
            file_obj,
            indent=2,
        )
        file_obj.write("\n")

    calibration_csv_path: Optional[Path] = None
    calibration_json_path: Optional[Path] = None
    if calibrate_thresholds:
        calibration_csv_path = output_dir / "phase3_threshold_calibration.csv"
        calibration_json_path = output_dir / "phase3_threshold_calibration_summary.json"
        calibration_fieldnames = [
            "run",
            "split",
            "field",
            "label",
            "support",
            "default_threshold",
            "default_predicted_positive",
            "default_precision",
            "default_recall",
            "default_f1",
            "best_threshold",
            "best_predicted_positive",
            "best_precision",
            "best_recall",
            "best_f1",
            "f1_delta",
        ]
        with calibration_csv_path.open("w", newline="") as file_obj:
            writer = csv.DictWriter(file_obj, fieldnames=calibration_fieldnames)
            writer.writeheader()
            writer.writerows(calibration_rows)

        with calibration_json_path.open("w") as file_obj:
            json.dump(
                {
                    "checkpoints": checkpoints,
                    "split": split,
                    "default_threshold": threshold,
                    "threshold_grid": _format_threshold_grid(threshold_grid),
                    "fields": fields,
                    "summaries": calibration_summaries,
                },
                file_obj,
                indent=2,
            )
            file_obj.write("\n")

    return csv_path, json_path, calibration_csv_path, calibration_json_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate per-label Phase 3 multi-label metrics for saved checkpoints.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--checkpoint", action="append", dest="checkpoints", help="Checkpoint to evaluate. Can be passed multiple times.")
    parser.add_argument("--output-dir", default="outputs/data2/phase3_per_label_reports")
    parser.add_argument("--split", default="val", choices=["train", "val", "test"])
    parser.add_argument("--fields", default=",".join(PHASE3_MULTILABEL_FIELDS), help="Comma-separated multi-label fields to report.")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--calibrate-thresholds", action="store_true", help="Write per-label threshold calibration reports.")
    parser.add_argument(
        "--threshold-grid",
        default="0.1,0.15,0.2,0.25,0.3,0.35,0.4,0.45,0.5,0.55,0.6,0.65,0.7,0.75,0.8,0.85,0.9",
        help="Comma-separated thresholds to test when --calibrate-thresholds is set.",
    )
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--prefetch-factor", type=int, default=2)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper()), format="%(asctime)s - %(levelname)s - %(message)s")
    fields = [field.strip() for field in args.fields.split(",") if field.strip()]
    checkpoints = args.checkpoints or DEFAULT_CHECKPOINTS
    threshold_grid = _parse_threshold_grid(args.threshold_grid)
    csv_path, json_path, calibration_csv_path, calibration_json_path = generate_report(
        checkpoints=checkpoints,
        output_dir=Path(args.output_dir),
        split=args.split,
        fields=fields,
        threshold=args.threshold,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        prefetch_factor=args.prefetch_factor,
        calibrate_thresholds=args.calibrate_thresholds,
        threshold_grid=threshold_grid,
    )
    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")
    if calibration_csv_path and calibration_json_path:
        print(f"Wrote {calibration_csv_path}")
        print(f"Wrote {calibration_json_path}")


if __name__ == "__main__":
    main()
