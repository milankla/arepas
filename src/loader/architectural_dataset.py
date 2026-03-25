"""
ArchitecturalDataset — dataset-agnostic PyTorch Dataset for multi-task
architectural classification.

Works with any image-label mapping CSV produced by
scripts/build_phase1_label_mapping.py — covering both ./data and ./data2
datasets.  Pass the appropriate csv_path to make_splits() to switch datasets.

  • Label encoders fitted from the actual classes present in the CSV
    (no hardcoded class lists — works as data grows or changes)
  • Building-level stratified 70 / 15 / 15 split on architectural_style
    (all images of one building land in the same partition — no leakage)
  • Separate torchvision transforms for train (augmented) vs eval (clean)
  • Configurable input resolution via image_size parameter
  • Graceful handling of missing images  (warned at __getitem__, returns zeros)

Usage
─────
    from src.loader.architectural_dataset import ArchitecturalDataset, make_splits

    # data/ dataset (default)
    train_ds, val_ds, test_ds = make_splits()

    # data2/ dataset
    train_ds, val_ds, test_ds = make_splits(
        csv_path="data2/image_label_mapping_phase1.csv",
    )

    train_loader = DataLoader(train_ds, batch_size=32, shuffle=True)
    for images, labels in train_loader:
        # images    : FloatTensor [B, 3, 224, 224]
        # labels    : dict[str, Tensor] — one key per LABEL_COLS
        #   single-label fields  → LongTensor  [B]      (class index)
        #   setting              → FloatTensor [B,  6]  (6 schema atomics, binary)
        ...

Label encoding
──────────────
    ds.label_encoders["architectural_style"].classes_
    ds.label_encoders["architectural_style"].transform(["Craftsman"])  → [2]
    # roof_type is now a single-label field — compound roofs are collapsed to
    # the "Compound" class at encode time:
    ds.label_encoders["roof_type"].classes_       # → ['Compound', 'Cross Gable', ...]
    ds.label_encoders["roof_type"].transform(["Hipped"])               # → [5]
    ds.label_encoders["roof_type"].transform(["Hipped; Front Gable"])  # KeyError — use
    # normalize_roof_type_label() first:  → "Compound" → [0]
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

import pandas as pd
import torch
from loguru import logger
from PIL import Image
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, MultiLabelBinarizer
from torch import Tensor
from torch.utils.data import Dataset
from torchvision import transforms

from .field_parser import normalize_value

# Optional import — only needed when callers pass model_config=
try:
    from ..models.model_config import ModelConfig
except ImportError:  # standalone / test context
    ModelConfig = None  # type: ignore[assignment,misc]


# ── Constants ────────────────────────────────────────────────────────────────

# Default image root and model settings.  csv_path is intentionally NOT
# defaulted here — callers must pass the path matching their dataset
# (e.g. "data/image_label_mapping_phase1.csv" or "data2/...").
IMAGE_ROOT_DEFAULT = "."
IMAGE_SIZE        = 224
RANDOM_STATE      = 42

# Label columns expected in the CSV.  The same fields apply to both the
# data/ and data2/ datasets for Phase 1 training.
PHASE1_LABEL_COLS: List[str] = [
    "architectural_style",
    "building_form",
    "roof_type",
    "primary_cladding",
    "stories",
    "alteration_level",
    "setting",           # schema 'multi': building’s relation to adjacent lots/street
    "chimney_present",   # derived: "Yes"/"No" gate from Chimney multipart column
]
LABEL_COLS = PHASE1_LABEL_COLS   # dataset-agnostic alias

# Split column — used for stratification
STRATIFY_COL = "architectural_style"

# Standard ImageNet normalisation — correct for any backbone pretrained on
# ImageNet (ResNet, EfficientNet, MobileNet, ViT-IN21k, …).
# Override via make_splits(norm_mean=..., norm_std=...) when using a backbone
# with different statistics, e.g.:
#   CLIP  : mean=(0.48145, 0.45783, 0.40821), std=(0.26863, 0.26130, 0.27578)
#   [-1,1]: mean=(0.5, 0.5, 0.5),             std=(0.5, 0.5, 0.5)
IMAGENET_MEAN: Tuple[float, float, float] = (0.485, 0.456, 0.406)
IMAGENET_STD:  Tuple[float, float, float] = (0.229, 0.224, 0.225)

def normalize_roof_type_label(value: str) -> str:
    """Collapse compound/multi-type roof strings to the single label 'Compound'.

    Any raw roof_type value that contains "; " (i.e. surveyors selected more
    than one type) or is the bare meta-tag "Compound Roof" is normalised to the
    canonical single label "Compound".  All other values are returned unchanged.

    This converts roof_type from a multi-label problem (19-bit binary vector,
    ~13% Jaccard) to a clean single-label problem (~12 classes, CrossEntropy).

    Examples::

        normalize_roof_type_label("Hipped")              # → "Hipped"
        normalize_roof_type_label("Hipped; Front Gable") # → "Compound"
        normalize_roof_type_label("Compound Roof")       # → "Compound"
    """
    if "; " in value or value.strip() == "Compound Roof":
        return "Compound"
    return value


# Schema 'multi' field: how the building relates to adjacent lots and the street.
# 6 options sorted alphabetically — matches MultiLabelBinarizer class order.
SETTING_SCHEMA_ATOMICS: List[str] = [
    "Attached on 1 Side",
    "Attached on 2 Sides",
    "Corner",
    "Flush at Sidewalk",
    "Set at Back of Lot",
    "Set Back from Sidewalk",
]

# Dispatch table: multi-label column → fixed ordered list of schema atomics.
# Only 'setting' remains multi-label; roof_type was converted to single-label
# (compound roofs are folded into the 'Compound' class via PRE_ENCODE_TRANSFORMS).
MULTILABEL_ATOMICS: Dict[str, List[str]] = {
    "setting": SETTING_SCHEMA_ATOMICS,
}

# Columns that use MultiLabelBinarizer (→ FloatTensor[n_atomics]) instead of
# LabelEncoder (→ LongTensor scalar).  Derived from MULTILABEL_ATOMICS so the
# two are always in sync.
MULTILABEL_COLS: List[str] = list(MULTILABEL_ATOMICS.keys())

# Per-column label normalisation applied BEFORE LabelEncoder fitting and before
# per-sample encoding in __getitem__.  Use for fields that need bespoke
# string → canonical-string mapping beyond the generic normalize_value().
PRE_ENCODE_TRANSFORMS: Dict[str, Callable[[str], str]] = {
    "roof_type": normalize_roof_type_label,
}


# ── Transforms ───────────────────────────────────────────────────────────────

def build_train_transform(
    image_size: int = IMAGE_SIZE,
    norm_mean: Tuple[float, float, float] = IMAGENET_MEAN,
    norm_std:  Tuple[float, float, float] = IMAGENET_STD,
) -> transforms.Compose:
    """Augmented transform for training.

    Args:
        image_size: Spatial resolution passed to the backbone.
        norm_mean:  Per-channel mean matching the backbone's pretraining dataset.
        norm_std:   Per-channel std  matching the backbone's pretraining dataset.
    """
    return transforms.Compose([
        transforms.Resize((image_size + 32, image_size + 32)),
        transforms.RandomCrop(image_size),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1),
        transforms.ToTensor(),
        transforms.Normalize(norm_mean, norm_std),
    ])


def build_eval_transform(
    image_size: int = IMAGE_SIZE,
    norm_mean: Tuple[float, float, float] = IMAGENET_MEAN,
    norm_std:  Tuple[float, float, float] = IMAGENET_STD,
) -> transforms.Compose:
    """Clean centre-crop transform for validation and test.

    Args:
        image_size: Spatial resolution passed to the backbone.
        norm_mean:  Per-channel mean matching the backbone's pretraining dataset.
        norm_std:   Per-channel std  matching the backbone's pretraining dataset.
    """
    return transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(norm_mean, norm_std),
    ])


# ── Dataset ──────────────────────────────────────────────────────────────────

class ArchitecturalDataset(Dataset):
    """
    PyTorch Dataset for Phase 1 multi-task architectural classification.

    Args:
        df:             DataFrame slice (train / val / test rows).
        label_encoders: Shared dict of fitted encoders, one per PHASE1_LABEL_COLS.
                        Single-label cols → LabelEncoder; multi-label cols
                        (currently roof_type) → MultiLabelBinarizer.
        image_root:     Base path; image_path column values are joined to it.
        transform:      torchvision transform applied to each loaded image.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        label_encoders: Dict[str, Union[LabelEncoder, MultiLabelBinarizer]],
        image_root: str = IMAGE_ROOT_DEFAULT,
        transform: Optional[transforms.Compose] = None,
        image_size: int = IMAGE_SIZE,
    ) -> None:
        self.df            = df.reset_index(drop=True)
        self.label_encoders = label_encoders
        self.image_root    = Path(image_root)
        self.image_size    = image_size
        self.transform     = transform or build_eval_transform(image_size)

    # ── Dataset protocol ─────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Tuple[Tensor, Dict[str, Tensor]]:
        row = self.df.iloc[idx]

        # ── Image ─────────────────────────────────────────────────────────
        img_path = self.image_root / row["image_path"]
        try:
            image = Image.open(img_path).convert("RGB")
            image = self.transform(image)
        except (FileNotFoundError, OSError) as exc:
            logger.warning(f"Missing image at {img_path}: {exc}. Returning zeros.")
            image = torch.zeros(3, self.image_size, self.image_size)

        # ── Labels ────────────────────────────────────────────────────────
        labels: Dict[str, Tensor] = {}
        for col in PHASE1_LABEL_COLS:
            raw   = row[col]
            value = normalize_value(raw)        # field_parser — single source of truth
            if col in PRE_ENCODE_TRANSFORMS:
                value = PRE_ENCODE_TRANSFORMS[col](value)
            if col in MULTILABEL_COLS:
                # Multi-label: split on "; " → binary vector FloatTensor[n_atomics]
                parts = [p.strip() for p in value.split("; ")] if value else []
                vec = self.label_encoders[col].transform([parts])[0]
                labels[col] = torch.tensor(vec, dtype=torch.float32)
            else:
                # Single-label: integer class index → LongTensor scalar
                idx_  = self.label_encoders[col].transform([value])[0]
                labels[col] = torch.tensor(idx_, dtype=torch.long)

        return image, labels

    # ── Introspection helpers ─────────────────────────────────────────────

    @property
    def num_classes(self) -> Dict[str, int]:
        """Return {col: num_classes} dict for each label field."""
        return {col: len(enc.classes_) for col, enc in self.label_encoders.items()}

    @property
    def class_names(self) -> Dict[str, List[str]]:
        """Return {col: [class_name, ...]} sorted list for each label field."""
        return {col: list(enc.classes_) for col, enc in self.label_encoders.items()}

    def class_counts(self) -> Dict[str, Dict[str, int]]:
        """Return {col: {class_name: count}} from this split."""
        result: Dict[str, Dict[str, int]] = {}
        for col in PHASE1_LABEL_COLS:
            counts = self.df[col].value_counts().to_dict()
            result[col] = {str(k): int(v) for k, v in counts.items()}
        return result


