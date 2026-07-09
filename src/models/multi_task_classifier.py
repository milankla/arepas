"""
Multi-Task Architectural Classifier

Predicts 25+ building attributes from photos using hierarchical multi-task learning.
Stages: Easy visual features → Style classification → Fine-grained details → Alterations
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models
from torchvision.models import (
    ResNet18_Weights,
    ResNet50_Weights,
    EfficientNet_B0_Weights,
    EfficientNet_B5_Weights,
)
from typing import Dict, List, Optional, Literal
from enum import Enum

from .model_config import ModelConfig


# Tasks with strong statistical co-dependence (Cramér's V ≥ 0.5).
# All three share a single 512-dim intermediate layer (style_group_fc) before
# their prediction heads to prevent learning separate shortcuts for the same concept.
# Source: scripts/attribute_dependency_analysis.py
#   architectural_style  ↔  building_form :  V = 0.923
#   building_form        ↔  roof_type     :  V = 0.725
#   architectural_style  ↔  roof_type     :  V = 0.521
# See docs/ATTRIBUTE_DEPENDENCY_ANALYSIS.md for full Cramér's V matrix.
STYLE_GROUP_TASKS = frozenset({'architectural_style', 'building_form', 'roof_type'})
STYLE_GROUP_DIM = 512

# Tasks that use FocalLoss instead of CrossEntropyLoss.
# primary_cladding: ~80% Brick in Phase 1 dataset — focal loss forces the model
# to learn minority cladding classes (Stucco, Asbestos, Aluminum) rather than
# collapsing to the majority. gamma=2.0 is the standard Lin et al. (2017) value.
# Source: docs/ATTRIBUTE_DEPENDENCY_ANALYSIS.md § Key Finding 5
# Single-label task routed through class-weighted FocalLoss (see per-task
# 'focal_loss' config keys, which are the actual dispatch mechanism). This
# frozenset is informational/documentation only.
#
# NOTE (2026-07-09): focal loss + inverse-frequency class weights were trialled
# on architectural_style and building_form (b5_pair_v2_phase2b) and REVERTED.
# architectural_style's dominant "No Clear Style" class (51.5%) is a legitimate
# majority, so reweighting collapsed accuracy below the majority baseline
# (77% -> 38%) and hurt macro-F1 too. Do not re-enable without a different
# strategy (e.g. more/better data), not loss reweighting.
FOCAL_LOSS_TASKS = frozenset({'primary_cladding'})
FOCAL_GAMMA_DEFAULT = 2.0

PairedFusionMode = Literal['concat_mlp', 'crop_residual', 'task_gated_residual']


def checkpoint_has_paired_fusion(state_dict: Dict[str, torch.Tensor]) -> bool:
    return any(key.startswith('paired_fusion.') for key in state_dict)


def normalize_paired_fusion_state_dict(state_dict: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
    """Map paired-v1 fusion checkpoint keys to the paired-v2 module layout."""
    remapped = dict(state_dict)
    for key, tensor in state_dict.items():
        if key.startswith(('paired_fusion.0.', 'paired_fusion.1.', 'paired_fusion.2.')):
            new_key = key.replace('paired_fusion.', 'paired_fusion.concat_mlp.', 1)
            remapped.setdefault(new_key, tensor)
    return remapped


class PairedViewFusion(nn.Module):
    """Fuse full-image and crop features for paired-view training.

    ``concat_mlp`` preserves the original paired-v1 behavior.  The residual
    modes start from crop features so a paired model does not have to relearn
    the crop-only baseline through a random projection before it can use context.
    """

    def __init__(
        self,
        feature_dim: int,
        mode: PairedFusionMode = 'concat_mlp',
        task_names: Optional[List[str]] = None,
        gate_init: str = 'crop_prior',
        gate_overrides: Optional[Dict[str, float]] = None,
        residual_scales: Optional[Dict[str, float]] = None,
        crop_bypass_tasks: Optional[List[str]] = None,
    ):
        super().__init__()
        self.mode = mode
        self.feature_dim = feature_dim
        self.gate_init = gate_init
        self.gate_overrides = gate_overrides or {}
        self.crop_bypass_tasks = set(crop_bypass_tasks or [])

        if mode == 'concat_mlp':
            self.concat_mlp = nn.Sequential(
                nn.Linear(feature_dim * 2, feature_dim),
                nn.ReLU(),
                nn.Dropout(0.3),
            )
        elif mode == 'crop_residual':
            self.full_residual = nn.Sequential(
                nn.Linear(feature_dim, feature_dim),
                nn.ReLU(),
                nn.Dropout(0.3),
            )
            self.residual_scale = nn.Parameter(torch.tensor(0.0))
        elif mode == 'task_gated_residual':
            self.full_residual = nn.Sequential(
                nn.Linear(feature_dim, feature_dim),
                nn.ReLU(),
                nn.Dropout(0.3),
            )
            names = sorted(set(task_names or []) | {'style_group'})
            self.task_gates = nn.ModuleDict({
                name: nn.Linear(feature_dim * 2, 1)
                for name in names
            })
            self.task_residual_scales = nn.ParameterDict({
                name: nn.Parameter(torch.tensor(self._initial_residual_scale(name, residual_scales)))
                for name in names
            })
            self._init_task_gates()
        else:
            raise ValueError(f"Unsupported paired fusion mode: {mode}")

    def _initial_gate_probability(self, task_name: str) -> float:
        if task_name in self.gate_overrides:
            return self.gate_overrides[task_name]
        if self.gate_init != 'crop_prior':
            return 0.5
        if task_name == 'setting':
            return 0.65
        if task_name in {'architectural_style', 'building_form', 'style_group'}:
            return 0.25
        if task_name == 'stories':
            return 0.01
        if task_name == 'roof_type':
            return 0.03
        if task_name == 'primary_cladding':
            return 0.20
        if task_name in {'chimney_present', 'wall_features', 'window'}:
            return 0.08
        if task_name in {'entrance', 'roof_materials'}:
            return 0.12
        if task_name in {'landscape_features', 'associated_buildings', 'building_category', 'current_use', 'original_use'}:
            return 0.60
        return 0.05

    def _initial_residual_scale(self, task_name: str, residual_scales: Optional[Dict[str, float]]) -> float:
        if residual_scales and task_name in residual_scales:
            return residual_scales[task_name]
        if self.gate_init != 'crop_prior':
            return 1.0
        if task_name == 'stories':
            return 0.25
        if task_name == 'roof_type':
            return 0.50
        if task_name in {'wall_features', 'window'}:
            return 0.60
        if task_name in {'entrance', 'roof_materials', 'primary_cladding'}:
            return 0.75
        return 1.0

    def _init_task_gates(self) -> None:
        for task_name, gate in self.task_gates.items():
            nn.init.zeros_(gate.weight)
            p = self._initial_gate_probability(task_name)
            bias = torch.logit(torch.tensor(p, dtype=gate.bias.dtype))
            nn.init.constant_(gate.bias, float(bias))

    def forward(
        self,
        full_features: torch.Tensor,
        crop_features: torch.Tensor,
        task_name: Optional[str] = None,
    ) -> torch.Tensor:
        if self.mode == 'concat_mlp':
            return self.concat_mlp(torch.cat([full_features, crop_features], dim=1))

        residual = self.full_residual(full_features)
        if self.mode == 'crop_residual':
            return crop_features + self.residual_scale * residual

        if task_name is None:
            raise ValueError("task_name is required for task_gated_residual fusion")
        if task_name in self.crop_bypass_tasks:
            return crop_features
        gate_name = task_name if task_name in self.task_gates else 'style_group'
        gate = torch.sigmoid(
            self.task_gates[gate_name](torch.cat([full_features, crop_features], dim=1))
        )
        scale = self.task_residual_scales[gate_name]
        return crop_features + scale * gate * residual


class FocalLoss(nn.Module):
    """
    Focal Loss for class-imbalanced single-label classification.

    FL(p_t) = -(1 - p_t)^gamma * log(p_t)

    The modulating factor (1 - p_t)^gamma down-weights easy (well-classified)
    examples and concentrates training on the hard minority classes.

    Reference: "Focal Loss for Dense Object Detection" (Lin et al., 2017)
    Used here for: primary_cladding (~80% Brick dominance in Phase 1 dataset)

    Args:
        gamma:  Focusing parameter. 0 = standard cross-entropy. Default: 2.0
        reduction: 'mean' or 'sum'. Default: 'mean'
        weight: Optional FloatTensor[num_classes] of per-class inverse-frequency
                weights.  Registered as a buffer so it moves to the correct
                device automatically with .to(device) / .cuda().
                When provided, the cross-entropy term is scaled by weight[class]
                *before* the focal modulating factor — this is equivalent to
                class-weighted focal loss as used in RetinaNet variants.
    """

    def __init__(
        self,
        gamma: float = FOCAL_GAMMA_DEFAULT,
        reduction: str = 'mean',
        weight: Optional[torch.Tensor] = None,
        ignore_index: int = -100,
        label_smoothing: float = 0.0,
    ):
        super().__init__()
        self.gamma = gamma
        self.reduction = reduction
        self.ignore_index = ignore_index
        self.label_smoothing = label_smoothing
        # register_buffer: tensor moves to device with .to() / .cuda(),
        # saved/loaded with state_dict, but NOT treated as a learnable param.
        # Passing None is valid — sets self.weight = None.
        self.register_buffer('weight', weight)

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Args:
            logits: Raw (un-normalised) class scores  [B, num_classes]
            targets: Integer class indices             [B]. Entries equal to
                     ``ignore_index`` are excluded from the loss (used to mask
                     out-of-scope supervision, e.g. chimney on basic surveys).
        Returns:
            Scalar focal loss
        """
        # Pass class weights to cross_entropy for per-class upweighting.
        # weight must be on the same device as logits (guaranteed by register_buffer).
        # ignore_index → those entries get 0 loss in the 'none' reduction.
        ce = F.cross_entropy(
            logits, targets, weight=self.weight,
            reduction='none', ignore_index=self.ignore_index,
            label_smoothing=self.label_smoothing,
        )  # [B]
        pt = torch.exp(-ce)                                       # probability of correct class
        focal = (1.0 - pt) ** self.gamma * ce                    # ignored entries → 0
        if self.reduction == 'sum':
            return focal.sum()
        # Mean over valid (non-ignored) samples only; clamp guards an
        # all-masked batch (returns a graph-connected 0, no gradient).
        n_valid = (targets != self.ignore_index).sum()
        return focal.sum() / n_valid.clamp(min=1)


