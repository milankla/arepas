"""backfill_mlflow.py — Import pre-ExperimentLogger training runs into MLflow.

Reads each training_history.json that was produced by the old trainer and logs
every epoch as a time-series metric, plus summary params inferred from the run.

Usage::

    python scripts/backfill_mlflow.py
    # or point at a specific history file:
    python scripts/backfill_mlflow.py --history outputs/phase1/training_history.json
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import mlflow

# ── Known run metadata ────────────────────────────────────────────────────────
# Keyed by the outputs directory name so we can attach the right params even
# though run_config.json didn't exist yet for these runs.
KNOWN_RUNS: dict[str, dict] = {
    "outputs": {
        "run_name": "resnet50_data_ph1-1_lr1e-04_bs16_ep20_legacy",
        "csv_path": "data/image_label_mapping_phase1.csv",
        "dataset_version": "data",
        "backbone": "resnet50",
        "epochs": 20,
        "batch_size": 16,
        "lr": 1e-4,
        "num_workers": 0,
        "early_stopping_patience": None,
        "roof_type_encoding": "multi_label_19",
        "note": "Phase-1 baseline on original data/",
    },
    "v1": {
        "run_name": "resnet50_data2_ph1-1_lr1e-04_bs32_ep8_legacy_multi_roof",
        "csv_path": "data2/image_label_mapping_phase1.csv",
        "dataset_version": "data2",
        "backbone": "resnet50",
        "epochs": 30,
        "batch_size": 32,
        "lr": 1e-4,
        "num_workers": 2,
        "early_stopping_patience": 5,
        "roof_type_encoding": "multi_label_19",
        "note": "data2 v1 — multi-label roof_type, stopped epoch 8",
    },
    "v2": {
        "run_name": "resnet50_data2_ph1-1_lr1e-04_bs32_ep8_legacy_single_roof_pat5",
        "csv_path": "data2/image_label_mapping_phase1.csv",
        "dataset_version": "data2",
        "backbone": "resnet50",
        "epochs": 30,
        "batch_size": 32,
        "lr": 1e-4,
        "num_workers": 2,
        "early_stopping_patience": 5,
        "roof_type_encoding": "single_label_compound",
        "note": "data2 v2 — single-label roof, patience=5, stopped epoch 8",
    },
    "v3": {
        "run_name": "resnet50_data2_ph1-1_lr1e-04_bs32_ep30_legacy_single_roof_nopat",
        "csv_path": "data2/image_label_mapping_phase1.csv",
        "dataset_version": "data2",
        "backbone": "resnet50",
        "epochs": 30,
        "batch_size": 32,
        "lr": 1e-4,
        "num_workers": 2,
        "early_stopping_patience": None,
        "roof_type_encoding": "single_label_compound",
        "note": "data2 v3 — single-label roof, 30 full epochs (best acc 77.2% ep10)",
    },
}


def _flat_metrics(d: dict, prefix: str = "") -> dict[str, float]:
    """Recursively flatten a nested metrics dict into underscore-separated keys.

    Uses underscores (not dots) to match the key format emitted by
    ExperimentLogger.log_epoch(), e.g. 'val_stories_acc' not 'val.stories.acc'.
    All float values are stored as percentages (×100) so the MLflow UI
    shows e.g. 77.21 instead of 0.7721.
    """
    out: dict[str, float] = {}
    for k, v in d.items():
        key = f"{prefix}{k}" if not prefix else f"{prefix}_{k}"
        if isinstance(v, dict):
            out.update(_flat_metrics(v, key))
        elif isinstance(v, (int, float)):
            out[key] = float(v) * 100
    return out


def backfill_run(history_path: Path, tracking_uri: str = "mlruns") -> None:
    history_path = Path(history_path)
    # Infer run dir name (e.g. "v3") — two levels up from the history file.
    run_dir = history_path.parent.parent.name   # phase1 -> parent -> v3 (under outputs/data2/)
    meta = KNOWN_RUNS.get(run_dir, {})
    run_name = meta.get("run_name") or f"legacy_{run_dir}"

    with open(history_path) as fh:
        history: list[dict] = json.load(fh)

    if not history:
        print(f"  [skip] empty history: {history_path}")
        return

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("arepas")

    with mlflow.start_run(run_name=run_name):
        # Log known params
        params = {k: (str(v) if v is None else v) for k, v in meta.items()
                  if k != "note"}
        params["backfilled"] = "true"
        if "note" in meta:
            params["note"] = meta["note"]
        mlflow.log_params(params)

        best_val_loss = float("inf")
        best_epoch = None

        for entry in history:
            epoch: int = entry["epoch"]
            train_losses: dict = entry.get("train_losses", {})
            val_losses: dict = entry.get("val_losses", {})
            val_metrics: dict = entry.get("val_metrics", {})

            metrics: dict[str, float] = {}
            for k, v in train_losses.items():
                metrics[f"train_loss_{k}"] = v
            for k, v in val_losses.items():
                metrics[f"val_loss_{k}"] = v
            metrics.update(_flat_metrics(val_metrics, "val"))

            mlflow.log_metrics(metrics, step=epoch)

            total_val = val_losses.get("total", float("inf"))
            if total_val < best_val_loss:
                best_val_loss = total_val
                best_epoch = epoch

        # Summary scalars visible in the Runs table
        mlflow.log_metric("best_val_loss", best_val_loss)
        if best_epoch is not None:
            mlflow.log_param("best_epoch", best_epoch)

        # Best and peak overall accuracy across all epochs
        all_accs = [
            e["val_metrics"].get("overall_accuracy", 0.0) for e in history
        ]
        if all_accs:
            mlflow.log_metric("best_overall_accuracy",
                              history[best_epoch - 1]["val_metrics"].get("overall_accuracy", 0.0) * 100
                              if best_epoch else 0.0)
            mlflow.log_metric("peak_overall_accuracy", max(all_accs) * 100)

    print(f"  ✓ {run_name}  ({len(history)} epochs, best val_loss={best_val_loss:.4f} @ ep{best_epoch})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill legacy training runs into MLflow.")
    parser.add_argument(
        "--history", nargs="*",
        help="Explicit training_history.json path(s). Auto-discovers outputs*/phase1/ if omitted.",
    )
    parser.add_argument(
        "--tracking-uri", default="sqlite:///mlflow.db",
        help="MLflow tracking URI (default: sqlite:///mlflow.db in cwd).",
    )
    parser.add_argument(
        "--skip-smoke-tests", action="store_true", default=True,
        help="Skip runs whose output dir contains 'smoke' (default: True).",
    )
    args = parser.parse_args()

    if args.history:
        paths = [Path(p) for p in args.history]
    else:
        root = Path(__file__).parent.parent
        paths = sorted(root.glob("outputs*/phase1/training_history.json"))
        if args.skip_smoke_tests:
            paths = [p for p in paths if "smoke" not in str(p)]

    print(f"Backfilling {len(paths)} run(s) into MLflow ({args.tracking_uri})…\n")
    os.chdir(Path(__file__).parent.parent)   # ensure mlruns/ lands in project root

    for p in paths:
        print(f"→ {p}")
        try:
            backfill_run(p, tracking_uri=args.tracking_uri)
        except Exception as exc:
            print(f"  [error] {exc}")

    print("\nDone. Open http://127.0.0.1:5001 to view all runs.")


if __name__ == "__main__":
    main()
