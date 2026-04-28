"""
Multi-Task Training Script

Progressive training strategy:
1. Phase 1 (Week 1-2): Easy tasks (stories, roof type, cladding)
2. Phase 2 (Week 3-4): Add architectural style, building form
3. Phase 3 (Week 5-6): Add fine-grained features
4. Phase 4 (Week 7-8): Add alteration detection
"""

import argparse
import warnings
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from typing import Any, Dict, List, Tuple, Optional
import logging
from pathlib import Path
from tqdm import tqdm
import json

from src.models.multi_task_classifier import MultiTaskArchitecturalClassifier, MultiTaskLoss
from src.models.model_config import ModelConfig
from src.models.metrics import compute_metrics, format_metrics_table
from src.loader.architectural_dataset import make_splits
from src.models.run_config import RunConfig
from src.models.experiment_logger import ExperimentLogger


logger = logging.getLogger(__name__)


class MultiTaskTrainer:
    """
    Trainer for progressive multi-task learning
    """
    
    def __init__(
        self,
        model: MultiTaskArchitecturalClassifier,
        train_loader: DataLoader,
        val_loader: DataLoader,
        device: str = 'cuda',
        learning_rate: float = 1e-4,
        output_dir: str = './outputs',
        max_batches: Optional[int] = None,
        early_stopping_patience: Optional[int] = None,
        experiment_logger: Optional[ExperimentLogger] = None,
        class_weights: Optional[Dict[str, torch.Tensor]] = None,
    ):
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.device = device
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # If set, each epoch/validation phase stops after this many batches.
        # Useful for smoke tests without needing a separate tiny dataset.
        self.max_batches = max_batches
        # Early stopping: stop if val_loss doesn't improve for this many epochs.
        self.early_stopping_patience = early_stopping_patience
        self._epochs_without_improvement = 0
        self.experiment_logger = experiment_logger
        
        # Optimizer and loss
        self.optimizer = optim.AdamW(
            model.parameters(),
            lr=learning_rate,
            weight_decay=0.01
        )
        self.criterion = MultiTaskLoss(
            active_phase=model.active_phase,
            class_weights=class_weights,
        ).to(device)
        
        # Learning rate scheduler
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=3,
        )
        
        # Tracking
        self.best_val_loss = float('inf')
        self.training_history = []
    
    def train_epoch(self, epoch: int) -> Dict[str, float]:
        """Train for one epoch"""
        self.model.train()
        
        epoch_losses = {}
        total_samples = 0
        
        pbar = tqdm(self.train_loader, desc=f"Epoch {epoch} [Train]")
        for batch_idx, (images, targets) in enumerate(pbar):
            if self.max_batches is not None and batch_idx >= self.max_batches:
                break
            images = images.to(self.device)
            targets = {k: v.to(self.device) for k, v in targets.items()}

            # Forward pass
            self.optimizer.zero_grad()
            predictions = self.model(images)
            
            # Calculate losses
            losses = self.criterion(predictions, targets)
            total_loss = losses['total']
            
            # Backward pass
            total_loss.backward()
            
            # Gradient clipping for stability
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            
            self.optimizer.step()
            
            # Accumulate losses
            batch_size = images.size(0)
            total_samples += batch_size
            
            for loss_name, loss_value in losses.items():
                if loss_name not in epoch_losses:
                    epoch_losses[loss_name] = 0.0
                epoch_losses[loss_name] += loss_value.item() * batch_size
            
            # Update progress bar
            pbar.set_postfix({'loss': total_loss.item()})
        
        # Average losses
        epoch_losses = {k: v / total_samples for k, v in epoch_losses.items()}
        return epoch_losses
    
    def validate(self, epoch: int) -> Tuple[Dict[str, float], Dict[str, Any]]:
        """Validate model.

        Collects all predictions and targets across batches first, then computes
        metrics in one shot so macro F1 is accurate (not a batch-wise average).

        Returns:
            (avg_losses, metrics) where metrics is the nested dict from
            compute_metrics() — includes per-task accuracy/F1 and 'overall_accuracy'.
        """
        self.model.eval()

        all_losses: Dict[str, float]               = {}
        all_preds:  Dict[str, List[torch.Tensor]]  = {}
        all_tgts:   Dict[str, List[torch.Tensor]]  = {}
        total_samples = 0

        with torch.no_grad():
            pbar = tqdm(self.val_loader, desc=f"Epoch {epoch} [Val]")
            for batch_idx, (images, targets) in enumerate(pbar):
                if self.max_batches is not None and batch_idx >= self.max_batches:
                    break
                images  = images.to(self.device)
                targets = {k: v.to(self.device) for k, v in targets.items()}

                predictions = self.model(images)
                losses      = self.criterion(predictions, targets)

                batch_size = images.size(0)
                total_samples += batch_size

                for loss_name, loss_value in losses.items():
                    all_losses[loss_name] = (
                        all_losses.get(loss_name, 0.0) + loss_value.item() * batch_size
                    )

                for task_name, pred in predictions.items():
                    all_preds.setdefault(task_name, []).append(pred.cpu())
                for task_name, tgt in targets.items():
                    all_tgts.setdefault(task_name, []).append(tgt.cpu())

                pbar.set_postfix({'loss': losses['total'].item()})

        avg_losses = {k: v / total_samples for k, v in all_losses.items()}

        # Compute metrics over the full validation set in one shot (accurate macro F1).
        concat_preds   = {k: torch.cat(v) for k, v in all_preds.items()}
        concat_targets = {k: torch.cat(v) for k, v in all_tgts.items()}
        metrics = compute_metrics(self.model, concat_preds, concat_targets)

        return avg_losses, metrics

    def train(self, num_epochs: int):
        """
        Full training loop
        """
        logger.info(f"Starting training for {num_epochs} epochs")
        logger.info(f"Model phase: {self.model.active_phase}")
        logger.info(f"Active tasks: {list(self.model.task_heads.keys())}")
        
        for epoch in range(1, num_epochs + 1):
            train_losses = self.train_epoch(epoch)
            val_losses, val_metrics = self.validate(epoch)

            self.scheduler.step(val_losses['total'])
            self._log_epoch_results(epoch, train_losses, val_losses, val_metrics)
            if self.experiment_logger is not None:
                self.experiment_logger.log_epoch(epoch, train_losses, val_losses, val_metrics)

            if val_losses['total'] < self.best_val_loss:
                self.best_val_loss = val_losses['total']
                self._save_checkpoint(epoch, val_losses, val_metrics, is_best=True)
                logger.info(f"✓ New best model saved (val_loss: {self.best_val_loss:.4f})")
                if self.experiment_logger is not None:
                    _best_ckpt = str(
                        self.output_dir / f"best_model_phase{self.model.active_phase}.pth"
                    )
                    self.experiment_logger.log_best_checkpoint(
                        epoch, val_losses, val_metrics, _best_ckpt
                    )
                self._epochs_without_improvement = 0
            else:
                self._epochs_without_improvement += 1

            if epoch % 5 == 0:
                self._save_checkpoint(epoch, val_losses, val_metrics, is_best=False)

            if (
                self.early_stopping_patience is not None
                and self._epochs_without_improvement >= self.early_stopping_patience
            ):
                logger.info(
                    f"Early stopping triggered: no improvement for "
                    f"{self.early_stopping_patience} consecutive epochs. "
                    f"Best val_loss: {self.best_val_loss:.4f}"
                )
                break
    
    def _log_epoch_results(
        self,
        epoch: int,
        train_losses: Dict[str, float],
        val_losses: Dict[str, float],
        val_metrics: Dict[str, Any],
    ):
        """Log training results and save to history."""
        overall = val_metrics.get('overall_accuracy', 0.0)
        logger.info(
            f"\nEpoch {epoch}"
            f"  |  Train Loss: {train_losses['total']:.4f}"
            f"  |  Val Loss: {val_losses['total']:.4f}"
            f"  |  Overall Acc: {overall:.4f}"
        )
        logger.info(format_metrics_table(val_metrics))

        self.training_history.append({
            'epoch': epoch,
            'train_losses': train_losses,
            'val_losses': val_losses,
            'val_metrics': val_metrics,
        })
    
    def _save_checkpoint(
        self,
        epoch: int,
        val_losses: Dict[str, float],
        val_metrics: Dict[str, Any],
        is_best: bool = False,
    ):
        """Save model checkpoint."""
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'val_losses': val_losses,
            'val_metrics': val_metrics,
            'best_val_loss': self.best_val_loss,
            'active_phase': self.model.active_phase,
            'num_classes': dict(self.model._num_classes_override),
        }
        
        # Save best model
        if is_best:
            path = self.output_dir / f'best_model_phase{self.model.active_phase}.pth'
            torch.save(checkpoint, path)
        
        # Save latest
        path = self.output_dir / f'checkpoint_epoch{epoch}.pth'
        torch.save(checkpoint, path)
        
        # Save training history
        history_path = self.output_dir / 'training_history.json'
        with open(history_path, 'w') as f:
            json.dump(self.training_history, f, indent=2)