# ── Split factory ─────────────────────────────────────────────────────────────

def make_splits(
    csv_path: str,
    image_root: str = IMAGE_ROOT_DEFAULT,
    train_ratio: float = 0.70,
    val_ratio:   float = 0.15,
    # test_ratio is implicitly 1 - train - val
    random_state: int = RANDOM_STATE,
    image_size: int = IMAGE_SIZE,
    norm_mean: Tuple[float, float, float] = IMAGENET_MEAN,
    norm_std:  Tuple[float, float, float] = IMAGENET_STD,
    model_config: "ModelConfig | None" = None,
    train_transform: Optional[transforms.Compose] = None,
    eval_transform:  Optional[transforms.Compose] = None,
) -> Tuple[ArchitecturalDataset, ArchitecturalDataset, ArchitecturalDataset]:
    """
    Load a label-mapping CSV, fit label encoders from its actual classes, and
    return building-stratified (train, val, test) ArchitecturalDataset instances.

    Works with any CSV produced by scripts/build_phase1_label_mapping.py,
    covering both the data/ and data2/ datasets:

        # data/ dataset (default)
        train, val, test = make_splits()

        # data2/ dataset
        train, val, test = make_splits(csv_path="data2/image_label_mapping_phase1.csv")

    The split is performed at building level (not image level) to prevent
    data leakage — all images of one building land in the same partition.
    Stratification is on architectural_style.  Classes with fewer than
    3 buildings fall back to a non-stratified split with a warning.

    Args:
        csv_path:        Path to the label-mapping CSV to load
        image_root:      Root directory; image_path values are relative to it
        train_ratio:     Fraction of buildings for training  (default 0.70)
        val_ratio:       Fraction of buildings for validation (default 0.15)
        random_state:    Reproducibility seed
        image_size:      Input resolution for the model (default 224).
                         Change to 384 or 512 when scaling up the backbone.
        norm_mean:       Per-channel normalisation mean matching the backbone's
                         pretraining dataset (default: ImageNet).
                         e.g. CLIP: (0.48145, 0.45783, 0.40821)
        norm_std:        Per-channel normalisation std (default: ImageNet).
                         e.g. CLIP: (0.26863, 0.26130, 0.27578)
        model_config:    If provided, image_size / norm_mean / norm_std are taken
                         from the ModelConfig.  Explicit keyword arguments for
                         those three params still take precedence over the config.
        train_transform: Override the default training transform entirely.
                         If None, build_train_transform(image_size, norm_mean, norm_std) is used.
        eval_transform:  Override the default eval transform entirely.
                         If None, build_eval_transform(image_size, norm_mean, norm_std) is used.

    Returns:
        (train_ds, val_ds, test_ds)
    """
    # Apply model_config first; explicit params win if caller passed them.
    if model_config is not None:
        if image_size == IMAGE_SIZE:   # caller didn't override
            image_size = model_config.image_size
        if norm_mean == IMAGENET_MEAN: # caller didn't override
            norm_mean = model_config.norm_mean
        if norm_std == IMAGENET_STD:   # caller didn't override
            norm_std = model_config.norm_std
        logger.info(f"ModelConfig applied: {model_config}")

    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Phase 1 CSV not found at {csv_path}. "
            "Run scripts/build_phase1_label_mapping.py first."
        )

    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df)} rows from {csv_path}")

    # ── Validate required columns ─────────────────────────────────────────
    missing_cols = [c for c in PHASE1_LABEL_COLS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"CSV is missing required columns: {missing_cols}")

    # ── Drop rows with any empty label ────────────────────────────────────
    before = len(df)
    df = df.dropna(subset=PHASE1_LABEL_COLS)
    df = df[df[PHASE1_LABEL_COLS].apply(
        lambda col: col.map(normalize_value) != ""
    ).all(axis=1)]
    if len(df) < before:
        logger.warning(f"Dropped {before - len(df)} rows with empty labels")

    # ── Fit encoders: MultiLabelBinarizer for multi-label cols, LabelEncoder for rest ──
    label_encoders: Dict[str, Union[LabelEncoder, MultiLabelBinarizer]] = {}
    for col in PHASE1_LABEL_COLS:
        if col in MULTILABEL_COLS:
            # Fixed schema atomics keep class order stable across datasets.
            mlb = MultiLabelBinarizer(classes=MULTILABEL_ATOMICS[col])
            all_rows = [
                [p.strip() for p in normalize_value(val).split("; ")]
                for val in df[col]
            ]
            mlb.fit(all_rows)
            label_encoders[col] = mlb
            logger.debug(f"  {col}: {len(mlb.classes_)} atomics (multi-label)")
        else:
            enc = LabelEncoder()
            transform_fn = PRE_ENCODE_TRANSFORMS.get(col)
            if transform_fn:
                enc.fit(df[col].map(normalize_value).map(transform_fn))
            else:
                enc.fit(df[col].map(normalize_value))
            label_encoders[col] = enc
            logger.debug(f"  {col}: {len(enc.classes_)} classes → {list(enc.classes_)}")

    logger.info(
        "Encoders fitted — class counts: "
        + ", ".join(
            f"{c}: {len(label_encoders[c].classes_)}{'(multi)' if c in MULTILABEL_COLS else ''}"
            for c in PHASE1_LABEL_COLS
        )
    )

    # ── Stratified 70 / 15 / 15 split — AT BUILDING LEVEL ───────────────
    # Split on buildings first so all images of one building land in the
    # same partition.  Splitting at image level would cause data leakage
    # (the model would be evaluated on buildings it already saw in training).
    test_ratio = round(1.0 - train_ratio - val_ratio, 10)

    # One row per building, carrying the stratification label
    buildings_df = (
        df.drop_duplicates(subset=["building_id"])[["building_id", STRATIFY_COL]]
        .reset_index(drop=True)
    )
    building_styles = buildings_df[STRATIFY_COL]

    # Check if stratification is possible at building level (need ≥ 3 per class)
    min_building_count = building_styles.value_counts().min()
    use_stratify = min_building_count >= 3

    if not use_stratify:
        logger.warning(
            f"Some {STRATIFY_COL} classes have < 3 buildings — "
            "falling back to non-stratified split."
        )

    # First cut: train buildings vs (val + test) buildings
    train_bids, temp_bids_df = train_test_split(
        buildings_df,
        test_size=round(1.0 - train_ratio, 10),
        random_state=random_state,
        stratify=building_styles if use_stratify else None,
    )

    # Second cut: val buildings vs test buildings
    stratify_temp = temp_bids_df[STRATIFY_COL] if use_stratify else None
    if use_stratify and stratify_temp.value_counts().min() < 2:
        stratify_temp = None
        logger.warning("Falling back to non-stratified val/test split.")

    val_bids, test_bids = train_test_split(
        temp_bids_df,
        test_size=round(test_ratio / (val_ratio + test_ratio), 10),
        random_state=random_state,
        stratify=stratify_temp,
    )

    # Map building IDs back to image rows
    df_train = df[df["building_id"].isin(train_bids["building_id"])]
    df_val   = df[df["building_id"].isin(val_bids["building_id"])]
    df_test  = df[df["building_id"].isin(test_bids["building_id"])]

    logger.info(
        f"Split — "
        f"train: {len(train_bids)} buildings / {len(df_train)} images, "
        f"val: {len(val_bids)} buildings / {len(df_val)} images, "
        f"test: {len(test_bids)} buildings / {len(df_test)} images"
    )

    # ── Build datasets ────────────────────────────────────────────────────
    train_ds = ArchitecturalDataset(
        df_train, label_encoders, image_root,
        transform=train_transform or build_train_transform(image_size, norm_mean, norm_std),
        image_size=image_size,
    )
    val_ds = ArchitecturalDataset(
        df_val, label_encoders, image_root,
        transform=eval_transform or build_eval_transform(image_size, norm_mean, norm_std),
        image_size=image_size,
    )
    test_ds = ArchitecturalDataset(
        df_test, label_encoders, image_root,
        transform=eval_transform or build_eval_transform(image_size, norm_mean, norm_std),
        image_size=image_size,
    )

    return train_ds, val_ds, test_ds


