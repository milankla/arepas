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

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from urllib.parse import quote, unquote

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
PHASE3_LABEL_DEFINITIONS_PATH = Path(__file__).resolve().parents[2] / "config" / "phase3_label_definitions.json"

# ── Survey-level gating for chimney_present ──────────────────────────────────
# The schema collects the Chimney field only at surveyLevel 3 ("Full Survey").
# In basic/partial surveys the field is out of scope, so a "No" there means
# "not assessed", not "no chimney".  We therefore supervise chimney_present only
# on Full-Survey buildings and mask the rest using the standard PyTorch
# ignore_index sentinel, which CrossEntropyLoss / FocalLoss skip in the loss and
# compute_metrics() excludes from accuracy/F1.
IGNORE_INDEX = -100
# Sentinel normalized value for single-label tasks meaning "mask this task for
# this building": excluded from the LabelEncoder's classes and from class-weight
# counts, and emitted as IGNORE_INDEX in __getitem__ (loss & metrics skip it).
# Used for architectural_style compound ("X; Y") entries, which are too rare
# (<50 buildings per combo) to train and would otherwise pollute "Other Style".
IGNORE_LABEL = "__IGNORE__"
FULL_SURVEY_VALUE = "Full Survey"
SURVEY_LEVEL_COL = "survey_level"
SURVEY_GATED_COLS = frozenset({"chimney_present"})

# Label columns that are actively trained in the current dataset.
# Adding a new task here (e.g. building_category) is all that's needed
# to make the data loader encode it and expose it to the training loop.
# The model will automatically build a head for it via _build_task_heads.
TRAINING_LABEL_COLS: List[str] = [
    "architectural_style",
    "building_form",
    "roof_type",
    "primary_cladding",
    "stories",
    # "alteration_level",  # removed: majority-class collapse (acc=63% ≈ 57% naive baseline,
    #                        # macro F1=27% after 14 epochs). Tier 4 task — not learnable from
    #                        # single facade photos without expert labels or class coarsening.
    #                        # Re-add when coarsened to 2-3 classes or data volume increases.
    "setting",           # schema 'multi': building's relation to adjacent lots/street
    "chimney_present",   # derived: "Yes"/"No" gate from Chimney multipart column
]
PHASE1_LABEL_COLS = TRAINING_LABEL_COLS  # backward-compat alias — prefer TRAINING_LABEL_COLS
LABEL_COLS = TRAINING_LABEL_COLS   # dataset-agnostic alias


def _load_phase3_label_definitions() -> Dict[str, Any]:
    if not PHASE3_LABEL_DEFINITIONS_PATH.exists():
        logger.warning(f"Phase 3 label definitions not found: {PHASE3_LABEL_DEFINITIONS_PATH}")
        return {"fields": {}}
    with PHASE3_LABEL_DEFINITIONS_PATH.open() as f:
        return json.load(f)


PHASE3_LABEL_DEFINITIONS = _load_phase3_label_definitions()
PHASE3_FIELD_SPECS: Dict[str, Dict[str, Any]] = PHASE3_LABEL_DEFINITIONS.get("fields", {})
PHASE3_LABEL_COLS: List[str] = list(PHASE3_FIELD_SPECS.keys())

# ── Phase 3 forward-plan tuning knobs (see docs/PHASE3_FORWARD_PLAN.md) ──
# Multi-label BCE pos_weight cap. Lowered 10.0 -> 3.5 for the combined-data
# Phase 3 run: at 10.0 the heads over-predict ~1.5-2.2x (low precision, the #1
# bottleneck in the June audit). 3.5 keeps minority recall without the runaway
# false positives. See docs/PHASE3_FORWARD_PLAN.md item C.
MULTILABEL_POS_WEIGHT_CLAMP: float = 3.5
# Minimum positive examples a multi-label atomic must have to stay in the loss.
# 0 = disabled. Set to 50 for the combined-data Phase 3 run: the configured
# train_labels are already curated to >=50 buildings, so this is a safety net
# that auto-drops any atomic that falls below the floor in the train split.
PHASE3_MIN_POSITIVE_COUNT: int = 50

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

# Single-label roof_type classes with < 50 buildings in the combined
# (data + data2 + data3) set are folded into "Other": too few to learn or to
# evaluate reliably (a ~15% test split leaves only a handful of buildings).
# Counts as of 2026-06-29: Shed 40, Mansard 34, Barrel Roof 25, Pyramidal 21,
# Gable 11, Unknown Roof Type 6, Monitor 2  (-> Other, ~148 buildings total).
RARE_ROOF_TYPES: frozenset = frozenset({
    "Shed", "Mansard", "Barrel Roof", "Pyramidal", "Gable",
    "Unknown Roof Type", "Monitor",
})