class TaskDifficulty(Enum):
    """Task difficulty levels for progressive training"""
    EASY = "easy"           # Stories, Roof Type, Primary Cladding
    MEDIUM = "medium"       # Architectural Style, Building Form
    HARD = "hard"          # Roof Features, Wall Features
    VERY_HARD = "very_hard" # Alteration Detection


class TaskConfig:
    """Configuration for each prediction task"""
    
    # Phase 1: Easy Visual Features
    EASY_TASKS = {
        'stories': {
            'num_classes': 6,
            'classes': ['1', '1.5', '2', '2.5', '3+', 'Unknown'],
            'loss_weight': 0.15,
            # 90 %+ class '1' in both datasets — focal loss prevents the head
            # from collapsing to predicting "1" for every building.
            'focal_loss': True,
            'focal_gamma': 2.0,
        },
        'roof_type': {
            'num_classes': 12,  # data-driven at runtime; ~12 classes after Compound folding
            # Single-label: any building with multiple roof types is collapsed to
            # "Compound" by normalize_roof_type_label() in the dataset loader.
            # Focal loss: "Compound" (~15%), Hip-on-Gable, Mansard etc. are minorities.
            'loss_weight': 0.12,
            'focal_loss': True,
            'focal_gamma': 2.0,
        },
        'primary_cladding': {
            'num_classes': 7,
            'classes': ['Brick', 'Wood', 'Stucco', 'Stone', 'Vinyl', 'Aluminum', 'Other'],
            # Focal loss: ~80% Brick in Phase 1 → minority classes need up-weighting.
            # Weight reduced from 0.15; focal loss handles within-class discrimination.
            'loss_weight': 0.10,
            'focal_loss': True,
            'focal_gamma': 2.0,
        },
        'chimney_present': {
            'num_classes': 2,
            # Schema gate: "Does the building have chimneys?" (Yes/No).
            # Sorted alphabetically to match LabelEncoder.fit() order.
            'classes': ['No', 'Yes'],
            'loss_weight': 0.10,
            # Extreme imbalance: ~90-96 % No in both datasets.
            'focal_loss': True,
            'focal_gamma': 2.0,
        },
        'setting': {
            'num_classes': 6,
            # Schema 'multi' field — 6 options sorted alphabetically (matches
            # MultiLabelBinarizer class order and SETTING_SCHEMA_ATOMICS).
            # ~19.5% of rows select 2 options; Corner almost always co-occurs
            # with Set Back from Sidewalk.  Extreme skew: Set Back present in
            # ~94% of rows — focal loss prevents trivial all-ones prediction.
            'classes': [
                'Attached on 1 Side', 'Attached on 2 Sides', 'Corner',
                'Flush at Sidewalk', 'Set at Back of Lot', 'Set Back from Sidewalk',
            ],
            'loss_weight': 0.10,
            'multi_label': True,
            'focal_loss': True,
            'focal_gamma': 2.0,
        }
    }
    
    # Phase 2: Architectural Classification
    MEDIUM_TASKS = {
        'architectural_style': {
            'num_classes': 12,
            'classes': ['Craftsman', 'Colonial Revival', 'Tudor Revival', 'Ranch',
                       'Cape Cod', 'Contemporary', 'Modern', 'Minimal Traditional',
                       'Prairie', 'Mediterranean', 'Victorian', 'Other'],
            # PRIMARY TARGET: increased from 0.25. Dominates the style-group branch.
            'loss_weight': 0.35,
        },
        'building_form': {
            'num_classes': 8,
            'classes': ['Bungalow', 'Ranch', 'Cape Cod', 'Two-Story', 'Split-Level',
                       'Colonial', 'Contemporary', 'Other'],
            # Reduced from 0.20: Cramér's V=0.923 with architectural_style means
            # these tasks are near-redundant. Lower weight prevents double-counting
            # the same underlying signal through two separate loss terms.
            'loss_weight': 0.12,
        },
    }
    
    # Phase 3: Fine-Grained Features (Multi-label)
    HARD_TASKS = {
        'roof_features': {
            'num_classes': 8,  # Multi-label
            'classes': ['Brackets', 'Eaves-Boxed', 'Eaves-Open', 'Dormers', 
                       'Purlins', 'Rafter Tails', 'Gables', 'Decorative Elements'],
            'loss_weight': 0.10,
            'multi_label': True
        },
        'wall_features': {
            'num_classes': 21,
            'loss_weight': 0.05,
            'multi_label': True
        },
        'landscape_features': {
            'num_classes': 17,
            'loss_weight': 0.03,
            'multi_label': True,
        },
        'window': {
            'num_classes': 25,
            'loss_weight': 0.045,
            'multi_label': True,
        },
        'entrance': {
            'num_classes': 14,
            'loss_weight': 0.035,
            'multi_label': True,
        },
        'associated_buildings': {
            'num_classes': 6,
            'loss_weight': 0.025,
            'multi_label': True,
        },
        'building_category': {
            'num_classes': 3,
            'loss_weight': 0.025,
            'focal_loss': True,
            'focal_gamma': 2.0,
        },
        'current_use': {
            'num_classes': 5,
            'loss_weight': 0.02,
            'focal_loss': True,
            'focal_gamma': 2.0,
        },
        'roof_materials': {
            'num_classes': 6,
            'loss_weight': 0.025,
            'multi_label': True,
        },
        'original_use': {
            'num_classes': 5,
            'loss_weight': 0.015,
            'focal_loss': True,
            'focal_gamma': 2.0,
        },
        # Chimney sub-fields — schema-compliant multi-label stubs.
        # loss_weight=0.0: only ~330 positive buildings across both datasets;
        # 5 of 7 material atomics have < 10 samples — not learnable yet.
        # Raise loss_weight once data volume or augmentation addresses sparsity.
        'chimney_material': {
            'num_classes': 7,
            'classes': [
                'Brick', 'Concrete', 'Metal', 'Other Chimney Material',
                'Stone', 'Stucco', 'Unknown Chimney Material',
            ],
            'loss_weight': 0.0,
            'multi_label': True,
        },
        'chimney_features': {
            'num_classes': 4,
            'classes': [
                'Chimney Pots', 'Decorative', 'Multiple Flues', 'Other Chimney Features',
            ],
            'loss_weight': 0.0,
            'multi_label': True,
        },
    }
    
    # Phase 4: Alteration Detection (Requires expert labels)
    VERY_HARD_TASKS = {
        'alteration_level': {
            'num_classes': 5,
            # Alphabetical order matches sklearn LabelEncoder.fit().
            'classes': [
                '1 - Completely Altered',
                '2 - Major Alterations',
                '3 - Moderate Alterations',
                '4 - Minor Alterations',
                '5 - Not Altered',
            ],
            'loss_weight': 0.15,
        },
        'alterations_windows': {
            'num_classes': 2,
            'classes': ['Original', 'Replaced'],
            'loss_weight': 0.08
        },
        'alterations_roof': {
            'num_classes': 2,
            'classes': ['Original', 'Modified'],
            'loss_weight': 0.08
        }
    }