# ── Phase metadata ───────────────────────────────────────────────────────────

_PHASE_NAMES: Dict[int, str] = {
    1: "EASY VISUAL FEATURES (stories, roof type, cladding)",
    2: "ARCHITECTURAL CLASSIFICATION (+ style, building form)",
    3: "FINE-GRAINED FEATURES",
    4: "ALTERATION DETECTION",
}


# ── DataLoader factory ────────────────────────────────────────────────────────

def build_dataloaders(
    csv_path: str,
    model_config: ModelConfig,
    batch_size: int = 32,
    num_workers: int = 4,
) -> Tuple[DataLoader, DataLoader, DataLoader, Dict[str, int], Dict[str, torch.Tensor]]:
    """Build train / val / test DataLoaders from any CSV + ModelConfig.

    Dataset-agnostic — works with data/ or data2/ (or any future dataset)
    provided the CSV was produced by build_phase1_label_mapping.py.

    Model-agnostic — image resolution and normalisation statistics are taken
    from ``model_config``, so the same call works for ResNet, EfficientNet,
    CLIP, ViT, etc.

    Args:
        csv_path:     Path to the label-mapping CSV.
        model_config: Backbone configuration (drives image_size + norm stats).
        batch_size:   Samples per GPU batch.
        num_workers:  DataLoader worker processes.

    Returns:
        (train_loader, val_loader, test_loader, num_classes, class_weights)
        where num_classes is {task_name: int} and class_weights is
        {task_name: FloatTensor[n_classes]}, both derived from the training split.
    """
    train_ds, val_ds, test_ds = make_splits(
        csv_path=csv_path,
        model_config=model_config,
    )
    logger.info(
        f"Dataset splits — train: {len(train_ds)}, "
        f"val: {len(val_ds)}, test: {len(test_ds)}"
    )
    logger.info(
        "Class counts per task: "
        + ", ".join(f"{k}: {v}" for k, v in train_ds.num_classes.items())
    )

    pin = torch.cuda.is_available()

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=pin,
        drop_last=True,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin,
    )
    test_loader = DataLoader(
        test_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin,
    )
    return train_loader, val_loader, test_loader, train_ds.num_classes, train_ds.class_weights