def normalize_roof_type_label(value: str) -> str:
    """Collapse compound/multi-type roof strings to the single label 'Compound'.

    Any raw roof_type value that contains "; " (i.e. surveyors selected more
    than one type) or is the bare meta-tag "Compound Roof" is normalised to the
    canonical single label "Compound".  Rare single-label classes (< 50
    buildings, see RARE_ROOF_TYPES) are folded into "Other".  All other values
    are returned unchanged.

    This converts roof_type from a multi-label problem (19-bit binary vector,
    ~13% Jaccard) to a clean single-label problem (~12 classes, CrossEntropy).

    Examples::

        normalize_roof_type_label("Hipped")              # → "Hipped"
        normalize_roof_type_label("Hipped; Front Gable") # → "Compound"
        normalize_roof_type_label("Compound Roof")       # → "Compound"
        normalize_roof_type_label("Pyramidal")           # → "Other"
    """
    if "; " in value or value.strip() == "Compound Roof":
        return "Compound"
    if value.strip() in RARE_ROOF_TYPES:
        return "Other"
    return value


# building_form duplicate spellings / typos -> canonical, plus the four
# "Gas Station - *" subtypes grouped into a single "Gas Station" family class.
BUILDING_FORM_CANON: Dict[str, str] = {
    "Central Block With Projecting Bays": "Central Block with Projecting Bays",
    "Central Block with Projecting Bay":  "Central Block with Projecting Bays",
    "Central Block ith Projecting Bay":   "Central Block with Projecting Bays",
    "Hipped Roof Box":                    "Hipped-Roof Box",
    "Central Passage Double Pile":        "Central Passage Double-Pile",
    "Apartment Block":                    "Apartment - Block",
    "Apartment-Block":                    "Apartment - Block",
    "Apartment Complex":                  "Apartment - Complex",
    "Split-Level":                        "Split Level",
    "High Rise":                          "High-Rise",
    "Comercial - Other":                  "Commercial - Other",
    "Gas Station - Oblong Box":           "Gas Station",
    "Gas Station - Other":                "Gas Station",
    "Gas Station - House with Canopy":    "Gas Station",
    "Gas Station - Cottage":              "Gas Station",
}

# building_form classes kept as their own label: >= 50 buildings in the combined
# (data + data2 + data3) set after BUILDING_FORM_CANON merging, plus the grouped
# "Gas Station" family. Every other value folds into "Other" (63 raw -> 27).
KEEP_BUILDING_FORMS: frozenset = frozenset({
    "Minimal Traditional", "Ranch", "Bungalow", "Gable Front",
    "Central Block with Projecting Bays", "Classic Cottage", "Terrace Type",
    "Transitional Ranch", "Duplex", "Commercial/Industrial Block", "Foursquare",
    "Hipped-Roof Box", "Apartment - Block", "One-Part Commercial Block",
    "Bi-Level", "Gabled Ell", "Split Level", "Service Bay Business",
    "Two-Part Commercial Block", "Commercial - Other",
    "Central Passage Double-Pile", "Hall and Parlor", "Apartment - Garden Court",
    "Shotgun", "Apartment - Complex", "Gas Station",
})


def normalize_building_form_label(value: str) -> str:
    """Canonicalize building_form spellings and fold rare classes into "Other".

    Merges duplicate spellings / typos (e.g. "Apartment Block" -> "Apartment -
    Block"), groups the four "Gas Station - *" subtypes into a single
    "Gas Station" class, then folds any class with < 50 buildings in the combined
    set into "Other" (63 raw classes -> 27).

    Examples::

        normalize_building_form_label("Ranch")               # → "Ranch"
        normalize_building_form_label("Apartment Block")     # → "Apartment - Block"
        normalize_building_form_label("Gas Station - Other") # → "Gas Station"
        normalize_building_form_label("Quonset")             # → "Other"
    """
    v = value.strip()
    v = BUILDING_FORM_CANON.get(v, v)
    if v == "" or v in KEEP_BUILDING_FORMS:
        return v
    return "Other"


def normalize_stories_label(value: str) -> str:
    """Coarsen rare high-storey classes into a single '3+' bucket.

    Combined dataset distribution (building-level, 17 269 buildings):
        "1"    : 11963 (69.3%)  ← 1-storey + the 4 "1/2" half/below-grade
        "1-1/2":  3010 (17.4%)
        "2"    :  1739 (10.1%)
        "2-1/2":   423  (2.4%)  ← 2-1/2 + "2.5" decimal variant
        "3+"   :   134  (0.8%)  ← 3, 3-1/2, 4, 5-9, 10-19, 20+ merged

    Coarsening strategy
    ───────────────────
    * "1/2"                            → "1" (only 4 buildings; < 50-per-class
                                            floor, and a raised-basement/half
                                            storey reads closest to 1-storey)
    * "2.5"                            → "2-1/2" (decimal-notation variant)
    * "3", "3-1/2", "4", "5-9",
      "10-19", "20+"                   → "3+" (all genuinely 3+ stories)

    Result: 5 classes — "1", "1-1/2", "2", "2-1/2", "3+".
    "2-1/2" is a real, common Denver category (Foursquares etc.) and is kept
    separate from the open-ended "3+" tall-building bucket.

    The "3+" bucket still has too few samples for strong recall, but macro F1
    is measured per class and class weights up-weight it so the model at least
    attempts to learn tall buildings.

    Examples::

        normalize_stories_label("1")      # → "1"
        normalize_stories_label("1/2")    # → "1"
        normalize_stories_label("2.5")    # → "2-1/2"
        normalize_stories_label("3")      # → "3+"
        normalize_stories_label("10-19")  # → "3+"
    """
    _TALL = {"3", "4", "5-9", "10-19", "3-1/2", "20+"}
    if value in _TALL:
        return "3+"
    if value == "2.5":  # decimal-notation variant (data3)
        return "2-1/2"
    if value == "1/2":  # 4 buildings, below the 50-per-class floor
        return "1"
    return value


