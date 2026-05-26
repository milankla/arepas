"""RunConfig — captures every parameter that defines a training run.

Serialised to ``run_config.json`` inside the output directory so that any
checkpoint is fully reproducible without digging through git logs or terminal
history.

Usage::

    cfg = RunConfig(
        csv_path="data2/image_label_mapping_phase1.csv",
        backbone="resnet50",
        ...
    )
    cfg.save(Path("runs/my_run/phase1"))

    # Later, reconstruct:
    cfg = RunConfig.load(Path("runs/my_run/phase1/run_config.json"))
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _git_commit() -> str:
    """Return current HEAD short hash, or 'unknown' if git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def _dataset_version(csv_path: str) -> str:
    """Infer a short dataset label from the CSV path (e.g. 'data2', 'data')."""
    parts = Path(csv_path).parts
    # Walk up until we find a directory that isn't a pure filename component
    for part in parts:
        if part.startswith("data"):
            return part
    return Path(csv_path).stem


@dataclass
class RunConfig:
    """All parameters that uniquely define a training run."""

    # ── Data ──────────────────────────────────────────────────────────────────
    csv_path: str
    dataset_version: str = ""           # auto-derived if blank

    # ── Model ─────────────────────────────────────────────────────────────────
    backbone: str = "resnet50"
    model_config_path: str = "config/models/resnet50.json"
    start_phase: int = 1
    end_phase: int = 1

    # ── Hyperparameters ───────────────────────────────────────────────────────
    epochs: int = 30
    batch_size: int = 32
    lr: float = 1e-4
    weight_decay: float = 0.01
    grad_accum_steps: int = 1
    num_workers: int = 2
    prefetch_factor: int = 4
    early_stopping_patience: Optional[int] = None

    # ── Warm-start / transfer learning ────────────────────────────────────────
    load_checkpoint: Optional[str] = None   # path to checkpoint loaded before phase 1
    freeze_phase1_heads: bool = False       # Stage 1 of two-stage Phase 2 training
    freeze_backbone: bool = False           # Freeze backbone entirely; only heads are updated
    backbone_lr_scale: Optional[float] = None  # backbone LR = lr * scale; None = same as heads
    scheduler: str = "plateau"              # "plateau" | "cosine"

    # ── Paired full + crop views ──────────────────────────────────────────────
    cropped_root: Optional[str] = None       # Root of precomputed crops, if used
    paired_views: bool = False               # Feed both full image and crop to model
    paired_fusion_mode: str = "concat_mlp"   # concat_mlp | crop_residual | task_gated_residual
    paired_gate_init: str = "crop_prior"     # crop_prior | neutral
    paired_gate_overrides: str = ""          # comma list, e.g. roof_type=0.03,stories=0.01
    paired_residual_scales: str = ""         # comma list, e.g. roof_type=0.5,stories=0.25
    paired_crop_bypass_tasks: str = ""       # comma list, e.g. stories,roof_type

    # ── Preprocessing decisions ───────────────────────────────────────────────
    roof_type_encoding: str = "single_label_compound"   # or "multi_label_19"
    augmentation_version: str = "v1"                    # bump when transforms change

    # ── Identity (auto-filled) ────────────────────────────────────────────────
    run_name: str = ""
    git_commit: str = field(default_factory=_git_commit)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    output_dir: str = ""

    def __post_init__(self) -> None:
        if not self.dataset_version:
            self.dataset_version = _dataset_version(self.csv_path)
        if not self.run_name:
            self.run_name = self._auto_slug()

    def _auto_slug(self) -> str:
        """Generate a human-readable run identifier from key parameters."""
        patience = f"_pat{self.early_stopping_patience}" if self.early_stopping_patience else ""
        return (
            f"{self.backbone}"
            f"_{self.dataset_version}"
            f"_ph{self.start_phase}-{self.end_phase}"
            f"_lr{self.lr:.0e}"
            f"_wd{self.weight_decay}"
            f"_bs{self.batch_size}"
            f"_ep{self.epochs}"
            f"{patience}"
            f"_{self.git_commit}"
        )

    # ── Serialisation ─────────────────────────────────────────────────────────

    def save(self, output_dir: Path) -> Path:
        """Write run_config.json into *output_dir* (creates dir if needed)."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "run_config.json"
        with open(path, "w") as fh:
            json.dump(asdict(self), fh, indent=2)
        return path

    @classmethod
    def load(cls, path: Path | str) -> "RunConfig":
        """Reconstruct a RunConfig from a saved run_config.json.

        Forward-compatible: unknown keys from future versions are ignored;
        missing keys from older configs use dataclass defaults.
        """
        with open(path) as fh:
            data = json.load(fh)
        # Drop keys not in the dataclass (future-proofing) and fill missing
        # keys with defaults (backward-compat with old run_config.json files).
        import dataclasses
        known = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def as_flat_dict(self) -> dict:
        """Return a flat str→str/float/int dict suitable for mlflow.log_params."""
        d = asdict(self)
        return {k: (str(v) if v is None else v) for k, v in d.items()}
