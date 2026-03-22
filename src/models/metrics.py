"""
Per-task evaluation metrics for multi-task architectural classification.

Exported:
    compute_metrics(model, predictions, targets)  → Dict[str, Any]
    format_metrics_table(metrics)                 → str
"""
from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any, Dict, List

import numpy as np
import torch
from sklearn.metrics import f1_score, hamming_loss

if TYPE_CHECKING:
    from src.models.multi_task_classifier import MultiTaskArchitecturalClassifier


def compute_metrics(
    model: "MultiTaskArchitecturalClassifier",
    predictions: Dict[str, torch.Tensor],
    targets: Dict[str, torch.Tensor],
) -> Dict[str, Any]:
    """Compute per-task accuracy + macro F1, and an overall accuracy.

    Evaluates each active task head against the provided targets.  Tasks whose
    names are absent from ``targets`` (e.g. chimney_present / setting when those
    columns are not yet in the CSV) are silently skipped.

    Single-label tasks  → {task: {'acc': float, 'f1': float}}
    Multi-label tasks   → {task: {'exact': float, 'hamming': float, 'f1': float}}
    Top-level           → 'overall_accuracy': float  (unweighted mean of primary acc)

    Args:
        model:       The classifier — used only to call get_task_config per task.
        predictions: Raw logit tensors keyed by task name.
        targets:     Ground-truth tensors keyed by task name.

    Returns:
        Nested metrics dict with 'overall_accuracy' at the top level.
    """
    task_metrics: Dict[str, Any] = {}
    primary_accs: List[float] = []

    for task_name, pred in predictions.items():
        if task_name not in targets:
            continue

        config = model.get_task_config(task_name)
        tgt    = targets[task_name]

        if config.get("multi_label", False):
            pred_bin = (torch.sigmoid(pred) > 0.5).float().numpy()
            tgt_np   = tgt.numpy()

            exact = float((pred_bin == tgt_np).all(axis=1).mean())
            hamm  = float(1.0 - hamming_loss(tgt_np, pred_bin))
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                f1 = float(f1_score(tgt_np, pred_bin, average="macro", zero_division=0))

            task_metrics[task_name] = {"exact": exact, "hamming": hamm, "f1": f1}
            primary_accs.append(exact)
        else:
            pred_cls = pred.argmax(dim=1).numpy()
            tgt_np   = tgt.numpy()

            acc = float((pred_cls == tgt_np).mean())
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                f1 = float(f1_score(tgt_np, pred_cls, average="macro", zero_division=0))

            task_metrics[task_name] = {"acc": acc, "f1": f1}
            primary_accs.append(acc)

    task_metrics["overall_accuracy"] = float(np.mean(primary_accs)) if primary_accs else 0.0
    return task_metrics


def format_metrics_table(metrics: Dict[str, Any]) -> str:
    """Format a compute_metrics() dict as a readable multi-line table string.

    Args:
        metrics: Output of compute_metrics().

    Returns:
        A multi-line string suitable for logger.info() or print().
    """
    lines: List[str] = []

    overall = metrics.get("overall_accuracy")
    if overall is not None:
        lines.append(f"  Overall Accuracy : {overall:.4f}")

    lines.append("")
    lines.append(f"  {'Task':<25} {'Metric':<13} {'Value':>7}   {'Macro F1':>8}")
    lines.append("  " + "\u2500" * 58)

    for task_name, vals in metrics.items():
        if task_name == "overall_accuracy" or not isinstance(vals, dict):
            continue

        if "exact" in vals:
            label   = "exact-match"
            acc_val = vals["exact"]
            extra   = f"   hamming={vals.get('hamming', 0):.4f}"
        else:
            label   = "accuracy"
            acc_val = vals.get("acc", 0.0)
            extra   = ""

        f1 = vals.get("f1", 0.0)
        lines.append(
            f"  {task_name:<25} {label:<13} {acc_val:>7.4f}   {f1:>8.4f}{extra}"
        )

    return "\n".join(lines)