# Viable architectural_style classes: ≥50 buildings each in the combined dataset
# (owner-approved exception: "Mission" at 46).  All other single-style raw values
# collapse into "Other Style"; compound "X; Y" entries are masked (IGNORE_LABEL),
# not folded here.
ARCH_STYLE_KEEP: frozenset = frozenset({
    "No Clear Architectural Style",
    "Craftsman",
    "Ranch",
    "Victorian Cottage",
    "Edwardian",
    "English Norman Cottage",
    "Modern Movement",
    "Classical Revival",
    "Mixed Style",
    "Queen Anne",
    "Dutch Colonial Revival",
    "Contemporary",
    "Mission",
    "Italianate",
    "Colonial Revival",
})


def normalize_arch_style_label(value: str) -> str:
    """Coarsen raw architectural_style classes into 15 viable + 'Other Style'.

    Compound "X; Y" entries are masked out of training (return IGNORE_LABEL);
    see the guard in the function body.

    Raw class distribution in data2/ (26 160 images):
        No Clear Architectural Style : 12 774  (48.8%)
        Craftsman                    :  5 061  (19.4%)
        Ranch                        :  2 763  (10.6%)
        Victorian Cottage            :  1 240   (4.7%)
        Edwardian                    :  1 163   (4.4%)
        English Norman Cottage       :    762   (2.9%)
        Modern Movement              :    573   (2.2%)
        Classical Revival            :    291   (1.1%)
        Mixed Style                  :    265   (1.0%)
        Queen Anne                   :    252   (1.0%)
        Dutch Colonial Revival       :    195   (0.7%)
        Contemporary                 :    157   (0.6%)
        Mission                      :    114   (0.4%)
        24 further classes with < 100 samples each → "Other Style"

    Threshold: keep classes with ≥ 100 image-level examples (≈ 27 buildings at
    the dataset average of ~3.7 images/building).  Below that, there are too few
    training samples for reliable recall even with class weighting.

    The existing raw value "Other Style" (23 examples) is absorbed into the
    merged bucket, so the output label set is unambiguous.

    Examples::

        normalize_arch_style_label("Craftsman")        # → "Craftsman"
        normalize_arch_style_label("Googie")           # → "Other Style"
        normalize_arch_style_label("Other Style")      # → "Other Style"
        normalize_arch_style_label("Tudor Revival")    # → "Other Style"
        normalize_arch_style_label("Ranch; Contemporary")  # → IGNORE_LABEL
    """
    # Compound "X; Y" survey entries mix two styles.  Each distinct combo has
    # <50 buildings (319 buildings across 101 combos in the combined dataset),
    # so we mask them out of the style head entirely rather than dump them in
    # "Other Style".  The sentinel becomes IGNORE_INDEX in __getitem__.
    if ";" in value:
        return IGNORE_LABEL
    return value if value in ARCH_STYLE_KEEP else "Other Style"


