"""ExperimentLogger — thin MLflow wrapper for training run tracking.

Logs all RunConfig parameters, per-epoch train/val metrics as time-series
curves, final per-task metrics at the best epoch, and the checkpoint path.

Falls back gracefully if mlflow is not installed — all calls become no-ops so
training is never blocked by a missing optional dependency.

Usage::

    logger = ExperimentLogger(run_config, experiment_name="arepas-phase1")
    logger.start()

    for epoch in range(1, epochs + 1):
        # ... train + validate ...
        logger.log_epoch(epoch, train_losses, val_losses, val_metrics)
        if is_best:
            logger.log_best_checkpoint(epoch, val_losses, val_metrics, ckpt_path)

    logger.end()
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from src.models.run_config import RunConfig

logger = logging.getLogger(__name__)

try:
    import mlflow
    _MLFLOW_AVAILABLE = True
except ImportError:
    _MLFLOW_AVAILABLE = False
    logger.warning(
        "mlflow not installed — experiment tracking disabled. "
        "Run: pip install mlflow"
    )


class ExperimentLogger:
    """Wraps an MLflow run for one training phase.

    All public methods are safe to call even when mlflow is not installed —
    they simply become no-ops, so training is never interrupted.
    """

    def __init__(
        self,
        run_config: "RunConfig",  # noqa: F821 — avoids circular import at type-check time
        experiment_name: str = "arepas",
        tracking_uri: str = "sqlite:///mlflow.db",
    ) -> None:
        self.run_config = run_config
        self.experiment_name = experiment_name
        self.tracking_uri = tracking_uri
        self._run = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start an MLflow run and log all RunConfig fields as parameters."""
        if not _MLFLOW_AVAILABLE:
            return
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(self.experiment_name)
        self._run = mlflow.start_run(run_name=self.run_config.run_name)
        mlflow.log_params(self.run_config.as_flat_dict())
        logger.info(
            f"MLflow run started: {self.run_config.run_name} "
            f"(experiment: {self.experiment_name})"
        )

    def end(self) -> None:
        """End the active MLflow run."""
        if not _MLFLOW_AVAILABLE or self._run is None:
            return
        mlflow.end_run()
        self._run = None

    # ── Per-epoch logging ─────────────────────────────────────────────────────

    def log_epoch(
        self,
        epoch: int,
        train_losses: Dict[str, float],
        val_losses: Dict[str, float],
        val_metrics: Dict[str, Any],
    ) -> None:
        """Log train/val losses and per-task metrics for one epoch."""
        if not _MLFLOW_AVAILABLE or self._run is None:
            return

        metrics: Dict[str, float] = {}

        # Losses
        for k, v in train_losses.items():
            metrics[f"train_loss_{k}"] = v
        for k, v in val_losses.items():
            metrics[f"val_loss_{k}"] = v

        # Per-task val metrics — stored as percentages (0–100) for readability
        for task, vals in val_metrics.items():
            if task == "overall_accuracy":
                metrics["val_overall_accuracy"] = float(vals) * 100
            elif isinstance(vals, dict):
                for metric_name, metric_val in vals.items():
                    metrics[f"val_{task}_{metric_name}"] = float(metric_val) * 100

        mlflow.log_metrics(metrics, step=epoch)

    # ── Best checkpoint ───────────────────────────────────────────────────────

    def log_best_checkpoint(
        self,
        epoch: int,
        val_losses: Dict[str, float],
        val_metrics: Dict[str, Any],
        checkpoint_path: Optional[str] = None,
    ) -> None:
        """Log the metrics at the best epoch and record the checkpoint path."""
        if not _MLFLOW_AVAILABLE or self._run is None:
            return

        mlflow.log_metric("best_epoch", epoch)
        mlflow.log_metric("best_val_loss", val_losses.get("total", 0.0))

        overall = val_metrics.get("overall_accuracy")
        if overall is not None:
            mlflow.log_metric("best_overall_accuracy", float(overall) * 100)

        for task, vals in val_metrics.items():
            if task == "overall_accuracy" or not isinstance(vals, dict):
                continue
            primary = vals.get("acc") or vals.get("jaccard") or vals.get("exact")
            if primary is not None:
                mlflow.log_metric(f"best_{task}_accuracy", float(primary) * 100)
            f1 = vals.get("f1")
            if f1 is not None:
                mlflow.log_metric(f"best_{task}_f1", float(f1) * 100)

        if checkpoint_path and Path(checkpoint_path).exists():
            mlflow.set_tag("best_checkpoint_path", checkpoint_path)

    # ── Context manager support ───────────────────────────────────────────────

    def __enter__(self) -> "ExperimentLogger":
        self.start()
        return self

    def __exit__(self, *_: Any) -> None:
        self.end()
