# Attribute Dependency Analysis

**Date:** March 7, 2026  
**Dataset:** `/data/` — 198 buildings, 19 datasets (Bungalows + Minimal Traditional)  
**Script:** `scripts/attribute_dependency_analysis.py`

---

## Cramér's V Association Matrix

Cramér's V measures association between categorical fields.  
`0` = no association · `1` = perfect association · `> 0.3` = meaningful for training strategy

|  | Arch. Style | Bldg. Form | Stories | Roof Type | Cladding | Setting |
|--|--|--|--|--|--|--|
| **Arch. Style** | 1.000 | **0.923** | 0.232 | **0.521** | 0.235 | 0.279 |
| **Bldg. Form** | **0.923** | 1.000 | 0.330 | **0.725** | 0.379 | 0.064 |
| **Stories** | 0.232 | 0.330 | 1.000 | 0.314 | 0.214 | 0.093 |
| **Roof Type** | **0.521** | **0.725** | 0.314 | 1.000 | **0.408** | **0.361** |
| **Cladding** | 0.235 | 0.379 | 0.214 | **0.408** | 1.000 | 0.226 |
| **Setting** | 0.279 | 0.064 | 0.093 | 0.361 | 0.226 | 1.000 |

---

## Dependency Tiers

### 🔴 Strong (V ≥ 0.5) — shared intermediate features beneficial

| Pair | V |
|------|---|
| Architectural Style ↔ Building Form | 0.923 |
| Building Form ↔ Roof Type | 0.725 |
| Architectural Style ↔ Roof Type | 0.521 |

### 🟡 Moderate (0.3 ≤ V < 0.5) — auxiliary task benefit possible

| Pair | V |
|------|---|
| Roof Type ↔ Primary Cladding | 0.408 |
| Building Form ↔ Primary Cladding | 0.379 |
| Roof Type ↔ Setting | 0.361 |
| Building Form ↔ Stories | 0.330 |
| Stories ↔ Roof Type | 0.314 |

### 🟢 Weak (V < 0.3) — independent heads preferred

| Pair | V |
|------|---|
| Architectural Style ↔ Setting | 0.279 |
| Architectural Style ↔ Primary Cladding | 0.235 |
| Architectural Style ↔ Stories | 0.232 |
| Primary Cladding ↔ Setting | 0.226 |
| Stories ↔ Primary Cladding | 0.214 |
| Stories ↔ Setting | 0.093 |
| Building Form ↔ Setting | 0.064 |

---

## Conditional Distributions

### Architectural Style → Roof Type

| Style | n | Top Roof Types |
|-------|---|----------------|
| No Clear Architectural Style | 101 | Hipped(52), Cross Gable(18), Side Gable(14) |
| Craftsman | 70 | Hip-on-Gable(15), Side Gable(15), Cross Gable(13) |
| Ranch | 18 | Hipped(16), Hipped; Front Gable(1), Side Gable(1) |
| English Norman Cottage | 5 | Cross Gable(3), Side Gable; Flat(1), Hipped; Front Gable(1) |
| Mixed Style | 2 | Cross Gable; Hipped(1), Hipped(1) |
| Classical Revival | 2 | Hipped(1), Side Gable(1) |

### Architectural Style → Primary Cladding

| Style | n | Top Cladding Types |
|-------|---|-------------------|
| No Clear Architectural Style | 101 | Brick(57), Shingles - Asbestos(15), Siding - Aluminum(9) |
| Craftsman | 70 | Brick(63), Stucco - Historic(4), Siding - Horizontal, Wood(3) |
| Ranch | 18 | Brick(16), Stucco - Historic(1), Concrete - Block(1) |
| English Norman Cottage | 5 | Brick(5) |
| Mixed Style | 2 | Stucco - Historic(1), Brick(1) |
| Classical Revival | 2 | Brick(1), Shingles - Asbestos(1) |

### Building Form → Stories (leakage risk check)

| Form | n | Stories distribution |
|------|---|----------------------|
| Minimal Traditional | 120 | 1 (119, **99%**), 1-1/2 (1, 1%) |
| Bungalow | 78 | 1 (63, 81%), 1-1/2 (14, 18%), 2 (1, 1%) |

### Alteration Level → Sub-field Presence

| Level | Altered sub-fields | % Present |
|-------|--------------------|-----------|
| 4 - Minor Alterations | 1 / 10 | 10.0% |
| 5 - Not Altered | 24 / 980 | 2.4% |

### Primary Cladding → Top Wall Features

| Cladding | n | Top Wall Features |
|----------|---|-------------------|
| Brick | 455 | Brick - Polychromatic(85), Brick - Patterned(79), Foundation - Concrete(49) |
| Shingles - Asbestos | 24 | Foundation - Concrete(13), Shutters(5), Gable Vents(3) |
| Stucco - Historic | 21 | Foundation - Not Visible(5), Belt Course(2), Shingles in Gable - Decorative(2) |
| Siding - Aluminum | 10 | Foundation - Concrete(6), Awnings(2), Shutters(1) |
| Concrete - Block | 9 | Foundation - Concrete(4), Shutters(4), Awnings(1) |
| Siding - Horizontal, Wood | 7 | Foundation - Concrete(5), Gable Vents(2) |