# Mapping used by normalize_cladding_label — defined at module level so it can
# be inspected / extended without touching the function body.
CLADDING_COARSEN_MAP: Dict[str, str] = {
    # ── Brick ─────────────────────────────────────────────────────────────
    "Brick":                                 "Brick",
    # ── Stucco ────────────────────────────────────────────────────────────
    "Stucco":                                "Stucco",   # data3 generic (no qualifier)
    "Stucco - Modern":                       "Stucco",
    "Stucco - Historic":                     "Stucco",
    "Stucco - Smooth":                       "Stucco",
    "Stucco-Modern":                         "Stucco",   # data3 typo variant
    "Stucco-Smooth":                         "Stucco",   # data3 typo variant
    "Stucco -Historic":                      "Stucco",   # data3 typo variant
    "Stucco -Smooth":                        "Stucco",   # data3 typo variant
    # ── Vinyl siding (large enough to keep separate) ─────────────────────
    "Siding - Vinyl":                        "Siding - Vinyl",
    # ── All other siding variants → one bucket ────────────────────────────
    "Siding - Horizontal, Unknown Material": "Siding - Other",
    "Siding - Horizontal, Wood":             "Siding - Other",
    "Siding - Aluminum":                     "Siding - Other",
    "Siding - Vertical, Unknown Material":   "Siding - Other",
    "Siding - Vertical, Wood":               "Siding - Other",
    "Siding - Wood Horizontal":              "Siding - Other",  # data3 variant
    "Siding - Wood Vertical":                "Siding - Other",  # data3 variant
    "Sidint - Wood Vertical":                "Siding - Other",  # data3 typo
    "Siding - Wood":                         "Siding - Other",  # data3 generic
    "Wood - Horizontal":                     "Siding - Other",  # data3 variant
    "Siding - Board and Batten":             "Siding - Other",
    "Board and Batten":                      "Siding - Other",  # data3 without prefix
    "Siding - Unknown Horizontal":           "Siding - Other",
    "Siding - Angled Wood":                  "Siding - Other",
    "Siding - Metal":                        "Siding - Other",
    "Siding - Rolled Asphalt":               "Siding - Other",
    # ── Shingle variants ──────────────────────────────────────────────────
    "Shingles - Asbestos":                   "Shingles",
    "Shingles - Plain":                      "Shingles",
    "Shingles - Asphalt":                    "Shingles",
    "Shingles - Unknown":                    "Shingles",
    "Shingles - Unknown Material":           "Shingles",
    "Shingles - Decorative":                 "Shingles",
    # ── Masonry / stone ───────────────────────────────────────────────────
    "Concrete - Block":                      "Concrete / Stone",
    "Concrete - Modular/Precast":            "Concrete / Stone",
    "Concrete Block":                        "Concrete / Stone",  # data3 variant
    "Concrete":                              "Concrete / Stone",  # data3 generic
    "Screen Block":                          "Concrete / Stone",
    "Stone - Faux":                          "Concrete / Stone",
    "Stone - Smooth":                        "Concrete / Stone",
    "Stone - Rusticated":                    "Concrete / Stone",
    "Stone - Other":                         "Concrete / Stone",
    "Stone - Cobble":                        "Concrete / Stone",
    # ── Sheet metal ───────────────────────────────────────────────────────
    "Sheet Metal":                           "Sheet Metal",
    "Metal":                                 "Sheet Metal",       # data3 generic
    # ── Catch-all ─────────────────────────────────────────────────────────
    "Other Cladding":                        "Other Cladding",
    "Unknown Cladding":                      "Other Cladding",
    "Glass":                                 "Other Cladding",
    "Terra Cotta":                           "Other Cladding",
}


def normalize_cladding_label(value: str) -> str:
    """Coarsen raw primary_cladding values into 8 meaningful groups.

    data3 records cladding as compound strings (e.g. "Brick; Siding - Vinyl").
    Split on '; ' and take the first token — the surveyor's primary material —
    then look it up in CLADDING_COARSEN_MAP.  Single-material values (data2)
    are unaffected since they contain no '; '.

    Any remaining unseen value falls back to "Other Cladding".
    """
    primary = value.split("; ")[0].strip()
    return CLADDING_COARSEN_MAP.get(primary, "Other Cladding")


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

# Canonicalise surveyor typo / casing / phrasing variants of the 6 setting
# atomics so they bind to the schema option instead of being silently dropped
# by the MultiLabelBinarizer (which ignores unknown labels).
#   "Set Back at Alley" (33) is intentionally NOT mapped — it is not one of the
#   6 schema options and is semantically distinct from "Set at Back of Lot",
#   so it stays dropped rather than guessed.
SETTING_ATOM_CANON: Dict[str, str] = {
    "Set Back From Sidewalk": "Set Back from Sidewalk",   # casing
    "et Back from Sidewalk":  "Set Back from Sidewalk",   # leading-char typo
    "Flush with Sidewalk":    "Flush at Sidewalk",        # phrasing
    "Attached 1 Side":        "Attached on 1 Side",       # phrasing
    "Attached 2 Sides":       "Attached on 2 Sides",      # phrasing
}


def normalize_setting_atomic(atom: str) -> str:
    """Map a raw setting atomic to its canonical schema spelling."""
    atom = atom.strip()
    return SETTING_ATOM_CANON.get(atom, atom)


# Per-atomic normaliser for multi-label columns, applied in parse_multilabel_value
# before the MultiLabelBinarizer.  Keyed by column name.
MULTILABEL_ATOM_TRANSFORMS: Dict[str, Callable[[str], str]] = {
    "setting": normalize_setting_atomic,
}

# Dispatch table: multi-label column → fixed ordered list of schema atomics.
# Only 'setting' remains multi-label; roof_type was converted to single-label
# (compound roofs are folded into the 'Compound' class via PRE_ENCODE_TRANSFORMS).
MULTILABEL_ATOMICS: Dict[str, List[str]] = {
    "setting": SETTING_SCHEMA_ATOMICS,
}

for _field_name, _field_spec in PHASE3_FIELD_SPECS.items():
    if _field_spec.get("target_type") == "multi_label":
        MULTILABEL_ATOMICS[_field_name] = list(_field_spec.get("train_labels", []))

# Columns that use MultiLabelBinarizer (→ FloatTensor[n_atomics]) instead of
# LabelEncoder (→ LongTensor scalar).  Derived from MULTILABEL_ATOMICS so the
# two are always in sync.
MULTILABEL_COLS: List[str] = list(MULTILABEL_ATOMICS.keys())