class MultiTaskArchitecturalClassifier(nn.Module):
    """
    Hierarchical multi-task classifier for building attributes.
    
    Architecture:
        1. Shared Backbone (ResNet50/EfficientNet/ViT)
        2. Task-specific heads with different difficulties
        3. Progressive training: Easy → Medium → Hard → Very Hard
    """
    
    def __init__(
        self,
        backbone: str = 'resnet50',
        weights: Optional[str] = 'DEFAULT',
        active_phase: int = 1,  # 1: Easy, 2: +Medium, 3: +Hard, 4: +Very Hard
        freeze_backbone: bool = False,
        model_config: Optional[ModelConfig] = None,
        num_classes: Optional[Dict[str, int]] = None,
        paired_views: bool = False,
        paired_fusion_mode: PairedFusionMode = 'concat_mlp',
        paired_gate_init: str = 'crop_prior',
        paired_gate_overrides: Optional[Dict[str, float]] = None,
        paired_residual_scales: Optional[Dict[str, float]] = None,
        paired_crop_bypass_tasks: Optional[List[str]] = None,
    ):
        """
        Args:
            backbone:      Backbone architecture name (default: 'resnet50').
            weights:       Torchvision weights preset ('DEFAULT' = ImageNet).
            active_phase:  Which task groups to activate (1–4).
            freeze_backbone: Freeze backbone weights (useful for fine-tuning).
            model_config:  Optional ModelConfig — drives backbone selection.
            num_classes:   Per-task class counts from the dataset, e.g.
                           ``train_ds.num_classes``.  Values here override the
                           static counts in TaskConfig, making head sizes
                           data-driven.  Tasks absent from this dict fall back
                           to the TaskConfig default.  Pass this whenever
                           training against a real CSV to avoid shape mismatches.

                           Example::

                               train_ds, val_ds, test_ds = make_splits(csv_path=...)
                               model = MultiTaskArchitecturalClassifier(
                                   num_classes=train_ds.num_classes
                               )
        """
        super().__init__()

        # model_config drives backbone selection when provided;
        # explicit backbone= kwarg still takes precedence if both are passed.
        if model_config is not None and backbone == 'resnet50':
            backbone = model_config.backbone

        # Per-task class counts supplied by the caller override TaskConfig values.
        # Stored here so _build_task_heads() can reference them.
        self._num_classes_override: Dict[str, int] = num_classes or {}

        self.active_phase = active_phase
        self.paired_views = paired_views
        self.paired_fusion_mode = paired_fusion_mode
        self.paired_gate_init = paired_gate_init
        self.paired_gate_overrides = paired_gate_overrides or {}
        self.paired_residual_scales = paired_residual_scales or {}
        self.paired_crop_bypass_tasks = paired_crop_bypass_tasks or []
        
        # Shared feature extractor
        self.backbone = self._build_backbone(backbone, weights)
        self.feature_dim = self._get_feature_dim(backbone)
        
        if freeze_backbone:
            for param in self.backbone.parameters():
                param.requires_grad = False

        # Shared style-group layer — projects backbone features to 512-dim for
        # the three most co-dependent tasks (see STYLE_GROUP_TASKS above).
        # Independent tasks (Setting, Stories, Cladding, Window, Entrance)
        # receive raw backbone features and bypass this layer entirely.
        self.style_group_fc = nn.Sequential(
            nn.Linear(self.feature_dim, STYLE_GROUP_DIM),
            nn.ReLU(),
            nn.Dropout(0.3)
        )

        # Task-specific heads
        self.task_heads = nn.ModuleDict()
        self._build_task_heads()

        self.paired_fusion = (
            PairedViewFusion(
                feature_dim=self.feature_dim,
                mode=paired_fusion_mode,
                task_names=list(self.task_heads.keys()),
                gate_init=paired_gate_init,
                gate_overrides=self.paired_gate_overrides,
                residual_scales=self.paired_residual_scales,
                crop_bypass_tasks=self.paired_crop_bypass_tasks,
            )
            if paired_views else None
        )
        
    def _build_backbone(self, backbone: str, weights: Optional[str]):
        """Build shared feature extractor.

        Args:
            backbone: Architecture name ('resnet50', 'efficientnet_b0', or
                      'efficientnet_b5').
            weights: Weight preset string.  Use 'DEFAULT' for ImageNet-pretrained
                     weights (recommended), or None to train from scratch.
                     Passed to the torchvision weights= API (v0.13+).
        """
        if backbone == 'resnet18':
            w = ResNet18_Weights[weights] if weights else None
            model = models.resnet18(weights=w)
            return nn.Sequential(*list(model.children())[:-1])
        elif backbone == 'resnet50':
            w = ResNet50_Weights[weights] if weights else None
            model = models.resnet50(weights=w)
            # Remove final classification layer
            return nn.Sequential(*list(model.children())[:-1])
        elif backbone == 'efficientnet_b0':
            w = EfficientNet_B0_Weights[weights] if weights else None
            model = models.efficientnet_b0(weights=w)
            return nn.Sequential(*list(model.children())[:-1])
        elif backbone == 'efficientnet_b5':
            w = EfficientNet_B5_Weights[weights] if weights else None
            model = models.efficientnet_b5(weights=w)
            return nn.Sequential(*list(model.children())[:-1])
        else:
            raise ValueError(f"Unsupported backbone: {backbone}")
    
    def _get_feature_dim(self, backbone: str) -> int:
        """Get feature dimension from backbone"""
        if 'resnet18' in backbone:
            return 512
        elif 'resnet50' in backbone:
            return 2048
        elif 'efficientnet_b0' in backbone:
            return 1280
        elif 'efficientnet_b5' in backbone:
            return 2048
        else:
            return 2048
    
    def _build_task_heads(self):
        """Build classification heads driven by data when num_classes is provided.

        **Primary path (training / inference):** when ``num_classes`` is supplied
        to the constructor (the normal case), heads are built for *exactly* those
        tasks — no more, no less.  Tasks present in ``TaskConfig`` but absent
        from ``num_classes`` are silently skipped, so untrained heads never
        appear in inference output.  This eliminates the previous bug where
        ``building_category`` was built as a Phase 2 head even though it was
        never in ``TRAINING_LABEL_COLS``.

        **Fallback path (no data / unit tests):** when ``num_classes`` is empty
        the old phase-gated construction is used so the model can be
        instantiated without a dataset (e.g. for architecture inspection).
        """
        # Complete registry of known task configs.
        all_known: Dict[str, Dict] = {
            **TaskConfig.EASY_TASKS,
            **TaskConfig.MEDIUM_TASKS,
            **TaskConfig.HARD_TASKS,
            **TaskConfig.VERY_HARD_TASKS,
        }

        if self._num_classes_override:
            # Data-driven: build exactly the tasks the dataset provides labels for.
            tasks_to_build: Dict[str, Dict] = {
                task: all_known.get(task, {'num_classes': n})
                for task, n in self._num_classes_override.items()
            }
        else:
            # Fallback: phase-gated construction (backward compat / no-data path).
            tasks_to_build = {}
            if self.active_phase >= 1:
                tasks_to_build.update(TaskConfig.EASY_TASKS)
            if self.active_phase >= 2:
                tasks_to_build.update(TaskConfig.MEDIUM_TASKS)
            if self.active_phase >= 3:
                tasks_to_build.update(TaskConfig.HARD_TASKS)
            if self.active_phase >= 4:
                tasks_to_build.update(TaskConfig.VERY_HARD_TASKS)

        # Build heads.
        # Style-group tasks (architectural_style, building_form, roof_type) receive
        # the 512-dim output of style_group_fc — their heads are a single Linear.
        # All other tasks get their own 2-layer projection from backbone features.
        for task_name, task_config in tasks_to_build.items():
            # Data-driven count from the caller (train_ds.num_classes) takes
            # precedence over the static placeholder in TaskConfig.
            num_classes = self._num_classes_override.get(
                task_name, task_config['num_classes']
            )

            # building_category has a fixed, schema-defined cardinality. A
            # data-derived count that diverges signals a label/data problem
            # (e.g. an unexpected category leaking in, or a category dropped
            # from the split) rather than a head we should silently resize to
            # fit bad data. Fail loudly so the encoder/CSV gets fixed.
            if (
                task_name == 'building_category'
                and task_name in self._num_classes_override
            ):
                expected = all_known['building_category']['num_classes']
                if num_classes != expected:
                    raise ValueError(
                        f"building_category head size mismatch: data yielded "
                        f"{num_classes} classes but TaskConfig declares "
                        f"{expected}. Check the label encoder / CSV for "
                        f"unexpected or missing building categories."
                    )

            if task_name in STYLE_GROUP_TASKS:
                # Input is STYLE_GROUP_DIM (512) from the shared style_group_fc
                self.task_heads[task_name] = nn.Linear(STYLE_GROUP_DIM, num_classes)
            else:
                # Independent 2-layer head from raw backbone features
                self.task_heads[task_name] = nn.Sequential(
                    nn.Flatten(),
                    nn.Linear(self.feature_dim, 512),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    nn.Linear(512, num_classes)
                )
    
    def _extract_features(self, x: torch.Tensor) -> torch.Tensor:
        features = self.backbone(x)
        if features.dim() == 4:
            features = features.flatten(1)
        return features

    def forward(self, x: torch.Tensor | Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """
        Forward pass through network
        
        Args:
            x: Input images [B, 3, H, W]
            
        Returns:
            Dictionary of predictions for each active task
        Style-group tasks (architectural_style, building_form, roof_type) are
        routed through style_group_fc (shared 512-dim projection) to leverage
        their strong co-dependence (Cramér's V 0.521–0.923). All other tasks
        receive backbone features directly.
        """
        if isinstance(x, dict):
            if self.paired_fusion is None:
                raise ValueError("Received paired-view input, but model was not created with paired_views=True")
            full_features = self._extract_features(x["full"])
            crop_features = self._extract_features(x["crop"])
            if self.paired_fusion_mode == 'task_gated_residual':
                outputs = {}
                for task_name, head in self.task_heads.items():
                    if task_name in STYLE_GROUP_TASKS:
                        task_features = self.paired_fusion(full_features, crop_features, task_name)
                        feat = self.style_group_fc(task_features)
                    else:
                        feat = self.paired_fusion(full_features, crop_features, task_name)
                    outputs[task_name] = head(feat)
                return outputs
            features = self.paired_fusion(full_features, crop_features)
        else:
            features = self._extract_features(x)

        # Style-group branch: shared 512-dim projection for co-dependent tasks
        style_features = self.style_group_fc(features)

        # Route each task to the appropriate feature tensor
        outputs = {}
        for task_name, head in self.task_heads.items():
            feat = style_features if task_name in STYLE_GROUP_TASKS else features
            outputs[task_name] = head(feat)

        return outputs
    
    def get_task_config(self, task_name: str) -> Dict:
        """Get configuration for specific task"""
        all_configs = {
            **TaskConfig.EASY_TASKS,
            **TaskConfig.MEDIUM_TASKS,
            **TaskConfig.HARD_TASKS,
            **TaskConfig.VERY_HARD_TASKS
        }
        return all_configs.get(task_name, {})


class MultiTaskLoss(nn.Module):
    """
    Combined loss for multi-task learning with task weighting
    """
    
    def __init__(
        self,
        active_phase: int = 1,
        focal_gamma: float = FOCAL_GAMMA_DEFAULT,
        class_weights: Optional[Dict[str, torch.Tensor]] = None,
        label_smoothing: float = 0.0,
    ):
        """
        Args:
            active_phase:   Controls which task configs are active (1–4).
            focal_gamma:    Focusing parameter for FocalLoss on imbalanced tasks.
                            0.0 = standard cross-entropy. Default: 2.0 (Lin et al., 2017).
            class_weights:  Optional dict mapping task name → FloatTensor[n_classes]
                            of inverse-frequency weights.  When provided, each
                            focal-loss task gets its own FocalLoss instance with
                            the corresponding weight tensor baked in.  Tasks not
                            present in the dict (or None dict) use unweighted FL.
            label_smoothing: CrossEntropy label smoothing (0.0 = off) applied to
                            single-label tasks (both focal and plain-CE paths).
                            Regularizes overconfident heads; leave 0.0 to keep
                            the historical default behavior.
        """
        super().__init__()
        self.active_phase = active_phase
        self.label_smoothing = label_smoothing
        self.ce_loss = nn.CrossEntropyLoss()
        self.bce_loss = nn.BCEWithLogitsLoss()          # multi-label tasks

        # Build per-task FocalLoss instances so each can carry its own class-weight
        # tensor (registered as a buffer → moves to device with .to() automatically).
        # Using nn.ModuleDict ensures buffers are included in state_dict and .to().
        all_task_configs = {
            **TaskConfig.EASY_TASKS,
            **TaskConfig.MEDIUM_TASKS,
            **TaskConfig.HARD_TASKS,
            **TaskConfig.VERY_HARD_TASKS,
        }
        focal_modules: Dict[str, nn.Module] = {}
        bce_modules: Dict[str, nn.Module] = {}
        for task_name, task_cfg in all_task_configs.items():
            if task_cfg.get('focal_loss', False):
                w = (class_weights or {}).get(task_name)   # None if not provided
                focal_modules[task_name] = FocalLoss(
                    gamma=focal_gamma, weight=w, label_smoothing=label_smoothing,
                )
            if task_cfg.get('multi_label', False):
                pos_weight = (class_weights or {}).get(task_name)
                bce_modules[task_name] = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
        self._focal_losses = nn.ModuleDict(focal_modules)
        self._bce_losses = nn.ModuleDict(bce_modules)

        # Fallback for any focal-loss task not pre-registered above.
        self._default_focal = FocalLoss(gamma=focal_gamma, label_smoothing=label_smoothing)
        
    def forward(
        self,
        predictions: Dict[str, torch.Tensor],
        targets: Dict[str, torch.Tensor]
    ) -> Dict[str, torch.Tensor]:
        """
        Calculate weighted loss across all tasks
        
        Args:
            predictions: Dict of task predictions
            targets: Dict of task ground truth labels
            
        Returns:
            Dict containing total loss and per-task losses
        """
        losses = {}
        total_loss = 0.0
        
        # Loss is computed for every task where both a prediction and a target are
        # available.  The full registry is used here so new tasks don't need a
        # phase-number bump just to participate in loss computation.  The guard
        # below ('if task_name not in predictions or task_name not in targets')
        # already handles tasks that are absent from the current batch.
        all_tasks = {
            **TaskConfig.EASY_TASKS,
            **TaskConfig.MEDIUM_TASKS,
            **TaskConfig.HARD_TASKS,
            **TaskConfig.VERY_HARD_TASKS,
        }

        # Calculate loss for each task
        for task_name, task_config in all_tasks.items():
            if task_name not in predictions or task_name not in targets:
                continue
            
            pred = predictions[task_name]
            target = targets[task_name]
            weight = task_config['loss_weight']
            
            # Dispatch to the appropriate loss function:
            #   multi_label tasks  → BCEWithLogitsLoss  (sigmoid, binary per class)
            #   focal_loss tasks   → per-task FocalLoss  (class-weighted focal CE)
            #   everything else    → CrossEntropyLoss
            if task_config.get('multi_label', False):
                bce = self._bce_losses[task_name] if task_name in self._bce_losses else self.bce_loss
                task_loss = bce(pred, target.float())
            elif task_config.get('focal_loss', False):
                focal = self._focal_losses[task_name] if task_name in self._focal_losses else self._default_focal
                task_loss = focal(pred, target)
            else:
                # Masked-mean CrossEntropy: average over valid (non-ignored)
                # samples only. Plain nn.CrossEntropyLoss(reduction='mean')
                # returns NaN when a whole batch is ignore_index (-100) — which
                # happens for masked single-label tasks like architectural_style
                # (compound styles). clamp(min=1) yields a graph-connected 0 for
                # an all-masked batch instead, mirroring FocalLoss above.
                ce = F.cross_entropy(
                    pred, target, reduction='none', ignore_index=-100,
                    label_smoothing=self.label_smoothing,
                )
                n_valid = (target != -100).sum()
                task_loss = ce.sum() / n_valid.clamp(min=1)
            
            losses[task_name] = task_loss
            total_loss += weight * task_loss
        
        losses['total'] = total_loss
        return losses


# Example usage
if __name__ == "__main__":
    # Preferred pattern: pass data-driven class counts so model heads match real data.
    #
    #   from src.loader.architectural_dataset import make_splits
    #   train_ds, val_ds, test_ds = make_splits("data2/image_label_mapping_phase1.csv")
    #   model = MultiTaskArchitecturalClassifier(
    #       backbone='resnet50',
    #       active_phase=1,
    #       num_classes=train_ds.num_classes,  # data-driven head sizes
    #   )
    #
    # The smoke-test below falls back to TaskConfig placeholder counts because
    # no CSV is available at import time.

    # Phase 1: Easy tasks — static fallback counts (fine for a shape-only smoke test)
    model_phase1 = MultiTaskArchitecturalClassifier(
        backbone='resnet50',
        weights='DEFAULT',
        active_phase=1,
        freeze_backbone=False,
    )

    # Test forward pass
    batch_size = 4
    dummy_images = torch.randn(batch_size, 3, 224, 224)
    outputs = model_phase1(dummy_images)

    print("Phase 1 (Easy Tasks) — TaskConfig fallback counts:")
    for task_name, output in outputs.items():
        config = model_phase1.get_task_config(task_name)
        n = model_phase1._num_classes_override.get(task_name, config['num_classes'])
        print(f"  {task_name}: {tuple(output.shape)} -> {n} classes")

    # Phase 2: Add medium tasks (architectural style)
    model_phase2 = MultiTaskArchitecturalClassifier(
        backbone='resnet50',
        weights='DEFAULT',
        active_phase=2,
        freeze_backbone=False,
    )

    outputs_phase2 = model_phase2(dummy_images)
    print(f"\nPhase 2 (Easy + Medium): {len(outputs_phase2)} total tasks")
