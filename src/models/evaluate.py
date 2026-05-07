"""
Standalone evaluation script for a trained MultiTaskArchitecturalClassifier.

Usage:
    python -m src.models.evaluate \\
      --checkpoint outputs/smoke_test/phase1/best_model_phase1.pth \\
      --csv data2/image_label_mapping_phase1.csv \\
      --model-config config/models/resnet18.json

Prints a formatted per-task metrics report (accuracy, macro F1, classification
report per task) and optionally saves a JSON summary.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import torch
import numpy as np
from sklearn.metrics import classification_report
from torch.utils.data import DataLoader
from tqdm import tqdm

from src.loader.architectural_dataset import make_splits
from src.models.metrics import compute_metrics, format_metrics_table
from src.models.model_config import ModelConfig
from src.models.multi_task_classifier import MultiTaskArchitecturalClassifier

logger = logging.getLogger(__name__)


def evaluate(
    checkpoint_path: str,
    csv_path: str,
    model_config: ModelConfig,
    split: str = "test",
    batch_size: int = 32,
    num_workers: int = 4,
    prefetch_factor: int = 4,
    cropped_root: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """Run evaluation and return (metrics, per_task_reports).

    Args:
        checkpoint_path: Path to a .pth checkpoint saved by MultiTaskTrainer.
        csv_path:        Label-mapping CSV (same one used during training).
        model_config:    Backbone config — drives image_size and norm stats for
                         dataset transforms.
        split:           Which split to evaluate: 'train', 'val', or 'test'.
        batch_size:      Samples per batch.
        num_workers:     DataLoader worker processes.
        prefetch_factor: Batches to prefetch per worker (ignored when num_workers=0).

    Returns:
        metrics:          Nested dict from compute_metrics() with overall_accuracy.
        per_task_reports: {task_name: sklearn classification_report string}.
    """
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"

    # ── Load checkpoint ───────────────────────────────────────────────────
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)
    active_phase = ckpt["active_phase"]
    num_classes  = ckpt.get("num_classes", {})
    logger.info(
        f"Checkpoint: phase={active_phase}, epoch={ckpt.get('epoch', '?')}"
        + (f", best_val_loss={ckpt['best_val_loss']:.4f}" if "best_val_loss" in ckpt else "")
    )

    # ── Build dataset splits ──────────────────────────────────────────────
    train_ds, val_ds, test_ds = make_splits(
        csv_path=csv_path,
        model_config=model_config,
        cropped_root=cropped_root,
    )
    ds = {"train": train_ds, "val": val_ds, "test": test_ds}[split]

    # Fallback: checkpoints saved before num_classes was added use training-split counts.
    if not num_classes:
        num_classes = train_ds.num_classes
        logger.warning("No num_classes in checkpoint (old format) — using training split counts")

    pf = prefetch_factor if num_workers > 0 else None
    loader = DataLoader(
        ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=(device == "cuda"),
        persistent_workers=(num_workers > 0),
        prefetch_factor=pf,
    )

    # ── Build model ───────────────────────────────────────────────────────
    model = MultiTaskArchitecturalClassifier(
        backbone=model_config.backbone,
        active_phase=active_phase,
        num_classes=num_classes,
    )
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device).eval()
    logger.info(
        f"Model: {model_config.backbone}, phase {active_phase}, "
        f"{len(model.task_heads)} heads — evaluating {len(ds)} {split} samples"
    )

    # ── Collect predictions and targets ──────────────────────────────────
    all_preds: Dict[str, list] = {}
    all_tgts:  Dict[str, list] = {}

    with torch.no_grad():
        for images, targets in tqdm(loader, desc=f"Evaluating [{split}]"):
            images = images.to(device)
            preds  = model(images)
            for task_name, pred in preds.items():
                all_preds.setdefault(task_name, []).append(pred.cpu())
            for task_name, tgt in targets.items():
                all_tgts.setdefault(task_name, []).append(tgt.cpu())

    concat_preds   = {k: torch.cat(v) for k, v in all_preds.items()}
    concat_targets = {k: torch.cat(v) for k, v in all_tgts.items()}

    # ── Overall metrics ───────────────────────────────────────────────────
    metrics = compute_metrics(model, concat_preds, concat_targets)

    # ── Per-task classification reports ───────────────────────────────────
    per_task_reports: Dict[str, str] = {}

    for task_name, pred in concat_preds.items():
        if task_name not in concat_targets:
            continue

        config      = model.get_task_config(task_name)
        tgt         = concat_targets[task_name]
        class_names = list(ds.label_encoders[task_name].classes_)

        if config.get("multi_label", False):
            pred_bin = (torch.sigmoid(pred) > 0.5).float().numpy()
            report = classification_report(
                tgt.numpy(), pred_bin,
                target_names=class_names,
                zero_division=0,
            )
        else:
            pred_cls = pred.argmax(dim=1).numpy()
            tgt_np   = tgt.numpy()
            # Only report classes actually present in this split — the test set
            # may not contain all training classes.
            labels_present = sorted(np.unique(tgt_np).tolist())
            names_present  = [class_names[i] for i in labels_present]
            report = classification_report(
                tgt_np, pred_cls,
                labels=labels_present,
                target_names=names_present,
                zero_division=0,
            )

        per_task_reports[task_name] = report

    return metrics, per_task_reports


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Evaluate a saved MultiTaskArchitecturalClassifier checkpoint.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--checkpoint", required=True, help="Path to .pth checkpoint file")
    parser.add_argument("--csv", required=True, help="Label-mapping CSV used during training")
    parser.add_argument(
        "--model-config", default="config/models/resnet50.json",
        help="Path to a config/models/*.json backbone preset",
    )
    parser.add_argument("--split", default="test", choices=["train", "val", "test"])
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument(
        "--prefetch-factor", type=int, default=4,
        help="Batches to prefetch per worker (persistent_workers always enabled when num_workers>0).",
    )
    parser.add_argument(
        "--cropped-root", default=None,
        help="Root directory of pre-cropped images (from scripts/crop_dataset.py). "
             "When set, crops are preferred over originals. Omit to use original images.",
    )
    parser.add_argument("--output", default=None, help="Path to save JSON report (optional)")
    args = parser.parse_args()

    cfg = ModelConfig.from_json(args.model_config)

    metrics, per_task_reports = evaluate(
        checkpoint_path=args.checkpoint,
        csv_path=args.csv,
        model_config=cfg,
        split=args.split,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        prefetch_factor=args.prefetch_factor,
        cropped_root=args.cropped_root,
    )

    # ── Print summary ─────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"  EVALUATION REPORT  —  {args.split.upper()} SPLIT")
    print(f"  Checkpoint : {args.checkpoint}")
    print(f"  Dataset    : {args.csv}")
    print("=" * 70)
    print(format_metrics_table(metrics))

    # ── Print per-task classification reports ─────────────────────────────
    for task_name, report in per_task_reports.items():
        print(f"\n{'─' * 70}")
        print(f"  {task_name}")
        print(f"{'─' * 70}")
        print(report)

    # ── Save JSON ─────────────────────────────────────────────────────────
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w") as f:
            json.dump(
                {
                    "checkpoint": args.checkpoint,
                    "csv": args.csv,
                    "split": args.split,
                    "metrics": metrics,
                },
                f,
                indent=2,
            )
        print(f"\nJSON report saved \u2192 {out_path}")


if __name__ == "__main__":
    main()