# Per-column label normalisation applied BEFORE LabelEncoder fitting and before
# per-sample encoding in __getitem__.  Use for fields that need bespoke
# string → canonical-string mapping beyond the generic normalize_value().
#
# roof_type:            collapse multi-type compound roofs → "Compound"
# stories:              coarsen rare high-storey classes   → "2+" / "3+"
# primary_cladding:     coarsen 18 raw classes             → 8 meaningful groups
# architectural_style:  coarsen raw classes → 15 + "Other Style" (compounds masked)
PRE_ENCODE_TRANSFORMS: Dict[str, Callable[[str], str]] = {
    "roof_type":           normalize_roof_type_label,
    "building_form":       normalize_building_form_label,
    "stories":             normalize_stories_label,
    "primary_cladding":    normalize_cladding_label,
    "architectural_style": normalize_arch_style_label,
}


def _phase3_single_label_value(col: str, value: str) -> str:
    spec = PHASE3_FIELD_SPECS.get(col, {})
    return spec.get("class_mapping", {}).get(value, value)


def normalize_label_value(col: str, raw: object) -> str:
    value = normalize_value(raw)
    if col in PHASE3_FIELD_SPECS and PHASE3_FIELD_SPECS[col].get("target_type") == "single_label":
        return _phase3_single_label_value(col, value)
    transform_fn = PRE_ENCODE_TRANSFORMS.get(col)
    return transform_fn(value) if transform_fn else value


