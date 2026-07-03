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

from src.models.multi_task_classifier import (
    MultiTaskArchitecturalClassifier,
    MultiTaskLoss,
    TaskConfig,
    normalize_paired_fusion_state_dict,
)
from src.models.model_config import ModelConfig
from src.models.metrics import compute_metrics, format_metrics_table
from src.loader.architectural_dataset import make_splits
from src.models.run_config import RunConfig
from src.models.experiment_logger import ExperimentLogger


logger = logging.getLogger(__name__)


ImageBatch = torch.Tensor | Dict[str, torch.Tensor]


def _parse_task_float_map(value: Optional[str]) -> Dict[str, float]:
    if not value:
        return {}
    result: Dict[str, float] = {}
    for item in value.split(','):
        item = item.strip()
        if not item:
            continue
        if '=' not in item:
            raise ValueError(f"Expected task=value in '{item}'")
        task, raw_value = item.split('=', 1)
        result[task.strip()] = float(raw_value)
    return result


def _parse_task_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def _move_images_to_device(images: ImageBatch, device: str) -> ImageBatch:
    if isinstance(images, dict):
        return {k: v.to(device) for k, v in images.items()}
    return images.to(device)


def _image_batch_size(images: ImageBatch) -> int:
    if isinstance(images, dict):
        return next(iter(images.values())).size(0)
    return images.size(0)


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
        weight_decay: float = 0.01,
        grad_accum_steps: int = 1,
        output_dir: str = './outputs',
        max_batches: Optional[int] = None,
        early_stopping_patience: Optional[int] = None,
        early_stop_metric: str = 'val_loss',
        early_stop_min_delta: float = 0.0,
        experiment_logger: Optional[ExperimentLogger] = None,
        class_weights: Optional[Dict[str, torch.Tensor]] = None,
        backbone_lr_scale: Optional[float] = None,
        resume_from_epoch: int = 0,
        resume_checkpoint_path: Optional[str] = None,
        scheduler: str = 'plateau',
        num_epochs: int = 30,
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
        # Early stopping: stop if the monitored metric doesn't improve for this
        # many consecutive epochs. Metric is 'val_loss' (lower is better) or
        # 'accuracy' (overall_accuracy, higher is better).
        self.early_stopping_patience = early_stopping_patience
        self.early_stop_metric = early_stop_metric
        self.early_stop_min_delta = float(early_stop_min_delta)
        self._epochs_without_improvement = 0
        self.experiment_logger = experiment_logger
        self.grad_accum_steps = max(1, int(grad_accum_steps))
        self.weight_decay = weight_decay
        self.resume_from_epoch = resume_from_epoch
        
        # Optimizer and loss
        # If backbone_lr_scale is set, use differential learning rates:
        # backbone gets lr * backbone_lr_scale (slower), heads get lr (faster).
        # This prevents the backbone from shifting representations too fast
        # when Phase 2 new heads are still adapting.
        if backbone_lr_scale is not None:
            backbone_lr = learning_rate * backbone_lr_scale
            head_params = list(model.style_group_fc.parameters()) + list(model.task_heads.parameters())
            if model.paired_fusion is not None:
                head_params += list(model.paired_fusion.parameters())
            self.optimizer = optim.AdamW(
                [
                    {"params": model.backbone.parameters(), "lr": backbone_lr},
                    {"params": head_params, "lr": learning_rate},
                ],
                weight_decay=weight_decay,
            )
            logger.info(
                f"Differential LR: backbone={backbone_lr:.2e}  "
                f"(scale={backbone_lr_scale}x),  heads={learning_rate:.2e}"
            )
        else:
            self.optimizer = optim.AdamW(
                model.parameters(),
                lr=learning_rate,
                weight_decay=weight_decay,
            )
        self.criterion = MultiTaskLoss(
            active_phase=model.active_phase,
            class_weights=class_weights,
        ).to(device)
        
        # Learning rate scheduler
        self._scheduler_type = scheduler
        if scheduler == 'cosine':
            self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer,
                T_max=num_epochs,
                eta_min=learning_rate * 0.01,
            )
            logger.info(f"Scheduler: CosineAnnealingLR (T_max={num_epochs}, eta_min={learning_rate * 0.01:.2e})")
        else:
            self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
                self.optimizer,
                mode='min',
                factor=0.5,
                patience=3,
            )
            logger.info("Scheduler: ReduceLROnPlateau (factor=0.5, patience=3)")
        
        # Tracking — pre-populated when resuming from a crashed run.
        self.best_val_loss = float('inf')
        self.best_overall_acc = float('-inf')
        # Reference value for the early-stopping metric (separate from the
        # checkpoint bests so min_delta can gate the patience counter).
        self._best_early_stop_value = (
            float('-inf') if self.early_stop_metric == 'accuracy' else float('inf')
        )
        self.training_history: list = []
        if resume_from_epoch > 0:
            history_path = self.output_dir / 'training_history.json'
            if history_path.exists():
                with open(history_path) as _f:
                    self.training_history = json.load(_f)
                original_history_len = len(self.training_history)
                self.training_history = [
                    rec for rec in self.training_history
                    if int(rec.get('epoch', 0)) <= resume_from_epoch
                ]
                if len(self.training_history) != original_history_len:
                    self._save_training_history()
                    logger.info(
                        f"Trimmed training history from {original_history_len} to "
                        f"{len(self.training_history)} records for resume"
                    )
                # Restore best-so-far so early-stopping and checkpoint logic work correctly.
                for _rec in self.training_history:
                    _loss = _rec.get('val_losses', {}).get('total', float('inf'))
                    _acc  = _rec.get('val_metrics', {}).get('overall_accuracy', float('-inf'))
                    if _loss < self.best_val_loss:
                        self.best_val_loss = _loss
                    if _acc > self.best_overall_acc:
                        self.best_overall_acc = _acc
                self._best_early_stop_value = (
                    self.best_overall_acc if self.early_stop_metric == 'accuracy'
                    else self.best_val_loss
                )
                logger.info(
                    f"Resuming from epoch {resume_from_epoch}: "
                    f"loaded {len(self.training_history)} history records, "
                    f"best_loss={self.best_val_loss:.4f}, best_acc={self.best_overall_acc:.4f}"
                )

        # Restore optimizer + scheduler state for true continuity when resuming.
        # Only done when a same-phase checkpoint is provided (not cross-phase warm-starts).
        if resume_from_epoch > 0 and resume_checkpoint_path is not None:
            _ckpt_path = Path(resume_checkpoint_path)
            if _ckpt_path.exists():
                _ckpt = torch.load(_ckpt_path, map_location="cpu")
                if "optimizer_state_dict" in _ckpt:
                    self.optimizer.load_state_dict(_ckpt["optimizer_state_dict"])
                    # Move optimizer tensors to the training device.
                    for _state in self.optimizer.state.values():
                        for _k, _v in _state.items():
                            if isinstance(_v, torch.Tensor):
                                _state[_k] = _v.to(device)
                    logger.info(f"Restored optimizer state from {_ckpt_path.name}")
                if "scheduler_state_dict" in _ckpt:
                    self.scheduler.load_state_dict(_ckpt["scheduler_state_dict"])
                    logger.info(f"Restored scheduler state from {_ckpt_path.name}")
    
    def train_epoch(self, epoch: int) -> Dict[str, float]:
        """Train for one epoch"""
        self.model.train()
        
        epoch_losses = {}
        total_samples = 0
        
        max_train_batches = (
            min(len(self.train_loader), self.max_batches)
            if self.max_batches is not None
            else len(self.train_loader)
        )

        pbar = tqdm(self.train_loader, desc=f"Epoch {epoch} [Train]")
        self.optimizer.zero_grad(set_to_none=True)
        for batch_idx, (images, targets) in enumerate(pbar):
            if self.max_batches is not None and batch_idx >= self.max_batches:
                break
            images = _move_images_to_device(images, self.device)
            targets = {k: v.to(self.device) for k, v in targets.items()}

            # Forward pass
            predictions = self.model(images)
            
            # Calculate losses
            losses = self.criterion(predictions, targets)
            total_loss = losses['total']
            
            # Backward pass
            (total_loss / self.grad_accum_steps).backward()

            # Step optimizer after gradient accumulation window (or at epoch end)
            should_step = (
                ((batch_idx + 1) % self.grad_accum_steps == 0)
                or ((batch_idx + 1) == max_train_batches)
            )
            if should_step:
                # Gradient clipping for stability
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                self.optimizer.step()
                self.optimizer.zero_grad(set_to_none=True)
            
            # Accumulate losses
            batch_size = _image_batch_size(images)
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
                images  = _move_images_to_device(images, self.device)
                targets = {k: v.to(self.device) for k, v in targets.items()}

                predictions = self.model(images)
                losses      = self.criterion(predictions, targets)

                batch_size = _image_batch_size(images)
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
        if self.resume_from_epoch > 0:
            logger.info(f"Skipping epochs 1-{self.resume_from_epoch} (already complete)")

        for epoch in range(1, num_epochs + 1):
            if epoch <= self.resume_from_epoch:
                continue
            train_losses = self.train_epoch(epoch)
            val_losses, val_metrics = self.validate(epoch)

            if self._scheduler_type == 'cosine':
                self.scheduler.step()
            else:
                self.scheduler.step(val_losses['total'])
            self._log_epoch_results(epoch, train_losses, val_losses, val_metrics)
            self._save_training_history()
            if self.experiment_logger is not None:
                self.experiment_logger.log_epoch(epoch, train_losses, val_losses, val_metrics)

            overall_acc = float(val_metrics.get('overall_accuracy', 0.0))

            # Checkpoint saving: both bests are always tracked, independent of
            # which metric drives early stopping.
            if val_losses['total'] < self.best_val_loss:
                self.best_val_loss = val_losses['total']
                self._save_checkpoint(epoch, val_losses, val_metrics, is_best=True)
                logger.info(f"✓ New best-loss model saved (val_loss: {self.best_val_loss:.4f})")
                if self.experiment_logger is not None:
                    _best_ckpt = str(
                        self.output_dir / f"best_model_by_loss_phase{self.model.active_phase}.pth"
                    )
                    self.experiment_logger.log_best_checkpoint(
                        epoch, val_losses, val_metrics, _best_ckpt
                    )
            if overall_acc > self.best_overall_acc:
                self.best_overall_acc = overall_acc
                self._save_checkpoint(
                    epoch,
                    val_losses,
                    val_metrics,
                    is_best=False,
                    best_by_acc=True,
                )
                logger.info(
                    f"✓ New best-accuracy model saved "
                    f"(overall_acc: {self.best_overall_acc:.4f})"
                )

            # Early-stopping bookkeeping on the selected metric (min_delta gated).
            if self.early_stop_metric == 'accuracy':
                current_metric = overall_acc
                improved = current_metric > self._best_early_stop_value + self.early_stop_min_delta
            else:  # 'val_loss'
                current_metric = val_losses['total']
                improved = current_metric < self._best_early_stop_value - self.early_stop_min_delta
            if improved:
                self._best_early_stop_value = current_metric
                self._epochs_without_improvement = 0
            else:
                self._epochs_without_improvement += 1

            if epoch % 5 == 0:
                self._save_checkpoint(epoch, val_losses, val_metrics, is_best=False)

            if (
                self.early_stopping_patience is not None
                and self._epochs_without_improvement >= self.early_stopping_patience
            ):
                if self.early_stop_metric == 'accuracy':
                    _best_label = f"val accuracy: {self.best_overall_acc:.4f}"
                else:
                    _best_label = f"val_loss: {self.best_val_loss:.4f}"
                logger.info(
                    f"Early stopping triggered: no {self.early_stop_metric} improvement "
                    f"(min_delta={self.early_stop_min_delta}) for "
                    f"{self.early_stopping_patience} consecutive epochs. Best {_best_label}."
                )
                break

            # Free cached MPS memory between epochs to prevent fragmentation
            # stalling on Apple Silicon (no-op on CUDA/CPU).
            if self.device == "mps":
                torch.mps.empty_cache()
    
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
        best_by_acc: bool = False,
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
            'best_overall_acc': self.best_overall_acc,
            'active_phase': self.model.active_phase,
            'num_classes': dict(self.model._num_classes_override),
        }
        
        # Save best model
        if is_best:
            path = self.output_dir / f'best_model_by_loss_phase{self.model.active_phase}.pth'
            self._atomic_torch_save(checkpoint, path)

        if best_by_acc:
            path = self.output_dir / f'best_model_phase{self.model.active_phase}.pth'
            self._atomic_torch_save(checkpoint, path)
        
        # Save the latest epoch checkpoint before removing old ones. This keeps the
        # previous valid checkpoint available if the write fails partway through.
        path = self.output_dir / f'checkpoint_epoch{epoch}.pth'
        self._atomic_torch_save(checkpoint, path)
        self._cleanup_epoch_checkpoints(current_epoch=epoch)
        
        # Save training history
        self._save_training_history()

    def _atomic_torch_save(self, obj: Dict[str, Any], path: Path) -> None:
        """Write a torch checkpoint without replacing a good file on failure."""
        tmp_path = path.with_name(f".{path.name}.tmp")
        try:
            torch.save(obj, tmp_path)
            tmp_path.replace(path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def _cleanup_epoch_checkpoints(self, current_epoch: int) -> None:
        """Keep only the latest successful epoch checkpoint for this run."""
        current_path = self.output_dir / f'checkpoint_epoch{current_epoch}.pth'
        for checkpoint_path in self.output_dir.glob('checkpoint_epoch*.pth'):
            if checkpoint_path != current_path:
                checkpoint_path.unlink()

    def _save_training_history(self) -> None:
        """Persist training history to disk (atomic write to avoid partial reads)."""
        history_path = self.output_dir / 'training_history.json'
        tmp_path = history_path.with_suffix('.json.tmp')
        with open(tmp_path, 'w') as f:
            json.dump(self.training_history, f, indent=2)
        tmp_path.replace(history_path)


# ── Phase metadata ───────────────────────────────────────────────────────────

_PHASE_NAMES: Dict[int, str] = {
    1: "EASY VISUAL FEATURES (stories, roof type, cladding)",
    2: "ARCHITECTURAL CLASSIFICATION (+ style, building form)",
    3: "FINE-GRAINED FEATURES",
    4: "ALTERATION DETECTION",
}

def _num_classes_for_phase(num_classes: Dict[str, int], phase: int) -> Dict[str, int]:
    allowed: Dict[str, Dict[str, Any]] = {}
    if phase >= 1:
        allowed.update(TaskConfig.EASY_TASKS)
    if phase >= 2:
        allowed.update(TaskConfig.MEDIUM_TASKS)
    if phase >= 3:
        allowed.update(TaskConfig.HARD_TASKS)
    if phase >= 4:
        allowed.update(TaskConfig.VERY_HARD_TASKS)
    return {task: count for task, count in num_classes.items() if task in allowed}


# ── DataLoader factory ────────────────────────────────────────────────────────

def build_dataloaders(
    csv_path: str,
    model_config: ModelConfig,
    batch_size: int = 32,
    num_workers: int = 4,
    prefetch_factor: int = 2,
    cropped_root: Optional[str] = None,
    paired_views: bool = False,
    include_phase3_labels: bool = False,
    phase3_labels: Optional[List[str]] = None,
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
        batch_size:      Samples per GPU batch.
        num_workers:     DataLoader worker processes.
        prefetch_factor: Batches to prefetch per worker.
        include_phase3_labels: Load the nine Phase 3 label-definition fields.
        phase3_labels: Optional subset of Phase 3 labels to load.

    Returns:
        (train_loader, val_loader, test_loader, num_classes, class_weights)
        where num_classes is {task_name: int} and class_weights is
        {task_name: FloatTensor[n_classes]}, both derived from the training split.
    """
    train_ds, val_ds, test_ds = make_splits(
        csv_path=csv_path,
        model_config=model_config,
        cropped_root=cropped_root,
        paired_views=paired_views,
        include_phase3_labels=include_phase3_labels,
        phase3_labels=phase3_labels,
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
    persistent = num_workers > 0
    pf = prefetch_factor if num_workers > 0 else None

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=pin,
        drop_last=True,
        persistent_workers=persistent,
        prefetch_factor=pf,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin,
        persistent_workers=persistent,
        prefetch_factor=pf,
    )
    test_loader = DataLoader(
        test_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin,
        persistent_workers=persistent,
        prefetch_factor=pf,
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
    weight_decay: float = 0.01,
    grad_accum_steps: int = 1,
    output_dir: Optional[str] = None,
    num_workers: int = 4,
    prefetch_factor: int = 4,
    max_batches: Optional[int] = None,
    early_stopping_patience: Optional[int] = None,
    early_stop_metric: str = 'val_loss',
    early_stop_min_delta: float = 0.0,
    run_name: Optional[str] = None,
    dataset_version: str = "",
    model_config_path: str = "",
    initial_checkpoint: Optional[str] = None,
    freeze_phase1_heads: bool = False,
    freeze_backbone: bool = False,
    cropped_root: Optional[str] = None,
    paired_views: bool = False,
    paired_fusion_mode: str = 'concat_mlp',
    paired_gate_init: str = 'crop_prior',
    paired_gate_overrides: str = '',
    paired_residual_scales: str = '',
    paired_crop_bypass_tasks: str = '',
    backbone_lr_scale: Optional[float] = None,
    force_overwrite: bool = False,
    resume_from_epoch: int = 0,
    scheduler: str = 'plateau',
    phase3_labels: str = '',
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
        f"CSV: {csv_path} | Phases: {start_phase}\u2013{end_phase} | "
        f"weight_decay: {weight_decay} | grad_accum_steps: {grad_accum_steps} | "
        f"paired_views: {paired_views} | paired_fusion: {paired_fusion_mode}"
    )
    gate_overrides = _parse_task_float_map(paired_gate_overrides)
    residual_scales = _parse_task_float_map(paired_residual_scales)
    crop_bypass_tasks = _parse_task_list(paired_crop_bypass_tasks)
    phase3_label_list = _parse_task_list(phase3_labels)

    # Build loaders once — image size and norm stats come from model_config.
    train_loader, val_loader, _, num_classes, class_weights = build_dataloaders(
        csv_path=csv_path,
        model_config=model_config,
        batch_size=batch_size,
        num_workers=num_workers,
        prefetch_factor=prefetch_factor,
        cropped_root=cropped_root,
        paired_views=paired_views,
        include_phase3_labels=end_phase >= 3,
        phase3_labels=phase3_label_list or None,
    )

    # Build a RunConfig to capture all parameters that define this run.
    run_cfg = RunConfig(
        csv_path=csv_path,
        dataset_version=dataset_version,
        backbone=model_config.backbone,
        model_config_path=model_config_path or "config/models/resnet50.json",
        start_phase=start_phase,
        end_phase=end_phase,
        phase3_labels=phase3_labels,
        epochs=epochs_per_phase,
        batch_size=batch_size,
        lr=lr,
        weight_decay=weight_decay,
        grad_accum_steps=grad_accum_steps,
        num_workers=num_workers,
        prefetch_factor=prefetch_factor,
        early_stopping_patience=early_stopping_patience,
        early_stop_metric=early_stop_metric,
        early_stop_min_delta=early_stop_min_delta,
        load_checkpoint=initial_checkpoint,
        freeze_phase1_heads=freeze_phase1_heads,
        freeze_backbone=freeze_backbone,
        backbone_lr_scale=backbone_lr_scale,
        scheduler=scheduler,
        cropped_root=cropped_root,
        paired_views=paired_views,
        paired_fusion_mode=paired_fusion_mode,
        paired_gate_init=paired_gate_init,
        paired_gate_overrides=paired_gate_overrides,
        paired_residual_scales=paired_residual_scales,
        paired_crop_bypass_tasks=paired_crop_bypass_tasks,
        run_name=run_name or "",
    )
    # Derive output dir from the auto-slug if not explicitly provided.
    if output_dir is None:
        output_dir = f"runs/{run_cfg.run_name}"
    run_cfg.output_dir = output_dir
    logger.info(f"Run: {run_cfg.run_name}  ->  {output_dir}")

    # Allow caller to warm-start from an existing checkpoint (e.g. Phase 1 best)
    # without having to re-run earlier phases in the same process.
    prev_checkpoint: Optional[str] = initial_checkpoint

    for phase in range(start_phase, end_phase + 1):
        print("\n" + "=" * 60)
        print(f"PHASE {phase}: {_PHASE_NAMES.get(phase, f'Phase {phase}')}")
        print("=" * 60)

        phase_out = Path(output_dir) / f"phase{phase}"

        # Guard: refuse to overwrite an existing run unless explicitly requested
        # or we are resuming a crashed run.
        resuming = resume_from_epoch > 0 and (phase_out / "training_history.json").exists()
        if not force_overwrite and not resuming and (phase_out / "training_history.json").exists():
            raise FileExistsError(
                f"Output directory already contains a completed run:\n"
                f"  {phase_out / 'training_history.json'}\n"
                f"Use --force-overwrite to overwrite it."
            )

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
            phase3_labels=run_cfg.phase3_labels,
            epochs=run_cfg.epochs,
            batch_size=run_cfg.batch_size,
            lr=run_cfg.lr,
            weight_decay=run_cfg.weight_decay,
            grad_accum_steps=run_cfg.grad_accum_steps,
            num_workers=run_cfg.num_workers,
            prefetch_factor=run_cfg.prefetch_factor,
            early_stopping_patience=run_cfg.early_stopping_patience,
            early_stop_metric=run_cfg.early_stop_metric,
            early_stop_min_delta=run_cfg.early_stop_min_delta,
            load_checkpoint=run_cfg.load_checkpoint,
            freeze_phase1_heads=run_cfg.freeze_phase1_heads,
            freeze_backbone=run_cfg.freeze_backbone,
            backbone_lr_scale=run_cfg.backbone_lr_scale,
            scheduler=run_cfg.scheduler,
            cropped_root=run_cfg.cropped_root,
            paired_views=run_cfg.paired_views,
            paired_fusion_mode=run_cfg.paired_fusion_mode,
            paired_gate_init=run_cfg.paired_gate_init,
            paired_gate_overrides=run_cfg.paired_gate_overrides,
            paired_residual_scales=run_cfg.paired_residual_scales,
            paired_crop_bypass_tasks=run_cfg.paired_crop_bypass_tasks,
            run_name=_phase_run_name,
            output_dir=str(phase_out),
        )
        phase_cfg.save(phase_out)

        model = MultiTaskArchitecturalClassifier(
            backbone=model_config.backbone,
            weights="DEFAULT",
            active_phase=phase,
            freeze_backbone=run_cfg.freeze_backbone,
            num_classes=_num_classes_for_phase(num_classes, phase),
            paired_views=run_cfg.paired_views,
            paired_fusion_mode=run_cfg.paired_fusion_mode,
            paired_gate_init=run_cfg.paired_gate_init,
            paired_gate_overrides=gate_overrides,
            paired_residual_scales=residual_scales,
            paired_crop_bypass_tasks=crop_bypass_tasks,
        )

        # Warm-start: transfer backbone + earlier task heads from previous phase
        # (or from an externally supplied checkpoint via --load-checkpoint).
        if prev_checkpoint is not None and Path(prev_checkpoint).exists():
            ckpt = torch.load(prev_checkpoint, map_location="cpu")
            state = normalize_paired_fusion_state_dict(ckpt["model_state_dict"])
            missing, unexpected = model.load_state_dict(
                state, strict=False
            )
            logger.info(
                f"Phase {phase} warm-start \u2190 {prev_checkpoint} "
                f"({len(missing)} missing keys, {len(unexpected)} unexpected)"
            )

            # --freeze-phase1-heads: on the first phase being trained (typically
            # Phase 2 Stage 1), freeze all Phase 1 task heads so only the new
            # heads + backbone can update.  Phase 1 head weights are preserved
            # from the loaded checkpoint.
            if freeze_phase1_heads and phase == start_phase:
                # Freeze the heads that were present in the loaded checkpoint
                # (i.e. everything trained in the prior run), not just the static
                # EASY_TASKS set.  This correctly handles runs that started with
                # a full TRAINING_LABEL_COLS task list (which includes
                # architectural_style and alteration_level — absent from EASY_TASKS).
                phase1_names = set(ckpt.get("num_classes", {}).keys())
                frozen_count = 0
                for task_name, head_module in model.task_heads.items():
                    if task_name in phase1_names:
                        for p in head_module.parameters():
                            p.requires_grad = False
                        frozen_count += 1
                logger.info(
                    f"freeze_phase1_heads: froze {frozen_count} Phase 1 task heads "
                    f"({sorted(phase1_names & set(model.task_heads.keys()))})"
                )

        with ExperimentLogger(phase_cfg, experiment_name="arepas") as exp_logger:
            trainer = MultiTaskTrainer(
                model=model,
                train_loader=train_loader,
                val_loader=val_loader,
                device=device,
                learning_rate=lr,
                weight_decay=weight_decay,
                grad_accum_steps=grad_accum_steps,
                output_dir=str(phase_out),
                max_batches=max_batches,
                early_stopping_patience=early_stopping_patience,
                early_stop_metric=run_cfg.early_stop_metric,
                early_stop_min_delta=run_cfg.early_stop_min_delta,
                experiment_logger=exp_logger,
                class_weights=class_weights,
                backbone_lr_scale=backbone_lr_scale,
                resume_from_epoch=resume_from_epoch,
                resume_checkpoint_path=str(prev_checkpoint) if resuming else None,
                scheduler=scheduler,
                num_epochs=epochs_per_phase,
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
        "--phase3-labels",
        default="",
        help=(
            "Comma-separated Phase 3 label subset to train when phase 3 is active. "
            "Blank means all configured Phase 3 labels. Example: "
            "wall_features,landscape_features,window,entrance,associated_buildings,building_category,roof_materials"
        ),
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
        "--weight-decay", type=float, default=0.01,
        help="AdamW weight decay (regularization strength).",
    )
    parser.add_argument(
        "--grad-accum-steps", type=int, default=1,
        help=(
            "Number of mini-batches to accumulate before optimizer.step(). "
            "Effective batch size = batch_size * grad_accum_steps."
        ),
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
        "--prefetch-factor", type=int, default=4,
        help="Batches to prefetch per worker (persistent_workers always enabled when num_workers>0).",
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
            "Stop training if the monitored metric (see --early-stop-metric) does "
            "not improve for this many consecutive epochs. Omit to disable early stopping."
        ),
    )
    parser.add_argument(
        "--early-stop-metric", choices=["val_loss", "accuracy"], default="accuracy",
        help=(
            "Metric that drives early stopping and the patience counter. "
            "'accuracy' monitors overall_accuracy (higher is better); 'val_loss' "
            "monitors total validation loss (lower is better). Default: accuracy — "
            "val_loss can rise from overconfidence while accuracy still improves."
        ),
    )
    parser.add_argument(
        "--early-stop-min-delta", type=float, default=0.001,
        help=(
            "Minimum change in the monitored metric to count as an improvement. "
            "Guards against the patience counter resetting on trivial noise."
        ),
    )
    parser.add_argument(
        "--load-checkpoint", default=None,
        help=(
            "Path to an existing .pth checkpoint to warm-start from before the "
            "first phase. Useful for continuing training from a previous phase "
            "(e.g. load Phase 1 best checkpoint when running --start-phase 2). "
            "Weights are loaded non-strictly — new heads initialise from scratch."
        ),
    )
    parser.add_argument(
        "--freeze-phase1-heads", action="store_true", default=False,
        help=(
            "Freeze all Phase 1 task heads after loading --load-checkpoint. "
            "Use for Stage 1 of two-stage Phase 2 training: new heads adapt to "
            "existing features without destabilising Phase 1 knowledge. "
            "Ignored if --load-checkpoint is not provided."
        ),
    )
    parser.add_argument(
        "--freeze-backbone", action="store_true", default=False,
        help=(
            "Freeze all backbone weights for the entire training run. "
            "Only task heads are updated. Useful for testing whether phase2 "
            "plateaus are caused by backbone drift or head capacity limits."
        ),
    )
    parser.add_argument(
        "--backbone-lr-scale", type=float, default=None,
        help=(
            "When set, uses differential learning rates: backbone LR = lr * backbone_lr_scale, "
            "task heads LR = lr.  Recommended value: 0.1 to 0.33.  "
            "Prevents the backbone from shifting representations too fast when "
            "Phase 2 new heads are still adapting, without freezing Phase 1 heads."
        ),
    )
    parser.add_argument(
        "--cropped-root", default=None,
        help=(
            "Root directory of pre-cropped images produced by scripts/crop_dataset.py. "
            "When set, the dataset loader prefers <cropped-root>/<stem>_crop.jpg over "
            "the original image path.  Omit to train on original images."
        ),
    )
    parser.add_argument(
        "--paired-views", action="store_true", default=False,
        help=(
            "Train on paired full + cropped images. Requires --cropped-root for "
            "true paired views; missing crops fall back to the full image."
        ),
    )
    parser.add_argument(
        "--paired-fusion",
        default="concat_mlp",
        choices=["concat_mlp", "crop_residual", "task_gated_residual"],
        help=(
            "Fusion module for --paired-views. concat_mlp preserves paired-v1; "
            "crop_residual starts as crop passthrough; task_gated_residual gives "
            "each task a crop/full gate."
        ),
    )
    parser.add_argument(
        "--paired-gate-init",
        default="crop_prior",
        choices=["crop_prior", "neutral"],
        help="Initial task gate bias for task_gated_residual paired fusion.",
    )
    parser.add_argument(
        "--paired-gate-overrides",
        default="",
        help=(
            "Comma-separated task=probability overrides for task_gated_residual initial gates, "
            "for example roof_type=0.03,stories=0.01."
        ),
    )
    parser.add_argument(
        "--paired-residual-scales",
        default="",
        help=(
            "Comma-separated task=scale initial full-residual multipliers for task_gated_residual, "
            "for example roof_type=0.5,stories=0.25. Scales are trainable."
        ),
    )
    parser.add_argument(
        "--paired-crop-bypass-tasks",
        default="",
        help=(
            "Comma-separated task names that should use crop features only in task_gated_residual, "
            "for example stories or stories,roof_type."
        ),
    )
    parser.add_argument(
        "--scheduler", default="plateau", choices=["plateau", "cosine"],
        help=(
            "LR scheduler. 'plateau' (default): ReduceLROnPlateau (factor=0.5, patience=3) — "
            "halves LR when val_loss stalls; can cause premature learning arrest. "
            "'cosine': CosineAnnealingLR — decays smoothly from lr to lr*0.01 over all epochs; "
            "keeps the model learning throughout the full run. Recommended for unfrozen phase2."
        ),
    )
    parser.add_argument(
        "--force-overwrite", action="store_true", default=False,
        help=(
            "Allow writing into an output directory that already contains a "
            "training_history.json. Without this flag the script aborts to "
            "prevent accidentally destroying a previous run."
        ),
    )
    parser.add_argument(
        "--resume-from", type=int, default=0, metavar="EPOCH",
        help=(
            "Resume a crashed run starting after this epoch. "
            "The checkpoint at <output-dir>/phase<N>/checkpoint_epoch<EPOCH>.pth "
            "is loaded and existing training_history.json is preserved and appended to. "
            "Example: --resume-from 12 (resumes from epoch 13 onward)."
        ),
    )
    args = parser.parse_args()

    cfg = ModelConfig.from_json(args.model_config)

    # When resuming, auto-resolve the checkpoint for the crashed epoch unless
    # the caller already supplied --load-checkpoint.
    initial_checkpoint = args.load_checkpoint
    if args.resume_from > 0 and initial_checkpoint is None and args.output_dir:
        # Try the per-epoch checkpoint first, fall back to best_model.
        phase = args.start_phase
        candidate = Path(args.output_dir) / f"phase{phase}" / f"checkpoint_epoch{args.resume_from}.pth"
        fallback  = Path(args.output_dir) / f"phase{phase}" / f"best_model_phase{phase}.pth"
        if candidate.exists() and candidate.stat().st_size > 300_000_000:
            initial_checkpoint = str(candidate)
            logger.info(f"--resume-from: using checkpoint {candidate}")
        elif fallback.exists():
            initial_checkpoint = str(fallback)
            logger.info(f"--resume-from: epoch checkpoint missing/truncated, using {fallback}")
        else:
            raise FileNotFoundError(
                f"Cannot resume: no usable checkpoint found at\n"
                f"  {candidate}\n  {fallback}"
            )

    progressive_training_pipeline(
        csv_path=args.csv,
        model_config=cfg,
        start_phase=args.start_phase,
        end_phase=args.end_phase,
        epochs_per_phase=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        weight_decay=args.weight_decay,
        grad_accum_steps=args.grad_accum_steps,
        output_dir=args.output_dir,
        num_workers=args.num_workers,
        prefetch_factor=args.prefetch_factor,
        max_batches=args.max_batches,
        early_stopping_patience=args.early_stopping_patience,
        early_stop_metric=args.early_stop_metric,
        early_stop_min_delta=args.early_stop_min_delta,
        run_name=args.run_name,
        dataset_version=args.dataset_version,
        model_config_path=args.model_config,
        initial_checkpoint=initial_checkpoint,
        freeze_phase1_heads=args.freeze_phase1_heads,
        freeze_backbone=args.freeze_backbone,
        cropped_root=args.cropped_root,
        paired_views=args.paired_views,
        paired_fusion_mode=args.paired_fusion,
        paired_gate_init=args.paired_gate_init,
        paired_gate_overrides=args.paired_gate_overrides,
        paired_residual_scales=args.paired_residual_scales,
        paired_crop_bypass_tasks=args.paired_crop_bypass_tasks,
        backbone_lr_scale=args.backbone_lr_scale,
        force_overwrite=args.force_overwrite,
        resume_from_epoch=args.resume_from,
        scheduler=args.scheduler,
        phase3_labels=args.phase3_labels,
    )