# ── CLI smoke test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import sys
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    parser = argparse.ArgumentParser(description="ArchitecturalDataset smoke test")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--csv",
        default=None,
        help="Path to the label-mapping CSV (e.g. data2/image_label_mapping_phase1.csv)",
    )
    group.add_argument(
        "--config",
        default="config/data.json",
        help="Dataset config file — csv path is derived from its stem (default: config/data.json)",
    )
    args = parser.parse_args()

    if args.csv:
        csv_path = args.csv
    else:
        from pathlib import Path as _Path
        csv_path = f"{_Path(args.config).stem}/image_label_mapping_phase1.csv"

    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        colorize=True,
        level="DEBUG",
    )

    train_ds, val_ds, test_ds = make_splits(csv_path=csv_path)

    print()
    print("=" * 60)
    print("  DATASET SMOKE TEST")
    print("=" * 60)
    print(f"  Train : {len(train_ds):>4} rows")
    print(f"  Val   : {len(val_ds):>4} rows")
    print(f"  Test  : {len(test_ds):>4} rows")
    print()
    print("  num_classes per field:")
    for col, n in train_ds.num_classes.items():
        print(f"    {col:<25} {n}")
    print()
    print("  class_names:")
    for col, names in train_ds.class_names.items():
        print(f"    {col:<25} {names}")
    print()

    # Pull one sample
    image, labels = train_ds[0]
    print(f"  Sample image shape  : {tuple(image.shape)}")
    print(f"  Sample image dtype  : {image.dtype}")
    print(f"  Sample labels:")
    for k, v in labels.items():
        if k in MULTILABEL_COLS:
            atomics = MULTILABEL_ATOMICS[k]
            active = [atomics[i] for i, b in enumerate(v.tolist()) if b]
            print(f"    {k}: {active}  (shape={tuple(v.shape)}, dtype={v.dtype})")
        else:
            print(f"    {k}: {v.item()}")
    print()

    # Verify label tensors are valid
    for col, tensor in labels.items():
        if col in MULTILABEL_COLS:
            atomics = MULTILABEL_ATOMICS[col]
            assert tensor.dtype == torch.float32, f"{col} must be float32"
            assert tensor.shape == (len(atomics),), \
                f"{col} shape {tuple(tensor.shape)} != ({len(atomics)},)"
        else:
            idx_ = tensor.item()
            n    = train_ds.num_classes[col]
            assert 0 <= idx_ < n, f"Label index {idx_} out of range [0, {n}) for {col}"
    print("  ✅ All label tensors valid")
    print("=" * 60)
