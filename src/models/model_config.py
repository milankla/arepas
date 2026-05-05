"""
ModelConfig — backbone configuration loaded from config/models/<name>.json.

Decouples model assumptions (backbone name, input resolution, normalisation
statistics) from both the dataset pipeline and the classifier definition.

File schema
───────────
    {
      "backbone":   "resnet18",          # torchvision model name (str, required)
      "image_size": 224,                 # input spatial resolution (int > 0, required)
      "norm_mean":  [0.485, 0.456, 0.406],  # 3-element list (required)
      "norm_std":   [0.229, 0.224, 0.225]   # 3-element list (required)
    }

Bundled configs  (config/models/)
──────────────────────────────────
    resnet18.json        ResNet-18,  ImageNet stats
    resnet50.json        ResNet-50,  ImageNet stats
    efficientnet_b0.json EfficientNet-B0, ImageNet stats
    clip_vit_b32.json    CLIP ViT-B/32,   CLIP stats

Usage
─────
    from src.models.model_config import ModelConfig

    cfg = ModelConfig.from_json("config/models/resnet18.json")
    print(cfg.backbone)     # "resnet18"
    print(cfg.image_size)   # 224
    print(cfg.norm_mean)    # (0.485, 0.456, 0.406)

    # Pass directly to make_splits — overrides image_size / norm_mean / norm_std
    train, val, test = make_splits(csv_path="data/image_label_mapping_phase1.csv",
                                   model_config=cfg)

    # Pass directly to MultiTaskArchitecturalClassifier
    model = MultiTaskArchitecturalClassifier(model_config=cfg)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple


# ── Known backbones ──────────────────────────────────────────────────────────
# Maps the JSON "backbone" string → torchvision constructor name (where applicable).
# clip_* backbones are handled separately (not in torchvision).
KNOWN_BACKBONES: frozenset[str] = frozenset({
    "resnet18",
    "resnet50",
    "efficientnet_b0",
    "efficientnet_b4",
    "efficientnet_b5",
    "mobilenet_v3_small",
    "mobilenet_v3_large",
    "vit_b_16",
    "vit_b_32",
    "clip_vit_b32",
    "clip_vit_l14",
})


# ── ModelConfig dataclass ────────────────────────────────────────────────────

@dataclass(frozen=True)
class ModelConfig:
    """
    Immutable configuration for a single backbone choice.

    Attributes:
        backbone:   torchvision / HuggingFace model identifier string.
        image_size: Spatial resolution (H == W) expected by the backbone.
        norm_mean:  Per-channel normalisation mean (length-3 tuple).
        norm_std:   Per-channel normalisation std  (length-3 tuple).
        source:     Path the config was loaded from (None if built in-code).
    """

    backbone:   str
    image_size: int
    norm_mean:  Tuple[float, float, float]
    norm_std:   Tuple[float, float, float]
    source:     str | None = None

    # ── Factory ───────────────────────────────────────────────────────────

    @classmethod
    def from_json(cls, path: str | Path) -> "ModelConfig":
        """Load and validate a ModelConfig from a JSON file.

        Args:
            path: Path to a config/models/*.json file.

        Returns:
            A validated, frozen ModelConfig instance.

        Raises:
            FileNotFoundError: if the JSON file does not exist.
            ValueError:        if any required field is missing or invalid.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(
                f"Model config not found: {p}\n"
                f"Available configs: {', '.join(sorted(str(x.name) for x in p.parent.glob('*.json')))}"
                if p.parent.exists() else
                f"Model config not found: {p}"
            )

        with p.open() as f:
            raw = json.load(f)

        return cls._validate_and_build(raw, source=str(p))

    @classmethod
    def from_dict(cls, d: dict, source: str | None = None) -> "ModelConfig":
        """Build a ModelConfig from a plain dict (e.g. already-loaded JSON)."""
        return cls._validate_and_build(d, source=source)

    # ── Internal helpers ──────────────────────────────────────────────────

    @classmethod
    def _validate_and_build(cls, raw: dict, source: str | None) -> "ModelConfig":
        missing = [k for k in ("backbone", "image_size", "norm_mean", "norm_std") if k not in raw]
        if missing:
            raise ValueError(f"Model config missing required keys: {missing}  (source: {source})")

        backbone = str(raw["backbone"])
        if backbone not in KNOWN_BACKBONES:
            # Warn but don't hard-error — allows experimental backbones.
            import warnings
            warnings.warn(
                f"Unknown backbone '{backbone}'. Known: {sorted(KNOWN_BACKBONES)}. "
                "Proceeding — ensure the backbone is handled in MultiTaskArchitecturalClassifier.",
                stacklevel=3,
            )

        image_size = int(raw["image_size"])
        if image_size <= 0:
            raise ValueError(f"image_size must be > 0, got {image_size}")

        norm_mean = tuple(float(v) for v in raw["norm_mean"])
        norm_std  = tuple(float(v) for v in raw["norm_std"])
        if len(norm_mean) != 3:
            raise ValueError(f"norm_mean must have exactly 3 elements, got {len(norm_mean)}")
        if len(norm_std) != 3:
            raise ValueError(f"norm_std must have exactly 3 elements, got {len(norm_std)}")

        return cls(
            backbone=backbone,
            image_size=image_size,
            norm_mean=norm_mean,   # type: ignore[arg-type]
            norm_std=norm_std,     # type: ignore[arg-type]
            source=source,
        )

    # ── Convenience ───────────────────────────────────────────────────────

    def to_make_splits_kwargs(self) -> dict:
        """Return a dict that can be passed directly to make_splits() via **."""
        return {
            "image_size": self.image_size,
            "norm_mean":  self.norm_mean,
            "norm_std":   self.norm_std,
        }

    def __repr__(self) -> str:
        src = f" ← {self.source}" if self.source else ""
        return (
            f"ModelConfig(backbone={self.backbone!r}, image_size={self.image_size}, "
            f"norm_mean={self.norm_mean}, norm_std={self.norm_std}){src}"
        )


# ── CLI smoke test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    configs_dir = Path(__file__).parent.parent.parent / "config" / "models"
    jsons = sorted(configs_dir.glob("*.json"))

    if not jsons:
        print(f"No JSON files found in {configs_dir}")
        sys.exit(1)

    print(f"Loading {len(jsons)} config(s) from {configs_dir}\n")
    for p in jsons:
        cfg = ModelConfig.from_json(p)
        print(f"  {p.name:<25} {cfg}")
        kw = cfg.to_make_splits_kwargs()
        assert set(kw) == {"image_size", "norm_mean", "norm_std"}

    print("\n✅ All model configs valid")
