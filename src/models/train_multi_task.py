"""
Multi-Task Training Script

Progressive training strategy:
1. Phase 1 (Week 1-2): Easy tasks (stories, roof type, cladding)
2. Phase 2 (Week 3-4): Add architectural style, building form
3. Phase 3 (Week 5-6): Add fine-grained features
4. Phase 4 (Week 7-8): Add alteration detection
"""

import argparse
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from typing import Dict, Tuple, Optional
import logging
from pathlib import Path
from tqdm import tqdm
import json

from src.models.multi_task_classifier import MultiTaskArchitecturalClassifier, MultiTaskLoss
from src.models.model_config import ModelConfig
from src.loader.architectural_dataset import make_splits


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
        output_dir: str = './outputs'
    ):
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.device = device
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Optimizer and loss
        self.optimizer = optim.AdamW(
            model.parameters(),
            lr=learning_rate,
            weight_decay=0.01
        )
        self.criterion = MultiTaskLoss(active_phase=model.active_phase)
        
        # Learning rate scheduler
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=3,
            verbose=True
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
    
    def validate(self, epoch: int) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Validate model"""
        self.model.eval()
        
        epoch_losses = {}
        epoch_accuracies = {}
        total_samples = 0
        
        with torch.no_grad():
            pbar = tqdm(self.val_loader, desc=f"Epoch {epoch} [Val]")
            for images, targets in pbar:
                images = images.to(self.device)
                targets = {k: v.to(self.device) for k, v in targets.items()}
                
                # Forward pass
                predictions = self.model(images)
                
                # Calculate losses
                losses = self.criterion(predictions, targets)
                
                # Calculate accuracies
                accuracies = self._calculate_accuracies(predictions, targets)
                
                # Accumulate
                batch_size = images.size(0)
                total_samples += batch_size
                
                for loss_name, loss_value in losses.items():
                    if loss_name not in epoch_losses:
                        epoch_losses[loss_name] = 0.0
                    epoch_losses[loss_name] += loss_value.item() * batch_size
                
                for task_name, acc_value in accuracies.items():
                    if task_name not in epoch_accuracies:
                        epoch_accuracies[task_name] = 0.0
                    epoch_accuracies[task_name] += acc_value * batch_size
                
                pbar.set_postfix({'loss': losses['total'].item()})
        
        # Average
        epoch_losses = {k: v / total_samples for k, v in epoch_losses.items()}
        epoch_accuracies = {k: v / total_samples for k, v in epoch_accuracies.items()}
        
        return epoch_losses, epoch_accuracies
    
    def _calculate_accuracies(
        self,
        predictions: Dict[str, torch.Tensor],
        targets: Dict[str, torch.Tensor]
    ) -> Dict[str, float]:
        """Calculate per-task accuracy"""
        accuracies = {}
        
        for task_name in predictions.keys():
            if task_name not in targets:
                continue
            
            pred = predictions[task_name]
            target = targets[task_name]
            
            # Get task config
            config = self.model.get_task_config(task_name)
            
            if config.get('multi_label', False):
                # Multi-label accuracy (threshold at 0.5)
                pred_binary = (torch.sigmoid(pred) > 0.5).float()
                correct = (pred_binary == target).all(dim=1).sum().item()
                total = target.size(0)
                accuracies[task_name] = correct / total
            else:
                # Single-label accuracy
                pred_classes = pred.argmax(dim=1)
                correct = (pred_classes == target).sum().item()
                total = target.size(0)
                accuracies[task_name] = correct / total
        
        return accuracies
    
    def train(self, num_epochs: int):
        """
        Full training loop
        """
        logger.info(f"Starting training for {num_epochs} epochs")
        logger.info(f"Model phase: {self.model.active_phase}")
        logger.info(f"Active tasks: {list(self.model.task_heads.keys())}")
        
        for epoch in range(1, num_epochs + 1):
            # Train
            train_losses = self.train_epoch(epoch)
            
            # Validate
            val_losses, val_accuracies = self.validate(epoch)
            
            # Update scheduler
            self.scheduler.step(val_losses['total'])
            
            # Log results
            self._log_epoch_results(epoch, train_losses, val_losses, val_accuracies)
            
            # Save checkpoint if best
            if val_losses['total'] < self.best_val_loss:
                self.best_val_loss = val_losses['total']
                self._save_checkpoint(epoch, val_losses, val_accuracies, is_best=True)
                logger.info(f"✓ New best model saved (val_loss: {self.best_val_loss:.4f})")
            
            # Save regular checkpoint
            if epoch % 5 == 0:
                self._save_checkpoint(epoch, val_losses, val_accuracies, is_best=False)
    
    def _log_epoch_results(
        self,
        epoch: int,
        train_losses: Dict[str, float],
        val_losses: Dict[str, float],
        val_accuracies: Dict[str, float]
    ):
        """Log training results"""
        logger.info(f"\nEpoch {epoch} Results:")
        logger.info(f"  Train Loss: {train_losses['total']:.4f}")
        logger.info(f"  Val Loss: {val_losses['total']:.4f}")
        
        # Log per-task accuracies
        logger.info("  Task Accuracies:")
        for task_name, acc in sorted(val_accuracies.items()):
            logger.info(f"    {task_name}: {acc:.3f}")
        
        # Save to history
        self.training_history.append({
            'epoch': epoch,
            'train_losses': train_losses,
            'val_losses': val_losses,
            'val_accuracies': val_accuracies
        })
    
    def _save_checkpoint(
        self,
        epoch: int,
        val_losses: Dict[str, float],
        val_accuracies: Dict[str, float],
        is_best: bool = False
    ):
        """Save model checkpoint"""
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'val_losses': val_losses,
            'val_accuracies': val_accuracies,
            'best_val_loss': self.best_val_loss,
            'active_phase': self.model.active_phase
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
) -> Tuple[DataLoader, DataLoader, DataLoader, Dict[str, int]]:
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
        (train_loader, val_loader, test_loader, num_classes)
        where num_classes is {task_name: int} derived from the training split.
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
    return train_loader, val_loader, test_loader, train_ds.num_classes


# ── Pipeline ──────────────────────────────────────────────────────────────────

def progressive_training_pipeline(
    csv_path: str,
    model_config: ModelConfig,
    start_phase: int = 1,
    end_phase: int = 1,
    epochs_per_phase: int = 20,
    batch_size: int = 32,
    lr: float = 1e-4,
    output_dir: str = "./outputs",
    num_workers: int = 4,
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
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(
        f"Device: {device} | Backbone: {model_config.backbone} | "
        f"CSV: {csv_path} | Phases: {start_phase}\u2013{end_phase}"
    )

    # Build loaders once — image size and norm stats come from model_config.
    train_loader, val_loader, _, num_classes = build_dataloaders(
        csv_path=csv_path,
        model_config=model_config,
        batch_size=batch_size,
        num_workers=num_workers,
    )

    prev_checkpoint: Optional[str] = None

    for phase in range(start_phase, end_phase + 1):
        print("\n" + "=" * 60)
        print(f"PHASE {phase}: {_PHASE_NAMES.get(phase, f'Phase {phase}')}")
        print("=" * 60)

        phase_out = Path(output_dir) / f"phase{phase}"

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

        trainer = MultiTaskTrainer(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            device=device,
            learning_rate=lr,
            output_dir=str(phase_out),
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
        "--output-dir", default="./outputs",
        help="Root directory for checkpoints and training history.",
    )
    parser.add_argument(
        "--num-workers", type=int, default=4,
        help="DataLoader worker processes.",
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
    )