### Roof Type → Top Roof Features

| Roof Type | n | Top Roof Features |
|-----------|---|-------------------|
| Cross Gable | 8 | Rafter Tails(2), Eaves - Open(2), Brackets - Decorative(1) |
| Hip-on-Gable | 6 | Purlins(2), Eaves - Open(2), Eaves - Boxed(1) |
| Side Gable | 5 | Dormer - Shed(1), Dormer - Wall(1), Eaves - Open(1) |
| Cross Gable; Hipped | 4 | Eaves - Open(1), Parapet - Shaped(1), Rafter Tails(1) |
| Hipped | 2 | Eaves - Open(1), Rafter Tails(1) |

---

## Key Findings & Training Strategy Implications

### 1. Label Leakage Risk: `Building Form ↔ Architectural Style` (V=0.923)

These two fields are nearly interchangeable in this dataset:
- Minimal Traditional → 99% single-storey, very uniform
- Bungalow → 81% single-storey, slightly more variation

**Recommendation:** Do not treat as fully independent tasks. Use one as an auxiliary supervision signal on a shared branch, or apply a shared 512-dim layer before both heads to prevent the model learning separate shortcuts for the same concept.

### 2. Strong Structural Cluster: `{Arch. Style, Bldg. Form, Roof Type}`

All three co-vary with V ≥ 0.521. A model predicting one of these is implicitly learning the others.

**Recommendation:** Replace three fully independent heads with a **shared task-group layer**:

```
Backbone → Global Pool (2048-dim)
  ├── Style Group (shared 512-dim layer)
  │     ├── Head: Architectural Style
  │     ├── Head: Building Form
  │     └── Head: Roof Type
  └── Independent Heads
        ├── Head: Stories
        ├── Head: Primary Cladding
        ├── Head: Setting
        ├── Head: Window
        └── Head: Entrance
```

### 3. Roof Type is a Hub Field

`Roof Type` has moderate-to-strong associations with four other fields (V=0.314–0.725). It acts as a bridge between the style cluster and the independent fields. Consider routing Roof Type through the shared style-group layer rather than an independent head.

### 4. Alteration Labels are Internally Consistent

- Level "5 - Not Altered" → only 2.4% of sub-fields show an alteration present ✅
- Level "4 - Minor Alterations" → 10% sub-fields altered ✅
- The ordinal alteration hierarchy is clean — no label inconsistency detected.

### 5. Brick Dominates Both Styles (~80% of dataset)

Brick is the dominant cladding for both Craftsman and Ranch styles. This creates **class imbalance** for `Primary Cladding`. Weighted loss or focal loss will be needed for minority classes (Stucco, Aluminum siding, Asbestos shingles).

### 6. Setting is Structurally Independent

`Setting` has V < 0.28 against all other fields. It captures spatial/urban context (corner lot, set-back, etc.) rather than architectural form. It should remain a fully independent head and may benefit from a **separate spatial feature pathway** at inference (e.g., attention to surrounding area rather than building facade).

---

## Recommended Architecture Update

Current plan (`MULTI_TASK_STRATEGY.md`) uses flat independent heads. The dependency analysis supports this update:

```python
class MultiTaskArchitecturalClassifier(nn.Module):
    def __init__(self, backbone_name='resnet50', active_tasks=None):
        super().__init__()
        self.backbone, self.feature_dim = self._build_backbone(backbone_name)

        # Shared style-group layer (serves strongly correlated tasks)
        self.style_group_fc = nn.Sequential(
            nn.Linear(self.feature_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.3)
        )

        # Task heads
        self.task_heads = nn.ModuleDict({
            # Style group (routed through shared layer)
            'architectural_style': nn.Linear(512, 12),
            'building_form':       nn.Linear(512, 8),
            'roof_type':           nn.Linear(512, 8),   # hub field → style group

            # Independent heads (routed directly from backbone)
            'stories':           nn.Linear(self.feature_dim, 6),
            'primary_cladding':  nn.Linear(self.feature_dim, 7),
            'setting':           nn.Linear(self.feature_dim, 3),
            'window_type':       nn.Linear(self.feature_dim, 7),
            'entrance_type':     nn.Linear(self.feature_dim, 5),
        })

    def forward(self, x):
        features = self.backbone(x).flatten(1)

        # Style group branch
        style_features = self.style_group_fc(features)

        outputs = {}
        style_group_tasks = {'architectural_style', 'building_form', 'roof_type'}
        for task, head in self.task_heads.items():
            feat = style_features if task in style_group_tasks else features
            outputs[task] = head(feat)

        return outputs
```

---

## Next Steps

1. **Update `src/models/multi_task_classifier.py`** — add `style_group_fc` shared layer
2. **Update loss weights** — increase weight for `architectural_style` (primary target); apply focal loss for `primary_cladding` due to Brick dominance
3. **Window/Entrance label normalization** — parse composite strings to extract primary type before training
4. **Create `data/image_label_mapping_phase1.csv`** — map images to labels for Phase 1 training
