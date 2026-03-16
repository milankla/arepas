"""
Multi-Task Training Script

Progressive training strategy:
1. Phase 1 (Week 1-2): Easy tasks (stories, roof type, cladding)
2. Phase 2 (Week 3-4): Add architectural style, building form
3. Phase 3 (Week 5-6): Add fine-grained features
4. Phase 4 (Week 7-8): Add alteration detection
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from typing import Dict, Tuple, Optional
import logging
from pathlib import Path
from tqdm import tqdm
import json

from multi_task_classifier import MultiTaskArchitecturalClassifier, MultiTaskLoss


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


def progressive_training_pipeline():
    """
    Complete progressive training pipeline
    
    Phase 1 (2 weeks): Easy tasks
    Phase 2 (2 weeks): + Architectural style
    Phase 3 (2 weeks): + Fine-grained features
    Phase 4 (2 weeks): + Alteration detection
    """
    
    # TODO: Initialize dataloaders (from your data preparation script)
    # train_loader = get_dataloader(split='train', phase=1)
    # val_loader = get_dataloader(split='val', phase=1)
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Using device: {device}")
    
    # Phase 1: Easy Tasks (Foundation)
    print("\n" + "="*60)
    print("PHASE 1: EASY VISUAL FEATURES")
    print("="*60)
    
    model_phase1 = MultiTaskArchitecturalClassifier(
        backbone='resnet50',
        weights='DEFAULT',
        active_phase=1,
        freeze_backbone=False
    )
    
    # trainer_phase1 = MultiTaskTrainer(
    #     model=model_phase1,
    #     train_loader=train_loader,
    #     val_loader=val_loader,
    #     device=device,
    #     learning_rate=1e-4,
    #     output_dir='./outputs/phase1'
    # )
    # trainer_phase1.train(num_epochs=20)
    
    # Phase 2: Add Architectural Style
    print("\n" + "="*60)
    print("PHASE 2: ARCHITECTURAL CLASSIFICATION")
    print("="*60)
    
    model_phase2 = MultiTaskArchitecturalClassifier(
        backbone='resnet50',
        weights='DEFAULT',
        active_phase=2,
        freeze_backbone=False
    )
    
    # Load Phase 1 weights (transfer learning)
    # checkpoint = torch.load('./outputs/phase1/best_model_phase1.pth')
    # Load shared backbone and Phase 1 task heads
    # model_phase2.load_state_dict(checkpoint['model_state_dict'], strict=False)
    
    # Continue training...
    
    print("\nProgressive training pipeline configured!")
    print("Next steps:")
    print("1. Prepare image-to-label mapping CSV")
    print("2. Create PyTorch Dataset class")
    print("3. Run Phase 1 training (easy tasks)")
    print("4. Evaluate Phase 1 results")
    print("5. Move to Phase 2 (architectural style)")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    progressive_training_pipeline()