# ── Pipeline ──────────────────────────────────────────────────────────────────

def progressive_training_pipeline(
    csv_path: str,
    model_config: ModelConfig,
    start_phase: int = 1,
    end_phase: int = 1,
    epochs_per_phase: int = 20,
    batch_size: int = 32,
    lr: float = 1e-4,
    output_dir: Optional[str] = None,
    num_workers: int = 4,
    max_batches: Optional[int] = None,
    early_stopping_patience: Optional[int] = None,
    run_name: Optional[str] = None,
    dataset_version: str = "",
    model_config_path: str = "",
) -> None:
    """Dataset- and model-agnostic progressive training pipeline.

    Builds DataLoaders once (shared across all phases), then trains a
    MultiTaskArchitecturalClassifier for each requested phase.  Each phase
    warm-starts from the previous phase's best checkpoint — shared backbone
    weights and earlier task heads are transferred via non-strict loading.

    Args:
        csv_path:          Label-mapping CSV (any dataset: data/ or data2/).
        model_config:      Backbone config — drives backbone choice, input
                           resolution, and normalisation statistics.
        start_phase:       First phase to train (1–4).
        end_phase:         Last phase to train inclusive (1–4).
        epochs_per_phase:  Training epochs per phase.
        batch_size:        Samples per GPU batch.
        lr:                AdamW initial learning rate.
        output_dir:        Root output directory; phase sub-dirs created here.
        num_workers:       DataLoader worker processes.
        max_batches:       If set, each train/val pass stops after this many
                           batches.  Useful for smoke tests on full datasets.
    """
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"
    logger.info(
        f"Device: {device} | Backbone: {model_config.backbone} | "
        f"CSV: {csv_path} | Phases: {start_phase}\u2013{end_phase}"
    )

    # Build loaders once — image size and norm stats come from model_config.
    train_loader, val_loader, _, num_classes, class_weights = build_dataloaders(
        csv_path=csv_path,
        model_config=model_config,
        batch_size=batch_size,
        num_workers=num_workers,
    )

    # Build a RunConfig to capture all parameters that define this run.
    run_cfg = RunConfig(
        csv_path=csv_path,
        dataset_version=dataset_version,
        backbone=model_config.backbone,
        model_config_path=model_config_path or "config/models/resnet50.json",
        start_phase=start_phase,
        end_phase=end_phase,
        epochs=epochs_per_phase,
        batch_size=batch_size,
        lr=lr,
        num_workers=num_workers,
        early_stopping_patience=early_stopping_patience,
        run_name=run_name or "",
    )
    # Derive output dir from the auto-slug if not explicitly provided.
    if output_dir is None:
        output_dir = f"runs/{run_cfg.run_name}"
    run_cfg.output_dir = output_dir
    logger.info(f"Run: {run_cfg.run_name}  ->  {output_dir}")

    prev_checkpoint: Optional[str] = None

    for phase in range(start_phase, end_phase + 1):
        print("\n" + "=" * 60)
        print(f"PHASE {phase}: {_PHASE_NAMES.get(phase, f'Phase {phase}')}")
        print("=" * 60)

        phase_out = Path(output_dir) / f"phase{phase}"

        # Per-phase RunConfig snapshot — written to phase_out/run_config.json.
        _phase_run_name = (
            f"{run_cfg.run_name}_ph{phase}" if start_phase != end_phase
            else run_cfg.run_name
        )
        phase_cfg = RunConfig(
            csv_path=run_cfg.csv_path,
            dataset_version=run_cfg.dataset_version,
            backbone=run_cfg.backbone,
            model_config_path=run_cfg.model_config_path,
            start_phase=phase,
            end_phase=phase,
            epochs=run_cfg.epochs,
            batch_size=run_cfg.batch_size,
            lr=run_cfg.lr,
            num_workers=run_cfg.num_workers,
            early_stopping_patience=run_cfg.early_stopping_patience,
            run_name=_phase_run_name,
            output_dir=str(phase_out),
        )
        phase_cfg.save(phase_out)

        model = MultiTaskArchitecturalClassifier(
            backbone=model_config.backbone,
            weights="DEFAULT",
            active_phase=phase,
            freeze_backbone=False,
            num_classes=num_classes,   # data-driven head sizes
        )

        # Warm-start: transfer backbone + earlier task heads from previous phase.
        if prev_checkpoint is not None and Path(prev_checkpoint).exists():
            ckpt = torch.load(prev_checkpoint, map_location="cpu")
            missing, unexpected = model.load_state_dict(
                ckpt["model_state_dict"], strict=False
            )
            logger.info(
                f"Phase {phase} warm-start \u2190 phase {phase - 1} checkpoint "
                f"({len(missing)} missing keys, {len(unexpected)} unexpected)"
            )

        with ExperimentLogger(phase_cfg, experiment_name="arepas") as exp_logger:
            trainer = MultiTaskTrainer(
                model=model,
                train_loader=train_loader,
                val_loader=val_loader,
                device=device,
                learning_rate=lr,
                output_dir=str(phase_out),
                max_batches=max_batches,
                early_stopping_patience=early_stopping_patience,
                experiment_logger=exp_logger,
                class_weights=class_weights,
            )
            trainer.train(num_epochs=epochs_per_phase)

        best_ckpt = phase_out / f"best_model_phase{phase}.pth"
        if best_ckpt.exists():
            prev_checkpoint = str(best_ckpt)
        logger.info(f"Phase {phase} complete. Best checkpoint \u2192 {best_ckpt}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Progressive multi-task training — dataset- and model-agnostic.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--csv",
        required=True,
        help=(
            "Path to the label-mapping CSV "
            "(e.g. data/image_label_mapping_phase1.csv or "
            "data2/image_label_mapping_phase1.csv)"
        ),
    )
    parser.add_argument(
        "--model-config",
        default="config/models/resnet50.json",
        help="Path to a config/models/*.json backbone preset.",
    )
    parser.add_argument(
        "--start-phase", type=int, default=1, choices=[1, 2, 3, 4],
        help="First phase to train.",
    )
    parser.add_argument(
        "--end-phase", type=int, default=1, choices=[1, 2, 3, 4],
        help="Last phase to train (inclusive).",
    )
    parser.add_argument(
        "--epochs", type=int, default=20,
        help="Training epochs per phase.",
    )
    parser.add_argument(
        "--batch-size", type=int, default=32,
    )
    parser.add_argument(
        "--lr", type=float, default=1e-4,
        help="AdamW initial learning rate.",
    )
    parser.add_argument(
        "--run-name", default=None,
        help=(
            "Human-readable name for this run. "
            "Auto-generates a slug from backbone/dataset/lr/etc. if omitted."
        ),
    )
    parser.add_argument(
        "--dataset-version", default="",
        help="Short label for the dataset (e.g. 'data2'). Auto-derived if omitted.",
    )
    parser.add_argument(
        "--output-dir", default=None,
        help=(
            "Root directory for checkpoints and training history. "
            "Defaults to runs/<auto-slug>/ if omitted."
        ),
    )
    parser.add_argument(
        "--num-workers", type=int, default=4,
        help="DataLoader worker processes.",
    )
    parser.add_argument(
        "--max-batches", type=int, default=None,
        help=(
            "Stop each train/val pass after this many batches. "
            "Use --max-batches 3 for a quick smoke test on the full dataset."
        ),
    )
    parser.add_argument(
        "--early-stopping-patience", type=int, default=None,
        help=(
            "Stop training if val_loss does not improve for this many consecutive "
            "epochs. Omit to disable early stopping."
        ),
    )
    args = parser.parse_args()

    cfg = ModelConfig.from_json(args.model_config)

    progressive_training_pipeline(
        csv_path=args.csv,
        model_config=cfg,
        start_phase=args.start_phase,
        end_phase=args.end_phase,
        epochs_per_phase=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        output_dir=args.output_dir,
        num_workers=args.num_workers,
        max_batches=args.max_batches,
        early_stopping_patience=args.early_stopping_patience,
        run_name=args.run_name,
        dataset_version=args.dataset_version,
        model_config_path=args.model_config,
    )