def _split_semicolon_multi(value: str) -> List[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def _subfield_option_map(spec: Dict[str, Any]) -> Dict[str, List[str]]:
    options: Dict[str, set[str]] = {subfield: set() for subfield in spec.get("included_subfields", [])}
    labels = (
        list(spec.get("train_labels", []))
        + list(spec.get("probation_labels", []))
        + list(spec.get("exclude_or_defer_labels", []))
    )
    for label in labels:
        if ": " not in label:
            continue
        subfield, option = label.split(": ", 1)
        if subfield in options:
            options[subfield].add(option)
    return {subfield: sorted(values, key=len, reverse=True) for subfield, values in options.items()}


def _extract_multipart_values(record: str, subfield: str) -> List[str]:
    """All raw values for ``subfield`` in ``record`` (schema-qualified or alias).

    Matches the schema-qualified key ("Window Type") and its bare alias with the
    field-group prefix dropped ("Type" — data3 Format-A). Uses ``finditer`` so
    *repeated* subfields ("Type: Fixed; Type: Sliding") all return, and searches
    anywhere in the record so a leading record-index prefix ("Window 1: ...",
    "Entrance 2: ...") is transparently skipped.
    """
    short = subfield.split(" ", 1)[-1]  # "Window Type" -> "Type"
    values: List[str] = []
    for key in {subfield, short}:
        pattern = rf"(?<![A-Za-z]){re.escape(key)}:\s*(.*?)(?=;\s*[A-Z][A-Za-z/ ]+:|$)"
        for match in re.finditer(pattern, record):
            value = match.group(1).strip()
            if value:
                values.append(value)
    return values


def _match_schema_options(raw: str, options: List[str]) -> List[str]:
    if not raw:
        return []
    if raw in options:
        return [raw]

    hits: List[str] = []
    remaining = raw
    for option in options:
        pattern = r"(?<!\w)" + re.escape(option) + r"(?!\w)"
        if re.search(pattern, remaining):
            hits.append(option)
            remaining = re.sub(pattern, " ", remaining)
    return hits


def _parse_phase3_multipart_labels(value: str, spec: Dict[str, Any]) -> List[str]:
    """Parse a multipart multi-label cell into ``"Subfield: Option"`` labels.

    Tolerates three source shapes without changing Format-B behaviour:
      * Format-B: ``"Window 1: Window Type: Fixed; Window Features: Stone Sill"``
        (schema-qualified keys, optional "Window N:" record-index prefix).
      * Format-A: ``"Type: Fixed; Type: Sliding; Material: Vinyl"`` — bare
        subfield aliases and *repeated* subfields.
      * Bare values: ``"Stoop - Low"`` (no ``key:`` prefix at all) — matched
        against every included subfield's option set.
    Keyed segments whose subfield is not included (e.g. Material/Location for
    ``window``) contribute nothing, so their values cannot leak into a head.
    """
    labels: set[str] = set()
    option_map = _subfield_option_map(spec)
    for record in re.split(r"\s+\|\s+", value):
        for subfield, options in option_map.items():
            for raw_value in _extract_multipart_values(record, subfield):
                for option in _match_schema_options(raw_value, options):
                    labels.add(f"{subfield}: {option}")
        if ":" not in record:
            # Bare value(s) with no "key:" prefix (e.g. "Stoop - Low").
            for subfield, options in option_map.items():
                for option in _match_schema_options(record.strip(), options):
                    labels.add(f"{subfield}: {option}")
    return sorted(labels)


def parse_multilabel_value(col: str, raw: object) -> List[str]:
    value = normalize_value(raw)
    if not value:
        return []

    if col not in PHASE3_FIELD_SPECS:
        parts = [part.strip() for part in value.split("; ") if part.strip()]
        transform = MULTILABEL_ATOM_TRANSFORMS.get(col)
        if transform:
            parts = [transform(part) for part in parts]
        return parts

    spec = PHASE3_FIELD_SPECS[col]
    train_labels = set(spec.get("train_labels", []))
    class_mapping = spec.get("class_mapping", {})
    if spec.get("parser") == "multipart_schema_options":
        labels = _parse_phase3_multipart_labels(value, spec)
    else:
        labels = [class_mapping.get(label, label) for label in _split_semicolon_multi(value)]
    return sorted({label for label in labels if label in train_labels})


def phase3_enabled_label_cols(
    include_phase3_labels: bool = False,
    phase3_labels: Optional[List[str]] = None,
) -> List[str]:
    if not include_phase3_labels:
        return list(TRAINING_LABEL_COLS)
    selected_phase3_labels = list(PHASE3_LABEL_COLS) if phase3_labels is None else list(phase3_labels)
    unknown_labels = [label for label in selected_phase3_labels if label not in PHASE3_FIELD_SPECS]
    if unknown_labels:
        raise ValueError(
            f"Unknown Phase 3 labels: {unknown_labels}. "
            f"Available labels: {PHASE3_LABEL_COLS}"
        )
    return list(TRAINING_LABEL_COLS) + selected_phase3_labels


def label_requires_nonempty_value(col: str) -> bool:
    spec = PHASE3_FIELD_SPECS.get(col)
    if not spec:
        return True
    return spec.get("target_type") == "single_label"


def filter_atomics_by_min_positive(col: str, values, min_count: int) -> List[str]:
    """Return the multi-label atomics for ``col`` with at least ``min_count`` positives.

    ``values`` is an iterable of raw cell values (e.g. ``df[col]``). When
    ``min_count <= 0`` the full configured atomic set is returned unchanged
    (current behavior). Otherwise atomics with fewer than ``min_count`` positive
    examples are dropped from the loss — this enforces the Phase 3 forward-plan
    rule of excluding dead labels. See docs/PHASE3_FORWARD_PLAN.md.
    """
    atomics = list(MULTILABEL_ATOMICS[col])
    if min_count <= 0:
        return atomics
    counts = {label: 0 for label in atomics}
    for raw in values:
        for label in parse_multilabel_value(col, raw):
            if label in counts:
                counts[label] += 1
    kept = [label for label in atomics if counts[label] >= min_count]
    dropped = [label for label in atomics if counts[label] < min_count]
    if dropped:
        logger.warning(
            f"{col}: dropping {len(dropped)} sub-threshold atomics "
            f"(<{min_count} positives) from the loss: {dropped}"
        )
    return kept


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
        label_encoders: Shared dict of fitted encoders, one per TRAINING_LABEL_COLS.
                        Single-label cols → LabelEncoder; multi-label cols
                        (currently roof_type) → MultiLabelBinarizer.
        image_root:     Base path; image_path column values are joined to it.
        transform:      torchvision transform applied to each loaded image.
        cropped_root:   Optional root directory of pre-cropped images produced by
                        scripts/crop_dataset.py.  When set, __getitem__ attempts
                        to load ``<cropped_root>/<stem>_crop.jpg`` first and falls
                        back to the original path if the crop file is absent.
                        Set to None (default) to use the original images.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        label_encoders: Dict[str, Union[LabelEncoder, MultiLabelBinarizer]],
        image_root: str = IMAGE_ROOT_DEFAULT,
        transform: Optional[transforms.Compose] = None,
        image_size: int = IMAGE_SIZE,
        cropped_root: Optional[str] = None,
        paired_views: bool = False,
        label_cols: Optional[List[str]] = None,
    ) -> None:
        self.df            = df.reset_index(drop=True)
        self.label_encoders = label_encoders
        self.image_root    = Path(image_root)
        self.image_size    = image_size
        self.transform     = transform or build_eval_transform(image_size)
        self.cropped_root  = Path(cropped_root) if cropped_root else None
        self.paired_views  = paired_views
        self.label_cols    = label_cols or list(TRAINING_LABEL_COLS)

    def _resolve_image_paths(self, raw_image_path: str) -> Tuple[Path, Optional[Path]]:
        raw_image_path = unquote(raw_image_path)
        full_path = self.image_root / raw_image_path
        if not full_path.exists():
            encoded = quote(raw_image_path, safe="/._-~")
            alt = self.image_root / encoded
            if alt.exists():
                full_path = alt

        crop_path: Optional[Path] = None
        if self.cropped_root is not None:
            stem = Path(raw_image_path).stem
            img_par = Path(raw_image_path).parent
            parts = img_par.parts
            rel_dir = Path(*parts[1:]) if len(parts) > 1 else img_par
            crop_candidate = self.cropped_root / rel_dir / f"{stem}_crop.jpg"
            if crop_candidate.exists():
                crop_path = crop_candidate
        return full_path, crop_path

    def _load_image_tensor(self, img_path: Path) -> Tensor:
        try:
            image = Image.open(img_path).convert("RGB")
            return self.transform(image)
        except (FileNotFoundError, OSError) as exc:
            logger.warning(f"Missing image at {img_path}: {exc}. Returning zeros.")
            return torch.zeros(3, self.image_size, self.image_size)

    # ── Dataset protocol ─────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Tuple[Union[Tensor, Dict[str, Tensor]], Dict[str, Tensor]]:
        row = self.df.iloc[idx]

        # ── Image ─────────────────────────────────────────────────────────
        full_path, crop_path = self._resolve_image_paths(row["image_path"])
        if self.paired_views:
            image: Union[Tensor, Dict[str, Tensor]] = {
                "full": self._load_image_tensor(full_path),
                "crop": self._load_image_tensor(crop_path or full_path),
            }
        else:
            image = self._load_image_tensor(crop_path or full_path)

        # ── Labels ────────────────────────────────────────────────────────
        labels: Dict[str, Tensor] = {}
        # Survey level gates whether the chimney field was in scope; mask
        # chimney_present supervision on non-Full-Survey buildings.
        survey_level = str(row[SURVEY_LEVEL_COL]) if SURVEY_LEVEL_COL in row else ""
        chimney_masked = survey_level != FULL_SURVEY_VALUE
        for col in self.label_cols:
            raw   = row[col]
            if col in MULTILABEL_COLS:
                # Multi-label: split on "; " → binary vector FloatTensor[n_atomics]
                encoder = self.label_encoders[col]
                parts = parse_multilabel_value(col, raw)
                # Drop atomics outside the fitted schema (e.g. "Set Back at Alley"),
                # same as fit-time filtering, so the MultiLabelBinarizer doesn't emit
                # a per-sample "unknown class will be ignored" warning. The encoded
                # vector is identical either way.
                known = set(encoder.classes_)
                parts = [p for p in parts if p in known]
                vec = encoder.transform([parts])[0]
                labels[col] = torch.tensor(vec, dtype=torch.float32)
            elif col in SURVEY_GATED_COLS and chimney_masked:
                # Out-of-scope for this survey level → ignore_index sentinel so
                # the loss and metrics skip it (no building is dropped).
                labels[col] = torch.tensor(IGNORE_INDEX, dtype=torch.long)
            else:
                # Single-label: integer class index → LongTensor scalar
                value = normalize_label_value(col, raw)
                if value == IGNORE_LABEL:
                    # Masked for this task (e.g. compound architectural_style):
                    # emit the ignore sentinel so loss & metrics skip it while
                    # the building still supervises its other tasks.
                    labels[col] = torch.tensor(IGNORE_INDEX, dtype=torch.long)
                else:
                    idx_ = self.label_encoders[col].transform([value])[0]
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

    @property
    def class_weights(self) -> Dict[str, torch.Tensor]:
        """Balanced inverse-frequency class weights for single-label tasks.

        For each non-multi-label column, computes the sklearn-style balanced
        weight for each class:

            weight[i] = n_samples / (n_classes * count[i])

        This up-weights rare classes so the loss function penalises errors on
        minority classes more heavily.  Multi-label columns receive BCE
        ``pos_weight`` vectors:

            pos_weight[i] = n_negative[i] / n_positive[i]

        The same normalisation pipeline applied in ``__getitem__`` (field-parser
        ``normalize_value`` + any ``PRE_ENCODE_TRANSFORMS`` function) is applied
        here so that the weight tensor aligns with the fitted LabelEncoder.

        Returns:
            Dict mapping column name → FloatTensor of shape [n_classes].
        """
        weights: Dict[str, torch.Tensor] = {}
        for col in self.label_cols:
            if col in MULTILABEL_COLS:
                counts = torch.zeros(len(self.label_encoders[col].classes_), dtype=torch.float32)
                for value in self.df[col]:
                    labels = set(parse_multilabel_value(col, value))
                    for index, label in enumerate(self.label_encoders[col].classes_):
                        if label in labels:
                            counts[index] += 1
                negatives = len(self.df) - counts
                pos_weight = torch.ones_like(counts)
                nonzero = counts > 0
                pos_weight[nonzero] = negatives[nonzero] / counts[nonzero]
                weights[col] = pos_weight.clamp(max=MULTILABEL_POS_WEIGHT_CLAMP)
                continue

            enc = self.label_encoders[col]

            # Apply the same pipeline as __getitem__
            values: "pd.Series" = self.df[col].map(lambda value: normalize_label_value(col, value))

            # Drop masked (IGNORE_LABEL) rows so weights reflect only the
            # buildings actually supervised for this task (e.g. compound
            # architectural_style entries are masked out).
            values = values[values != IGNORE_LABEL]

            # Survey-gated tasks (chimney_present) are supervised only on
            # Full-Survey rows, so weight them over that subset to match the
            # samples that actually contribute to the loss.
            if col in SURVEY_GATED_COLS and SURVEY_LEVEL_COL in self.df.columns:
                mask = self.df[SURVEY_LEVEL_COL] == FULL_SURVEY_VALUE
                values = values[mask.values]

            n_classes = len(enc.classes_)
            n_samples = len(values)

            w = torch.ones(n_classes, dtype=torch.float32)
            for i, cls in enumerate(enc.classes_):
                count = int((values == cls).sum())
                if count > 0:
                    w[i] = n_samples / (n_classes * count)
                # else: leave w[i] = 1.0 (fallback for classes absent in this split)

            # Cap at 3× to prevent extreme weights on very rare classes
            # (e.g. stories "2+" = ×76 uncapped) from causing overfitting.
            # v5 max=10.0 → F1 ↑ but acc −9pp; v6 max=5.0 → acc −7.7pp.
            # 3.0 further softens minority push to recover more accuracy.
            w = w.clamp(max=3.0)

            weights[col] = w
        return weights

    def class_counts(self) -> Dict[str, Dict[str, int]]:
        """Return {col: {class_name: count}} from this split."""
        result: Dict[str, Dict[str, int]] = {}
        for col in self.label_cols:
            if col in MULTILABEL_COLS:
                counts = {label: 0 for label in self.label_encoders[col].classes_}
                for value in self.df[col]:
                    for label in parse_multilabel_value(col, value):
                        counts[label] += 1
                result[col] = counts
            else:
                values = self.df[col].map(lambda value: normalize_label_value(col, value))
                counts = values.value_counts().to_dict()
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
    model_config = None,
    train_transform: Optional[transforms.Compose] = None,
    eval_transform:  Optional[transforms.Compose] = None,
    cropped_root: Optional[str] = None,
    paired_views: bool = False,
    include_phase3_labels: bool = False,
    phase3_labels: Optional[List[str]] = None,
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
        cropped_root:    Optional path to a directory of pre-cropped images produced
                         by scripts/crop_dataset.py.  When set, __getitem__ tries
                         ``<cropped_root>/<stem>_crop.jpg`` before falling back to
                         the original image.  Pass None (default) to use originals.
        paired_views:    Return both full and cropped images as a dict with keys
                 ``full`` and ``crop``. Requires cropped_root for true
                 paired training; missing crops fall back to full image.
        include_phase3_labels: Include the nine Phase 3 label-definition fields
                 from config/phase3_label_definitions.json. Default is
                 False to preserve existing Phase 1/2 training behavior.
        phase3_labels: Optional subset of Phase 3 fields to include when
             include_phase3_labels is true. Use this for staged Phase 3
             experiments that exclude weak or deferred fields.

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
    active_label_cols = phase3_enabled_label_cols(include_phase3_labels, phase3_labels)

    # ── Validate required columns ─────────────────────────────────────────
    missing_cols = [c for c in active_label_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"CSV is missing required columns: {missing_cols}")

    # ── Drop rows with any empty label ────────────────────────────────────
    before = len(df)
    nonempty_label_cols = [col for col in active_label_cols if label_requires_nonempty_value(col)]
    df = df.dropna(subset=nonempty_label_cols)
    df = df[df[nonempty_label_cols].apply(
        lambda col: col.map(normalize_value) != ""
    ).all(axis=1)]
    if len(df) < before:
        logger.warning(f"Dropped {before - len(df)} rows with empty labels")

    # ── Fit encoders: MultiLabelBinarizer for multi-label cols, LabelEncoder for rest ──
    label_encoders: Dict[str, Union[LabelEncoder, MultiLabelBinarizer]] = {}
    for col in active_label_cols:
        if col in MULTILABEL_COLS:
            # Fixed schema atomics keep class order stable across datasets.
            # PHASE3_MIN_POSITIVE_COUNT (default 0 = off) can drop dead labels.
            atomics = filter_atomics_by_min_positive(col, df[col], PHASE3_MIN_POSITIVE_COUNT)
            atomic_set = set(atomics)
            mlb = MultiLabelBinarizer(classes=atomics)
            all_rows = [
                [label for label in parse_multilabel_value(col, val) if label in atomic_set]
                for val in df[col]
            ]
            mlb.fit(all_rows)
            label_encoders[col] = mlb
            logger.debug(f"  {col}: {len(mlb.classes_)} atomics (multi-label)")
        else:
            enc = LabelEncoder()
            mapped = df[col].map(lambda value: normalize_label_value(col, value))
            # Drop masked (IGNORE_LABEL) rows so the sentinel never becomes a
            # class — e.g. architectural_style compound "X; Y" entries.
            mapped = mapped[mapped != IGNORE_LABEL]
            enc.fit(mapped)
            label_encoders[col] = enc
            logger.debug(f"  {col}: {len(enc.classes_)} classes → {list(enc.classes_)}")

    logger.info(
        "Encoders fitted — class counts: "
        + ", ".join(
            f"{c}: {len(label_encoders[c].classes_)}{'(multi)' if c in MULTILABEL_COLS else ''}"
            for c in active_label_cols
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
        cropped_root=cropped_root,
        paired_views=paired_views,
        label_cols=active_label_cols,
    )
    val_ds = ArchitecturalDataset(
        df_val, label_encoders, image_root,
        transform=eval_transform or build_eval_transform(image_size, norm_mean, norm_std),
        image_size=image_size,
        cropped_root=cropped_root,
        paired_views=paired_views,
        label_cols=active_label_cols,
    )
    test_ds = ArchitecturalDataset(
        df_test, label_encoders, image_root,
        transform=eval_transform or build_eval_transform(image_size, norm_mean, norm_std),
        image_size=image_size,
        cropped_root=cropped_root,
        paired_views=paired_views,
        label_cols=active_label_cols,
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
