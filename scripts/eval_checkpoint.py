"""Re-evaluate a saved checkpoint with the current metrics."""
import argparse
import torch
from src.models.multi_task_classifier import MultiTaskArchitecturalClassifier
from src.models.metrics import compute_metrics, format_metrics_table
from src.models.train_multi_task import build_dataloaders
from src.models.model_config import ModelConfig


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--model-config", default="config/models/resnet50.json")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--phase", type=int, default=1)
    args = parser.parse_args()

    cfg = ModelConfig.from_json(args.model_config)
    _, val_loader, _, num_classes = build_dataloaders(
        csv_path=args.csv,
        model_config=cfg,
        batch_size=args.batch_size,
        num_workers=0,
    )

    model = MultiTaskArchitecturalClassifier(
        backbone=cfg.backbone,
        weights=None,
        active_phase=args.phase,
        freeze_backbone=False,
        num_classes=num_classes,
    )
    ckpt = torch.load(args.checkpoint, map_location="cpu")
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    all_preds, all_tgts = {}, {}
    with torch.no_grad():
        for images, targets in val_loader:
            preds = model(images)
            for k, v in preds.items():
                all_preds.setdefault(k, []).append(v)
            for k, v in targets.items():
                all_tgts.setdefault(k, []).append(v)

    preds_cat = {k: torch.cat(v) for k, v in all_preds.items()}
    tgts_cat  = {k: torch.cat(v) for k, v in all_tgts.items()}
    metrics = compute_metrics(model, preds_cat, tgts_cat)
    print(format_metrics_table(metrics))


if __name__ == "__main__":
    main()
