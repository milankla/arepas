# Multi-Task Learning Strategy for 25 Building Attributes

## Overview

Your project requires predicting **25 architectural attributes** from building photos. This is a complex multi-task learning problem that requires a staged approach.

---

## ✅ Field Feasibility Analysis

### **Tier 1: EASY (85-95% Accuracy Expected)**
Directly observable from single photo, clear visual features:

1. **Stories** - Count visible floors (1, 1.5, 2, 2.5, 3+)
2. **Roof Type** - Geometric pattern (Hip, Gable, Flat, Gambrel, Mansard) — multi-label, 19 schema atomics
3. **Primary Cladding** - Surface material (Brick, Wood, Stucco, Stone, Vinyl)
4. **Setting** - Spatial context: 6 schema atomics, multi-label (`Attached on 1 Side`, `Attached on 2 Sides`, `Corner`, `Flush at Sidewalk`, `Set at Back of Lot`, `Set Back from Sidewalk`)
5. **Chimney** - `chimney_present` (Yes/No, binary) active in Phase 1; `chimney_material` (7 atomics) and `chimney_features` (4 atomics) deferred to Phase 3 (< 330 positive buildings)
6. **Window** - Type and configuration (Double-hung, Casement, Bay, Fixed)
7. **Entrance** - Type and location (Full porch, Partial porch, Recessed)

**Training Priority:** START HERE - These tasks provide foundational visual features

---

### **Tier 2: MEDIUM (70-85% Accuracy Expected)**
Visible but require fine-grained feature detection:

8. **Architectural Style** - Craftsman, Colonial, Tudor, Ranch, etc. (PRIMARY TARGET)
9. **Building Form** - Bungalow, Ranch, Cape Cod, Two-Story
10. **Roof Features** - Brackets, Eaves, Dormers, Purlins, Rafter tails
11. **Roof Materials** - Asphalt shingles, Tile, Slate, Metal (texture-based)
12. **Additional Cladding** - Secondary materials (stucco accents, trim)
13. **Wall Features** - Belt courses, Quoins, Half-timbering, Bay windows
14. **Landscape Features** - Fences, Walkways, Planters, Retaining walls
15. **Associated Buildings** - Garage, Shed, Outbuildings (detection + classification)

**Training Priority:** PHASE 2 - Build on foundational features from Tier 1

---

### **Tier 3: HARD (50-70% Accuracy Expected)**
Require multiple views, context, or domain knowledge:

16. **Building Plan** - Rectangular, L-shape, T-shape (needs aerial view or multiple angles)
17. **Building Category** - Residential-Single, Multi-dwelling, Commercial (ambiguous from exterior)
18. **Current Use** - Actual usage (may require signage/context clues)
19. **Original Use** - Historical usage (requires historical knowledge)

**Training Priority:** PHASE 3 - May need multi-view aggregation

---

### **Tier 4: VERY HARD (30-50% Accuracy Expected)**
Require historical comparison or expert architectural knowledge:

20. **Alteration Level** - Scale 1-5 (requires knowing original design)
21. **Alterations-Additions** - Rear additions, wing additions
22. **Alterations-Entrances** - Modified vs. original doorways
23. **Alterations-Roof** - Re-roofed, dormers added
24. **Alterations-Cladding** - Re-sided, brick over wood
25. **Alterations-Windows** - Replaced vs. original windows

**Training Priority:** PHASE 4 - Requires expert labels, attention mechanisms

---

## 🎯 Progressive Training Strategy

### **Phase 1: Parallel Pipeline Development (Weeks 1-4)**
**Goal:** Build preprocessing pipeline (Track 1) while establishing baseline model (Track 2)

**Dataset:** `/data/` directory ONLY (style-based organization)
- 19 datasets organized by architectural style (Bungalows, Minimal Traditional)
- Centralized image folders: `Bungalows - Photos/`, `Minimal Traditional - Photos/`
- Controlled style distribution (2 main styles)
- **~500-1000 building images** (smaller scale for rapid iteration)

**Why Start with `/data/`:**
1. **Smaller dataset** → Faster iteration for both preprocessing and model development
2. **Style-organized** → Easier to validate preprocessing quality
3. **Cleaner data** → Reduced complexity for initial debugging
4. **Known structure** → Easier to validate image-label mapping

---

#### **Track 1: Image Preprocessing Pipeline (Parallel - Weeks 1-4)**
**Goal:** Build automated house detection + cropping system

**Approach: Mask R-CNN Instance Segmentation**

Using **Detectron2 Mask R-CNN** for building detection:
- Pre-trained on COCO dataset with instance segmentation
- Precise boundaries for building detection and cropping
- ~200-300ms per image
- Better handles complex scenes with multiple buildings
- Provides both bounding boxes and instance masks

**Why Mask R-CNN:**
- **Pros:** More accurate crops, precise segmentation boundaries, robust building detection
- **Cons:** Requires Detectron2 installation, more memory than lightweight detectors
- **Best for:** Architectural photography with varying building positions and complex scenes

**Pipeline Steps:**
```python
# Preprocessing Pipeline (Track 1)
1. Load raw image from /data/
2. Run Mask R-CNN to detect and segment building
3. Extract bounding box from instance mask
4. Crop image to building region (with 10% padding)
5. Resize to 512x512 (higher res for fine details)
5. Save cropped image to /data/preprocessed/
6. Generate metadata: {image_id, bbox_coords, confidence_score}
```

**Quality Control:**
- Manual review of 100 random crops
- Flag images where detection confidence < 0.7
- Fallback to center crop if no building detected

**Expected Output:**
- **Preprocessed dataset:** `/data/preprocessed/` folder
- **Metadata CSV:** Mapping original → cropped images
- **Quality report:** Detection success rate, avg confidence, failure cases
- **Deliverable:** Reusable preprocessing module for Phase 2

---

#### **Track 2: Baseline Pipeline + Tier 1 Training (Parallel - Weeks 1-4)**
**Goal:** Build end-to-end training pipeline on **original images** with **Tier 1 tasks ONLY**

**Task Scope:** **Tier 1 ONLY** (7 easy tasks)
- Stories, Roof Type, Primary Cladding, Setting, Chimney, Window, Entrance
- **NO Tier 2 yet** (defer architectural style to Phase 2)

**Why Tier 1 Only in Phase 1:**
1. **Simpler tasks** → Easier to debug pipeline issues
2. **Fast convergence** → Get working model in 2-3 days
3. **Architectural style needs better data** → Wait for cropped images + `/data2/`
4. **Focus on infrastructure** → Data loading, training loop, evaluation

**Images:** Use **original, unprocessed images** from `/data/`
- Standard preprocessing: Resize 224x224, normalize
- No crops yet (waiting for Track 1)

**Expected Results:**
- Tier 1 tasks: **85-90%** accuracy on original images
- **Deliverable:** Working end-to-end pipeline from raw data → trained model → evaluation
- **Ready for Phase 2:** Pipeline validated and ready for cropped images + harder tasks

**Phase 1 Architecture (Track 2):**
```python
Input: [Batch, 3, 224, 224] RGB images (ORIGINAL, not cropped)
  ↓
Backbone: ResNet50 (baseline)
  ↓
Shared Features: [Batchsch, 2048, 7, 7]
  ↓
Global Average Pooling: [Batch, 2048]
  ↓
Task Heads (7 Tier 1 heads ONLY):
  - stories: 6 classes
  - roof_type: 19 atomics       ← multi-label, BCEWithLogitsLoss
  - primary_cladding: 7 classes ← FocalLoss(γ=2.0)
  - chimney_present: 2 classes (No/Yes) ← FocalLoss(γ=2.0), ~90-96% No
  - setting: 6 atomics          ← multi-label, BCEWithLogitsLoss, FocalLoss(γ=2.0)
  - window_type: 7 classes
  - entrance_type: 5 classes

# Phase 3 stubs (loss_weight=0.0 until data volume warrants training):
#   chimney_material: 7 atomics (multi-label) — < 330 positive buildings
#   chimney_features: 4 atomics (multi-label) — < 330 positive buildings
```

**Model Flexibility (See Implementation section):**
- Swap backbones via config file: `model.backbone: resnet50 | efficientnet_b3 | vit_b_16`
- Compare accuracy across architectures
- All models output same feature dimension → reuse task heads

**Phase 1 Loss Function (Tier 1 Only):**
```python
# Phase 1: Weighted multi-task loss (Tier 1 tasks)
# Weights updated from attribute dependency analysis (docs/ATTRIBUTE_DEPENDENCY_ANALYSIS.md)
Total Loss = 0.15  * L_stories
           + 0.12  * L_roof_type          # reduced: style-group task (V=0.725 w/ building_form)
           + 0.10  * FL_primary_cladding  # FocalLoss(γ=2.0): ~80% Brick dominance
           + 0.08  * L_chimney
           + 0.08  * L_setting
           + 0.10  * L_window
           + 0.10  * L_entrance

# Phase 2 added (✅ DONE — 66.63% 7-task overall):
# + 0.35 * L_architectural_style  # PRIMARY TARGET — actual: 59.66% acc, 23.04% F1 (Gate B)
# + 0.12 * L_building_form        # V=0.923 overlap with arch_style — actual: 45.72% acc, 21.84% F1
#
# ⏳ DEFERRED to next data drop:
# + 0.05 * L_roof_features        # multi-label BCE — DEFERRED: only 10% of buildings labelled (max 21 per atomic)
# + 0.05 * L_wall_features        # multi-label BCE — DEFERRED: 85% coverage but deferring with roof_features

# Loss function selection per task:
#   FocalLoss(γ=2.0)    → primary_cladding  (class imbalance)
#   BCEWithLogitsLoss   → roof_type (multi-label, 19 atomics — Option B)
#   BCEWithLogitsLoss   → roof_features, wall_features  (multi-label, when eventually added)
#   CrossEntropyLoss    → all other tasks
```

---

### **Phase 2: Cropped Images + Tier 2 Tasks + Dataset Switch (Weeks 5-7)**
**Goal:** Scale to `/data2/`, use preprocessed images, add Tier 2 tasks (architectural style!)

**Major Changes (3 simultaneous upgrades):**

1. **Dataset Switch:** `/data/` → `/data2/`
   - Switch from 2 style categories to 8 diverse neighborhoods
   - **~2000-5000 buildings** (larger scale)
   - Mixed architectural styles per neighborhood (real-world distribution)

2. **Image Upgrade:** Original → Cropped/Preprocessed
   - Use Track 1 preprocessing pipeline on `/data2/` images
   - **512x512 cropped images** (vs 224x224 originals)
   - Buildings centered, background removed
   - **Expected improvement:** +5-10% accuracy on all tasks

3. **Task Expansion:** Tier 1 → Tier 1 + Tier 2
   - **Add 2 Tier 2 tasks:** Architectural Style, Building Form
   - **Total: 9 tasks** (7 from Phase 1 + 2 new)
   - **PRIMARY TARGET:** Architectural Style classification (12 classes)
   - **⏳ Deferred to next data drop:** Roof Features (only 10% of buildings labelled, max 21 per atomic — not trainable), Wall Features (85% coverage but deferring alongside Roof Features)

**Dataset:** `/data2/` directory (neighborhood-based organization)
- 8 datasets organized by Denver neighborhoods (Cole, Regis, Skyland, South City Park, Sunnyside, etc.)
- Co-located images: Each neighborhood folder has images + CSV
- **Preprocessed folder:** `/data2/preprocessed/` (output from Track 1 pipeline)
- **More diverse** architectural styles (mixed within neighborhoods)
- **Larger scale** → Better generalization

**Why This Combination Makes Sense:**
1. **Cropped images help architectural style** → Better building features visible
2. **More data helps architectural style** → More examples of rare styles (Tudor, Colonial)
3. **Leverage Phase 1 foundation** → Transfer learning from Tier 1 tasks
4. **Real-world distribution** → Buildings grouped geographically, not by style

**Training Strategy:**
- **Transfer Learning:** Load Phase 1 weights for Tier 1 tasks, add new Tier 2 heads
- **Two-stage training:**
  - Stage 1: Freeze Tier 1 heads, train Tier 2 heads only (5 epochs)
  - Stage 2: Fine-tune all tasks jointly (25 epochs)
- **Higher resolution:** 384x384 input (vs 224x224 in Phase 1)
- **Longer training:** 30 epochs total (more tasks + more data)
- **Learning rate warmup:** Gradual increase for first 3 epochs

**Deduplication:**
- Remove 148 overlapping buildings from `/data2/` training set
- Keep duplicates in validation for cross-dataset comparison

**Actual Results (Phase 2 ✅ DONE — 66.63% 7-task overall, epoch 11, early stopping):**
- **Tier 1 tasks (retained):** stories 72.13% / roof_type 54.52% / primary_cladding 59.41% / chimney_present 92.67% / setting 82.33% Jaccard
- **Tier 2 tasks (new):**
  - Architectural Style: **59.66%** acc, 23.04% F1 → **Gate B** (< 70%; image cropping recommended before Phase 3)
  - Building Form: **45.72%** acc, 21.84% F1
  - ~~Roof Features~~ — **DEFERRED**: only 75/759 buildings (10%) labelled; best atomic has 21 buildings
  - ~~Wall Features~~ — **DEFERRED**: 645/759 buildings (85%) labelled but deferring with roof_features until next data drop
- **Key metric:** Does model generalize to unseen neighborhoods?

**Validation Strategy:**
- Hold out 1-2 entire neighborhoods for validation (e.g., South City Park)
- Test if model predicts styles in neighborhoods it's never seen
- Compare performance: Phase 1 model vs Phase 2 model on same `/data/` test set

---

### **Phase 3: Advanced Tier 3 Tasks (Weeks 8-10) - OPTIONAL**
**Goal:** Add **Tier 3 tasks** if Phase 2 achieves >80% on Tier 1 and >75% on architectural style

**Dataset:** Continue with `/data2/` + preprocessed images (best setup from Phase 2)

**New Tasks (4 advanced tasks):**
- Building Plan (Rectangular, L-shape, T-shape, Irregular)
- Building Category (Residential-Single, Multi-family, Commercial, Mixed-use)
- Current Use (Residential, Commercial, Institutional, Vacant)
- Original Use (Historical usage - requires domain knowledge)

**Why These Are Harder:**
- **Building Plan:** Requires aerial view or multiple angles (not always available)
- **Building Category:** Ambiguous from single front photo (needs context clues)
- **Current/Original Use:** May require signage, historical records, neighborhood context

**Special Techniques Required:**

1. **Multi-View Aggregation:**
   - Each building has 3-8 photos from different angles
   - Ensemble predictions across views
   - **View Fusion:** Concatenate features from multiple images
   ```python
   # Multi-view ensemble
   building_features = [backbone(view) for view in building_views]
   fused_features = torch.cat(building_features, dim=1)  # Concatenate
   prediction = head(fused_features)  # Single prediction per building
   ```

2. **Historical Context Integration:**
   - For "Original Use": Add neighborhood metadata (construction year, zoning history)
   - Embed contextual features alongside visual features
   - May require manual annotation by architectural historians

3. **Attention Mechanisms:**
   - Learn which photo angles are most informative for each task
   - Building Plan → prioritize side/corner views
   - Building Category → prioritize entrance/facade views

**Expected Results:**
- Building Plan: **60-70%** (limited by single-view photos)
- Building Category: **75-85%** (easier with context clues)
- Current Use: **65-75%** (signage helps)
- Original Use: **50-65%** (very hard without historical knowledge)

**Success Criteria:**
- If Phase 3 accuracy < 60% → Consider these tasks **too hard for computer vision alone**
- May need hybrid approach: CV model + knowledge base lookup

---

### **Phase 4: Alteration Detection (Weeks 9-10) - RESEARCH PHASE**
**Goal:** Experimental - Tackle **HARDEST TASKS**

**New Tasks:** Alteration Level, Alterations-Windows, Alterations-Roof, Alterations-Cladding

**Why This Is Hard:**
- Requires knowing **original design** (historical knowledge)
- Need to compare current photo to **idealized historical prototype**
- Subtle changes (e.g., replacing wood windows with vinyl)

**Special Training Approaches:**

1. **Contrastive Learning:**
   - Train on pairs: (altered building, unaltered similar building)
   - Learn to detect deviations from historical norms

2. **Attention Mechanisms:**
   - Highlight altered regions (replaced windows, added siding)
   - Provide interpretability: "Alteration detected in window area"

3. **Expert Labels Required:**
   - Architectural historians to validate ground truth
   - May need to limit dataset to buildings with known history

**Expected Results:**
- Alteration Level accuracy: **50-60%** (very challenging)
- Binary alteration detection: **65-75%** (yes/no is easier than severity)

**Realistic Expectations:**
- Some alterations may be **impossible** to detect from single photo
- Consider this an **experimental phase** - useful insights even if accuracy is moderate

---

## 🏗️ Implementation Architecture

### **Flexible Multi-Task Model Structure**

```python
class MultiTaskArchitecturalClassifier(nn.Module):
    """
    Flexible multi-task network with swappable backbones
    
    Supports:
    - ResNet50 (2048-dim features)
    - EfficientNet-B3 (1536-dim features)
    - ViT-B/16 (768-dim features)
    """
    
    def __init__(self, backbone_name: str = 'resnet50', active_tasks: list = None):
        super().__init__()
        
        # Build backbone based on config
        self.backbone, self.feature_dim = self._build_backbone(backbone_name)
        self.backbone_name = backbone_name
        
        # Shared style-group layer for co-dependent tasks (Cramér's V ≥ 0.5).
        # architectural_style ↔ building_form (V=0.923)
        # building_form       ↔ roof_type     (V=0.725)
        # architectural_style ↔ roof_type     (V=0.521)
        # See docs/ATTRIBUTE_DEPENDENCY_ANALYSIS.md
        self.style_group_fc = nn.Sequential(
            nn.Linear(self.feature_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.3)
        )
        
        # Task-specific heads
        self.task_heads = self._build_heads(self.feature_dim, active_tasks)
    
    def _build_backbone(self, name: str):
        """
        Factory method for backbone selection
        Returns: (backbone_module, feature_dimension)
        """
        if name == 'resnet50':
            backbone = models.resnet50(pretrained=True)
            # Remove final FC layer
            backbone = nn.Sequential(*list(backbone.children())[:-1])
            return backbone, 2048
        
        elif name == 'efficientnet_b3':
            from timm import create_model
            backbone = create_model('efficientnet_b3', pretrained=True, num_classes=0)
            return backbone, 1536
        
        elif name == 'vit_b_16':
            from timm import create_model
            backbone = create_model('vit_base_patch16_224', pretrained=True, num_classes=0)
            return backbone, 768
        
        else:
            raise ValueError(f"Unknown backbone: {name}")
    
    def _build_heads(self, feature_dim: int, active_tasks: list = None):
        """
        Build task-specific prediction heads
        All heads use same feature dimension from backbone
        """
        # Default: Phase 1 + Phase 2 tasks
        if active_tasks is None:
            active_tasks = [
                'stories', 'roof_type', 'primary_cladding', 'chimney',
                'setting', 'window_type', 'entrance_type',
                'architectural_style', 'building_form',
                'roof_features', 'wall_features'
            ]
        
        # Style-group tasks route through style_group_fc (512-dim).
        # Independent tasks receive backbone features directly (feature_dim).
        heads = {}
        
        # Tier 1: Easy single-label tasks (independent — bypass style_group_fc)
        if 'stories' in active_tasks:
            heads['stories'] = nn.Linear(feature_dim, 6)
        if 'roof_type' in active_tasks:
            heads['roof_type'] = nn.Linear(512, 19)          # style-group; multi-label 19 schema atomics (Option B)
        if 'primary_cladding' in active_tasks:
            heads['primary_cladding'] = nn.Linear(feature_dim, 7)
        if 'chimney' in active_tasks:
            heads['chimney'] = nn.Linear(feature_dim, 2)
        if 'setting' in active_tasks:
            heads['setting'] = nn.Linear(feature_dim, 3)
        if 'window_type' in active_tasks:
            heads['window_type'] = nn.Linear(feature_dim, 7)
        if 'entrance_type' in active_tasks:
            heads['entrance_type'] = nn.Linear(feature_dim, 5)
        
        # Tier 2: Architectural classification (PRIMARY TARGET) — style-group
        if 'architectural_style' in active_tasks:
            heads['architectural_style'] = nn.Linear(512, 12)  # style-group (V=0.923 w/ building_form)
        if 'building_form' in active_tasks:
            heads['building_form'] = nn.Linear(512, 8)         # style-group hub
        
        # Multi-label tasks (use sigmoid activation, not softmax)
        if 'roof_features' in active_tasks:
            heads['roof_features'] = nn.Linear(feature_dim, 8)
        if 'wall_features' in active_tasks:
            heads['wall_features'] = nn.Linear(feature_dim, 10)
        
        # Tier 3: Advanced tasks (Phase 3)
        if 'building_plan' in active_tasks:
            heads['building_plan'] = nn.Linear(feature_dim, 5)
        if 'building_category' in active_tasks:
            heads['building_category'] = nn.Linear(feature_dim, 4)
        
        # Tier 4: Alteration detection (Phase 4)
        if 'alteration_level' in active_tasks:
            heads['alteration_level'] = nn.Linear(feature_dim, 5)
        if 'alterations_windows' in active_tasks:
            heads['alterations_windows'] = nn.Linear(feature_dim, 2)
        
        return nn.ModuleDict(heads)
    
    def forward(self, x):
        # Extract shared features from backbone
        features = self.backbone(x)  # Shape depends on backbone
        
        # Flatten if needed (ResNet outputs [B, C, 1, 1])
        if features.dim() == 4:
            features = features.flatten(1)  # [B, feature_dim]
        
        # Style-group branch — shared 512-dim projection for co-dependent tasks
        style_features = self.style_group_fc(features)
        
        # Route each task: style-group → style_features, others → raw features
        STYLE_GROUP = {'architectural_style', 'building_form', 'roof_type'}
        outputs = {}
        for task_name, head in self.task_heads.items():
            feat = style_features if task_name in STYLE_GROUP else features
            outputs[task_name] = head(feat)
        
        return outputs
```

### **Configuration-Driven Training**

```yaml
# config/model_config.yaml

# Phase 1: /data/ dataset
phase1:
  dataset:
    data_dir: "data/"
    config_file: "config/data.json"
  
  model:
    backbone: "resnet50"  # Options: resnet50, efficientnet_b3, vit_b_16
    active_tasks:
      - stories
      - roof_type
      - primary_cladding
      - chimney
      - setting
      - window_type
      - entrance_type
      - architectural_style
      - building_form
      - roof_features
      - wall_features
  
  training:
    batch_size: 32
    epochs: 30
    learning_rate: 0.001
    weight_decay: 0.0001

# Phase 2: /data2/ dataset
phase2:
  dataset:
    data_dir: "data2/"
    config_file: "config/data2.json"
    load_phase1_weights: true
  
  model:
    backbone: "resnet50"  # Keep same or try different
    active_tasks: [same as phase1]
  
  training:
    batch_size: 32
    epochs: 40  # More data = more epochs
    learning_rate: 0.0005  # Lower LR for fine-tuning
    weight_decay: 0.0001

# Model comparison experiments
experiments:
  - name: "resnet50_baseline"
    backbone: "resnet50"
  - name: "efficientnet_comparison"
    backbone: "efficientnet_b3"
  - name: "vit_comparison"
    backbone: "vit_b_16"
```

### **Training Script with Model Comparison**

```python
# src/models/train_multi_task.py

import yaml
from pathlib import Path

def train(config_path: str, experiment_name: str = None):
    # Load configuration
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # Select experiment (for model comparison)
    if experiment_name:
        exp_config = next(e for e in config['experiments'] if e['name'] == experiment_name)
        config['model']['backbone'] = exp_config['backbone']
    
    # Build model with specified backbone
    model = MultiTaskArchitecturalClassifier(
        backbone_name=config['model']['backbone'],
        active_tasks=config['model']['active_tasks']
    )
    
    # Load data from specified directory
    dataset = ArchitecturalDataset(
        data_dir=config['dataset']['data_dir'],
        config_file=config['dataset']['config_file']
    )
    
    # Train and log results
    results = trainer.train(model, dataset, config['training'])
    
    # Save results for comparison
    save_results(experiment_name, config['model']['backbone'], results)

# Compare models
if __name__ == '__main__':
    # Phase 1: Train baseline on /data/
    train('config/model_config.yaml', experiment_name='resnet50_baseline')
    
    # Compare different backbones
    train('config/model_config.yaml', experiment_name='efficientnet_comparison')
    train('config/model_config.yaml', experiment_name='vit_comparison')
    
    # Generate comparison report
    compare_models(['resnet50_baseline', 'efficientnet_comparison', 'vit_comparison'])
```

---

## 📊 Data Requirements

### **Image Requirements:**
- **Minimum per task:** 500 labeled examples (for rare classes)
- **Ideal per task:** 1000+ labeled examples
- **Image quality:** 224x224 minimum, 512x512 recommended
- **Multiple angles:** 3-8 photos per building (ensemble at inference)

### **Label Quality:**
- **Tier 1-2 tasks:** Can use existing survey data (already labeled)
- **Tier 3 tasks:** May need manual verification
- **Tier 4 tasks:** **REQUIRE expert architectural historian labels**

### **Current Data Status:**

**Phase 1 Dataset (`/data/`):**
- ✅ **Images:** Centralized by style (Bungalows - Photos, Minimal Traditional - Photos)
- ✅ **Tabular labels:** 19 CSV files (style-based organization)
- ✅ **Schema:** 80 fields total
- ✅ **Advantages:** 
  - Smaller, manageable size for pipeline development
  - Style-organized (easier to validate preprocessing quality)
  - Known structure (easier debugging)
- ⚠️ **Image-label alignment:** Need to create mapping via `smithsonianNumber`
- 🔄 **Preprocessing (Track 1):** Will generate `/data/preprocessed/` folder with cropped images

**Phase 2 Dataset (`/data2/`):**
- ✅ **Images:** Co-located with CSVs in each neighborhood folder
- ✅ **Tabular labels:** 8 CSV files (neighborhood-based organization)
- ✅ **Schema:** Same 80 fields (different column order)
- ✅ **Advantages:**
  - Larger dataset (more buildings)
  - Real-world distribution (mixed styles per neighborhood)
  - Geographic organization (test generalization)
- ⚠️ **Deduplication needed:** 148 buildings overlap with `/data/` (identified via `smithsonianNumber`)
- ⚠️ **Image-label alignment:** Need configurable loader to handle both organizations

**Cross-Phase Considerations:**
- 🔄 **Deduplication strategy:** Remove overlapping buildings from Phase 2 training (keep in validation)
- 🔄 **Schema normalization:** Existing `configurable_loader.py` handles both column orders
- ❌ **Alteration labels:** May need expert annotation for Phase 4 tasks (both datasets)

---

## 🎯 Evaluation Metrics

### **Per-Task Metrics:**

**Single-Label Tasks (Most tasks):**
- **Accuracy:** Percentage of correct predictions
- **Precision/Recall:** Per-class performance
- **Confusion Matrix:** Where does model confuse classes?

**Multi-Label Tasks (Roof Features, Wall Features):**
- **Hamming Loss:** Average per-label error rate
- **Subset Accuracy:** Exact match of all labels
- **F1 Score (Macro/Micro):** Balanced performance across labels

**Regression-Style Tasks (Alteration Level):**
- **Mean Absolute Error (MAE):** Average deviation from true level
- **Ordinal Classification:** Treat 1-5 scale as ordinal

### **Overall System Metrics:**

1. **Average Task Accuracy:** Mean across all active tasks
2. **Weighted Task Accuracy:** Weight by task importance (style = 2x, easy tasks = 1x)
3. **Per-Phase Accuracy:** Track improvement as phases progress

---

## 🚀 Next Steps

### **Phase 1: Parallel Pipeline Development (Weeks 1-4)**

---

#### **Track 1: Image Preprocessing Pipeline — ✅ COMPLETE**

**Approach: GroundingDINO** (`IDEA-Research/grounding-dino-tiny` via `transformers`)

Text prompt: `"building. house. facade."` — box threshold 0.25, text threshold 0.20.

**Scoring function** per candidate box:
```
score = confidence × squareness × centrality
squareness  = min(w,h) / max(w,h)          # prefer tight, non-elongated boxes
centrality  = 1 − 2 × |cx/W − 0.5|        # prefer boxes centred horizontally
```
`min_area_ratio=0.03`, `max_area_ratio=0.99`, `padding_ratio=0.05`.

**Output**: 456×456 square crops with ImageNet-mean letterboxing `(124, 116, 104)` when
the padded bbox cannot be squared with real pixels alone.

**Fallback**: geometric centre-crop when no box passes the confidence threshold.

**Results on `data2/` (2,708 images across 759 buildings)**:
- Detected: 2,607 / 2,708 (96.3%)
- Geometric fallback: 1
- Errors: 0
- Output manifest: `crops/data2/crop_manifest.csv`

**Run the crop pipeline**:
```bash
python scripts/crop_dataset.py \
  --csv data2/image_label_mapping_phase1.csv \
  --out crops/data2 \
  --manifest crops/data2/crop_manifest.csv
```

**Preview results**:
```bash
python scripts/preview_crops.py \
  --manifest crops/data2/crop_manifest.csv \
  --out-root crops/data2 --port 8000
```

**Key source files**:
- `src/image_preprocessing/grounding_dino_detector.py` — detector + crop logic
- `src/image_preprocessing/detector_base.py` — `BaseDetector` ABC
- `scripts/crop_dataset.py` — CLI driver (resume-safe)
- `scripts/preview_crops.py` — HTML preview server

---

#### **Track 2: Baseline Pipeline + Tier 1 Training (Weeks 1-4)**

**Week 1: Data Infrastructure**

1. ⏳ **Data Mapping Script (Phase 1 Dataset)**
   ```bash
   python scripts/create_image_label_mapping.py \
     --data-dir data/ \
     --config config/data.json \
     --output data/image_label_mapping_phase1.csv
   ```
   - **Purpose**: Map images to labels for `/data/` directory ONLY
   - **Data sources**: 19 style-based datasets (Bungalows, Minimal Traditional)
   - **Configuration**: Uses `config/data.json`
   - **Key steps**:
     1. Load datasets using `configurable_loader.py`
     2. Match images in `Bungalows - Photos/` and `Minimal Traditional - Photos/`
     3. Extract smithsonianNumber from filenames
     4. Create one row per image with **Tier 1 task labels only**
   - **Output**: `data/image_label_mapping_phase1.csv`
   - **Columns**: `image_path, smithsonian_number, stories, roof_type, primary_cladding, chimney, setting, window_type, entrance_type`

2. ⏳ **Class Distribution Analysis**
   ```bash
   python scripts/analyze_dataset.py \
     --mapping data/image_label_mapping_phase1.csv \
     --tasks stories roof_type primary_cladding chimney setting window_type entrance_type
   ```
   - Count examples per class for **7 Tier 1 tasks**
   - Identify class imbalance (may need weighted loss)
   - Verify all images are accessible
   - Generate visualizations (class distribution bar charts)

3. ⏳ **PyTorch Dataset Class**
   ```python
   # src/loader/architectural_dataset.py
   
   class ArchitecturalBuildingDataset(Dataset):
       def __init__(self, csv_path, active_tasks=None, transform=None):
           self.df = pd.read_csv(csv_path)
           self.active_tasks = active_tasks or [
               'stories', 'roof_type', 'primary_cladding', 'chimney',
               'setting', 'window_type', 'entrance_type'
           ]
           self.transform = transform or self._default_transform()
       
       def _default_transform(self):
           return transforms.Compose([
               transforms.Resize(256),
               transforms.CenterCrop(224),
               transforms.ToTensor(),
               transforms.Normalize(
                   mean=[0.485, 0.456, 0.406],
                   std=[0.229, 0.224, 0.225]
               )
           ])
       
       def __getitem__(self, idx):
           row = self.df.iloc[idx]
           
           # Load image
           image = Image.open(row['image_path']).convert('RGB')
           image = self.transform(image)
           
           # Load labels for active tasks
           labels = {task: row[task] for task in self.active_tasks}
           
           return image, labels
   ```

**Week 2: Baseline Model Training**

4. ⏳ **Train Baseline (ResNet50, Tier 1 Only)**
   ```bash
   python src/models/train_multi_task.py \
     --config config/model_config_phase1.yaml \
     --data data/image_label_mapping_phase1.csv \
     --tasks stories roof_type primary_cladding chimney setting window_type entrance_type \
     --backbone resnet50 \
     --epochs 30 \
     --batch-size 32
   ```
   - Train on **7 Tier 1 tasks ONLY**
   - Use **original images** (224x224)
   - Monitor convergence for each task
   - Save checkpoints every 5 epochs
   - **Expected:** 85-90% accuracy on Tier 1 tasks

5. ⏳ **Evaluate Baseline**
   ```bash
   python src/models/evaluate.py \
     --checkpoint outputs/phase1_baseline/best_model.pth \
     --data data/image_label_mapping_phase1.csv \
     --tasks stories roof_type primary_cladding chimney setting window_type entrance_type
   ```
   - Generate per-task accuracy reports
   - Create confusion matrices for each task
   - Analyze failure cases
   - **Deliverable:** Baseline performance report

**Week 3-4: Pipeline Validation**

6. ⏳ **Test Data Loading Pipeline**
   - Verify image-label alignment (spot check 50 random images)
   - Test data augmentation (rotation, flip, color jitter)
   - Validate class encodings match labels

7. ⏳ **Prepare for Phase 2**
   - **Deliverable:** Validated training pipeline ready for:
     1. Cropped images (from Track 1)
     2. Larger `/data2/` dataset
     3. Additional Tier 2 tasks

### **Phase 2: Scale to `/data2/` + Cropped Images + Tier 2 (Weeks 5-7)**

**Week 5: Data Migration**

8. ⏳ **Map Phase 2 Dataset**
   ```bash
   python scripts/create_image_label_mapping.py \
     --data-dir data2/preprocessed/ \
     --config config/data2.json \
     --output data2/image_label_mapping_phase2.csv \
     --tasks all  # Include Tier 1 + Tier 2 tasks
   ```
   - Map `/data2/` neighborhood-based organization
   - Use **preprocessed/cropped images** from Track 1
   - Include **all 11 tasks** (Tier 1 + Tier 2)
   - Output: `data2/image_label_mapping_phase2.csv`

9. ⏳ **Deduplicate Across Phases**
   ```bash
   python scripts/deduplicate_datasets.py \
     --phase1 data/image_label_mapping_phase1.csv \
     --phase2 data2/image_label_mapping_phase2.csv \
     --output data2/image_label_mapping_phase2_clean.csv
   ```
   - Remove 148 overlapping buildings from Phase 2 training set
   - Keep duplicates in validation for cross-dataset comparison

**Week 6-7: Transfer Learning + Tier 2**

10. ✅ **Fine-tune on `/data2/` with Tier 2 Tasks** *(DONE — Phase 2 complete)*
    ```bash
    # Stage 1: Warmup (5 epochs, Tier 2 heads only)
    python -m src.models.train_multi_task \
      --csv data2/image_label_mapping_phase1.csv \
      --model-config config/models/efficientnet_b5.json \
      --start-phase 2 --end-phase 2 \
      --load-checkpoint outputs/data2/b5/v7_bs16/phase1/best_model_phase1.pth \
      --freeze-phase1-heads \
      --epochs 5 --batch-size 16 --lr 3.0e-4 --weight-decay 0.010 \
      --output-dir ./outputs/data2/b5/phase2_warmup

    # Stage 2: Joint fine-tune (early stopping at epoch 11)
    python -m src.models.train_multi_task \
      --csv data2/image_label_mapping_phase1.csv \
      --model-config config/models/efficientnet_b5.json \
      --start-phase 2 --end-phase 2 \
      --load-checkpoint outputs/data2/b5/phase2_warmup/phase2/best_model_by_acc_phase2.pth \
      --epochs 25 --batch-size 16 --lr 1.5e-4 --weight-decay 0.010 \
      --early-stopping-patience 10 \
      --output-dir ./outputs/data2/b5/phase2_full
    ```
    - **Note:** Used `image_label_mapping_phase1.csv` — `architectural_style` and `building_form` columns were already present
    - **Tasks trained:** `architectural_style`, `building_form` (+ 5 retained Phase 1 tasks) = 7 total
    - **roof_features / wall_features NOT included** — deferred to next data drop
    - **Add new Tier 2 heads** (architectural_style, building_form)

11. ⏳ **Cross-Dataset Validation**
    ```bash
    python src/models/evaluate.py \
      --checkpoint outputs/phase2_full/best_model.pth \
      --test-datasets data/image_label_mapping_phase1.csv data2/image_label_mapping_phase2_clean.csv \
      --compare-phases
    ```
    - Evaluate Phase 2 model on both `/data/` and `/data2/`
    - Test generalization to held-out neighborhoods (e.g., South City Park)
    - Compare: Phase 1 model vs Phase 2 model on same test set
    - **Key metrics:**
      - Tier 1 accuracy improvement (original → cropped images)
      - Tier 2 (architectural style) accuracy on diverse neighborhoods
      - Generalization to unseen neighborhoods

---

## ⚠️ Key Considerations

### **1. Label Quality is Critical**

**Problem:** If ground truth labels are incorrect, model will learn wrong patterns

**Solution:**
- Sample 50-100 buildings for **manual expert validation**
- Cross-reference multiple data sources
- Flag low-confidence predictions for human review

### **2. Multi-View Aggregation**

**Problem:** Each building has 3-8 photos (different angles)

**Options:**
- **Option A:** Use all images independently (data augmentation)
- **Option B:** Ensemble predictions at inference (vote across views)
- **Option C:** Multi-view fusion in model architecture

**Recommendation:** Start with Option A (simpler), move to Option B if needed

### **3. Class Imbalance**

**Problem:** Some classes may be rare (e.g., "Mansard roof" vs. "Gable roof")

**Solutions:**
- **Weighted Loss:** Give higher weight to rare classes
- **Focal Loss:** Focus learning on hard examples
- **Data Augmentation:** Oversample rare classes
- **Stratified Sampling:** Ensure validation set has all classes

#### **Standardized Imbalance Policy (Current Default)**

To avoid over-correcting minority classes, use **capped inverse-frequency class weights** with a hard cap:

- **Default cap:** `max=3.0` for single-label tasks
- Compute weights on the **training split only** (never val/test)
- Combine with focal loss only for tasks with severe skew

This is now the preferred default because runs with larger caps (e.g. 10.0 and 5.0) increased minority F1 but caused larger drops in overall accuracy and higher validation loss. `max=3.0` provided the best balance so far.

#### **Where to Apply It**

Apply capped class weights (`max=3.0`) to **single-label** attributes with imbalance, for example:
- `stories`
- `primary_cladding`
- `architectural_style`
- `building_form`
- `alteration_level` (after class coarsening if needed)

Do **not** apply this exact class-weight path directly to **multi-label** tasks (`roof_type`, `roof_features`, `wall_features`, etc.). For multi-label tasks, use `BCEWithLogitsLoss(pos_weight=...)` per label instead.

#### **Decision Rule Before Enabling Weights on a Task**

1. Check class histogram and tail sizes.
2. Coarsen classes if multiple labels are too rare to learn.
3. Start with cap `max=3.0`.
4. Evaluate using **macro-F1 + per-class recall + overall accuracy + val loss**.
5. Keep weighting only if minority recall improves without unacceptable accuracy/regression tradeoff.

### **4. Attribute Co-dependence (Data-Driven Finding)**

**Source:** Full Cramér's V matrix in [docs/ATTRIBUTE_DEPENDENCY_ANALYSIS.md](ATTRIBUTE_DEPENDENCY_ANALYSIS.md)

**Key findings from `scripts/attribute_dependency_analysis.py` on 198 Phase 1 buildings:**

| Pair | Cramér's V | Implication |
|------|-----------|-------------|
| Architectural Style ↔ Building Form | **0.923** | Near-redundant — label leakage risk |
| Building Form ↔ Roof Type | **0.725** | Strong structural cluster |
| Architectural Style ↔ Roof Type | **0.521** | Same cluster |
| Roof Type ↔ Primary Cladding | 0.408 | Moderate — Roof Type is a hub field |
| Building Form ↔ Stories | 0.330 | Moderate |
| Setting ↔ (all others) | < 0.28 | Fully independent — spatial context |

**Architecture impact:** `architectural_style`, `building_form`, and `roof_type` share a single `style_group_fc` (512-dim) layer before their heads. All other tasks receive backbone features directly.

**Label leakage warning:** `Building Form` and `Architectural Style` are near-interchangeable in this dataset. Do not train them as fully independent tasks or the model will learn separate shortcuts for the same underlying concept.

**Class imbalance warning:** Primary Cladding is ~80% Brick across both styles. Use **focal loss or class-weighted cross-entropy** to prevent the minority cladding classes (Stucco, Asbestos shingles, Aluminum siding) being ignored during training.

---

### **5. Interpretability**

**Why Important:** Architectural experts need to **trust** the model

**Approaches:**
- **Attention Maps:** Visualize which regions model focuses on
- **Feature Attribution:** Which attributes drive style prediction?
- **Error Analysis:** When model fails, understand why

---

### **6. Phase 1 Data Edge Cases (Discovered During Implementation)**

The following were found when building `data/image_label_mapping_phase1.csv` and `src/loader/architectural_dataset.py`. Must be resolved before wiring the dataset to the trainer.

**6a. `alteration_level` — extreme class imbalance (99% majority)**
- Phase 1 dataset: 631/638 rows are `5 - Not Altered`, only 7 are `4 - Minor Alterations`
- A model that always predicts the majority class would score 99% accuracy with zero learning
- **Fix before training:** Use `FocalLoss(γ=2.0)` (already defined in `multi_task_classifier.py`) or pass `class_weight` to `CrossEntropyLoss`
- **Long-term:** Phase 4 alteration tasks need expert-labelled examples across all 5 alteration levels

**6b. `roof_type` — multi-label over 19 schema atomics (Option B) ✅ IMPLEMENTED**

The Discover Denver schema defines `roof_type` as type `multi` — surveyors intentionally select multiple atomics joined by `"; "` (e.g. `"Hipped; Front Gable"`). Treating compound strings as atomic single-label classes (Option A) would create 40 classes in `data2/`, of which 21/27 compound classes have <10 examples and are effectively unlearnable.

**Decision: Option B — 19 independent binary classifiers with `BCEWithLogitsLoss`.**

**Implementation (commit `978f890`):**
- `src/loader/architectural_dataset.py`: `MultiLabelBinarizer(classes=ROOF_TYPE_SCHEMA_ATOMICS)` fitted with fixed class order; `__getitem__` returns `FloatTensor[19]` for `roof_type`, `LongTensor` for all other fields
- `src/models/multi_task_classifier.py`: `TaskConfig.EASY_TASKS['roof_type']` → `num_classes=19`, `multi_label=True`; `MultiTaskLoss` already dispatches to `BCEWithLogitsLoss` for `multi_label=True` tasks

**`data2/` atomic label frequency analysis (n=2708 rows, 762 buildings):**

| Atomic | Positive examples | % buildings | Signal |
|---|---|---|---|
| Hipped | 928 | 34.3% | ✅ strong |
| Front Gable | 596 | 22.0% | ✅ strong |
| Cross Gable | 407 | 15.0% | ✅ strong |
| Flat | 395 | 14.6% | ✅ strong |
| Side Gable | 373 | 13.8% | ✅ strong |
| Compound Roof | 97 | 3.6% | ⚠️ weak |
| Hip-on-Gable | 81 | 3.0% | ⚠️ weak |
| Cross Hip-on-Gable | 44 | 1.6% | ⚠️ weak |
| Shed | 25 | 0.9% | ⚠️ weak |
| Pyramidal | 18 | 0.7% | ⚠️ rare |
| Dutch Hipped | 17 | 0.6% | ⚠️ rare |
| Mansard | 15 | 0.6% | ⚠️ rare |
| Gambrel | 9 | 0.3% | ⚠️ rare |
| Other | 3 | 0.1% | ⚠️ rare |
| Unknown Roof Type | 1 | 0.04% | ⚠️ rare |
| Barrel Roof | 0 | — | ❌ never seen |
| Conical | 0 | — | ❌ never seen |
| Dome | 0 | — | ❌ never seen |
| Monitor | 0 | — | ❌ never seen |

**Key stats:** avg 1.11 labels/building; 8.4% of buildings have compound roof types; all compound strings decompose cleanly into schema atomics (no unrecognised parts).

**6c. `primary_cladding` — actual class count (10) doesn't match `TaskConfig` (7)**
- `TaskConfig.EASY_TASKS['primary_cladding']['num_classes'] = 7` is hardcoded with placeholder classes
- Phase 1 dataset has **10 real classes**: Brick, Concrete - Block, Shingles - Asbestos, Shingles - Plain, Shingles - Unknown, Siding - Aluminum, Siding - Horizontal (Unknown Material), Siding - Horizontal (Wood), Stone - Rusticated, Stucco - Historic
- The head `nn.Linear(feature_dim, 7)` will crash at training time with a 10-class label
- **Fix (Priority 5):** Update `TaskConfig` to use actual class lists from `ArchitecturalDataset.class_names` at runtime rather than hardcoded counts; or at minimum update the static counts/classes to match the real data

---

## 📈 Expected Timeline

| Phase | Duration | Focus | Dataset | Expected Accuracy | Status |
|-------|----------|-------|---------|-------------------|--------|
| **Setup** | 1 week | Pipeline infrastructure | N/A | N/A | ✅ Done |
| **Phase 1** | 3-4 weeks | Tier 1 tasks (5 active) | `data2/` | 80-85% avg | ✅ Done — 71.86% (B5 bs=16) |
| ↳ Data prep | 1 week | Image-label mapping (759 buildings) | `data2/` | N/A | ✅ Done |
| ↳ Tier 1 tasks | 2-3 weeks | stories, roof_type, cladding, chimney, setting | `data2/` | 85-90% | ✅ Done — actual ceiling ~72% |
| ↳ Model comparison | — | ResNet50 vs B5; grid search + batch scaling | `data2/` | Compare | ✅ Done — B5 bs=16 wins |
| **Phase 2** | 2-3 weeks | Tier 2 tasks (arch style, building form) | `data2/` | 60-75% new tasks | ✅ Done — 66.63% 7-task overall |
| ↳ CSV extension | 3 days | Parse Tier 2 cols from CLEAN.txt files | `data2/` | N/A | ✅ Done — cols already in phase1.csv |
| ↳ Two-stage training | 1-2 weeks | Stage 1: freeze heads; Stage 2: joint fine-tune | `data2/` | 60-75% | ✅ Done — warmup ep5 (56.33%) → full ep11 (66.63%) |
| ↳ Gate A/B decision | 1 day | arch_style ≥70%? → Phase 3 vs. preprocessing first | `data2/` | Evaluate | ✅ Gate B — arch_style=59.66% (<70%); image crop recommended |
| **Phase 3** | 2 weeks | Tier 3 tasks (building_plan, category, use) | `data2/` | 50-70% | ⏳ Future |
| **Phase 4** | 2 weeks | Alteration detection (RESEARCH) | Both | 50-65% | ⏳ Future |
| **Total** | **6-8 weeks** | **Core pipeline + 11 tasks** | **Both datasets** | **65-75% avg** | |

---

## 💡 Success Criteria

### **Minimum Viable Product (MVP):**
- Phase 1 complete: **85%+ on easy tasks**
- Phase 2 complete: **75%+ on architectural style**
- Production API: Batch classify 1000 buildings/hour

### **Full Success:**
- All 4 phases complete
- **80%+ average accuracy** across 25 tasks
- Interpretable predictions (attention maps, feature attribution)
- Deployment-ready REST API

### **Stretch Goals:**
- **Multi-city expansion:** Train on Denver + other cities
- **Temporal analysis:** Track architectural style evolution over time
- **Active learning:** Model requests labels for uncertain predictions

---

## 🤝 Committee Support Needed

### **1. Architectural Style Taxonomy**
- **Question:** Clear hierarchy of styles (which are sub-categories?)
- **Example:** Is "Craftsman" a type of "Bungalow"? Or separate?
- **Impact:** Affects label encoding and class definitions

### **2. Field Definitions**
- **Question:** What exactly is "Building Plan"? (Floor plan or footprint?)
- **Question:** How to distinguish "Original Use" from "Current Use"?
- **Impact:** Ensures model learns correct concepts

### **3. Ground Truth Validation**
- **Request:** Expert review of 50-100 sample buildings
- **Purpose:** Validate existing labels, establish gold standard
- **Timeline:** Before Phase 2 training (Week 3)

### **4. Alteration Labels**
- **Request:** Architectural historian to label alterations
- **Challenge:** Tier 4 tasks require historical comparison
- **Alternative:** Start with Phases 1-3, defer Phase 4 if too difficult

### **5. Success Threshold**
- **Question:** What accuracy is "good enough" for production?
  - 80% average? 90%? 95%?
- **Question:** Which tasks are **critical** vs. **nice-to-have**?
  - Is architectural style classification the #1 priority?

---

## � Empirical Training Learnings — Phase 1 on `data2/`

> **Status as of May 2026:** Phase 1 training (5 tasks: stories, roof_type, primary_cladding, chimney_present, setting) on `data2/` is complete. Best checkpoint: EfficientNet-B5 bs=16 at **71.86% overall** (b5/v7_bs16).

---

### What We Actually Achieved vs. Expectations

| Task | Tier 1 prediction | Actual best (B5 v7_bs16) | Gap | Verdict |
|------|------------------|--------------------------|-----|---------|
| chimney_present | 85–95% | **92.42%** | ✅ | Met |
| setting (Jaccard) | 85–95% | **80.81%** | ~5% below | Close |
| stories | 85–95% | **73.59%** | ~15% below | Harder than expected |
| primary_cladding | 85–95% | **59.66%** / F1 22.9% | ~30% below | Severely bottlenecked by class imbalance |
| roof_type (multi-label) | 85–95% | **52.81%** / F1 36.2% | ~35% below | Multi-label BCE is correct choice but task is harder than projected |

**Root cause for gaps:** `primary_cladding` is ~68% Brick in the training set — the model learns a near-Brick default. `roof_type` multi-label accuracy is artificially depressed because exact multi-label match is a strict criterion; Hamming accuracy is ~95%+ (per-label error is low). Stories is genuinely harder — 1.5-story and 2.5-story count distinctions are ambiguous from single photos.

---

### EfficientNet-B5 Batch Size Findings

The single biggest variable was **batch size**, not learning rate or weight decay.

| BS | Best LR | Best WD | Overall Acc | Notes |
|----|---------|---------|-------------|-------|
| 4 | 1e-4 | — | 69.45% | Likely overfit; no early stopping |
| 4 | 1e-4 | 0.01–0.03 | 60–61% | High WD killed minority-class learning |
| 8 | 1.0–1.1e-4 | 0.010 | 68.51–68.96% | Grid winner at bs=8; noisy gradients |
| **16** | **1.5e-4** | **0.010** | **71.86%** | New best; LR scaled by √2 per linear rule |

**Why B5 needs bs≥16:** EfficientNet-B5's stochastic depth and compound-scaled width amplify gradient variance. At bs=8, the noise floor prevents stable convergence — the model oscillates between plateaus. At bs=16 with LR scaled by √2, the effective gradient noise drops enough to use B5's extra capacity.

**Tested:** bs=32 (LR ~2.1e-4) — not yet run. Next candidate.

---

### Hyperparameter Sensitivity

- **Weight decay:** 0.010 is clearly better than 0.005 or 0.030 for B5 on this dataset. Low WD allows overfitting; high WD collapses minority-class prediction.
- **LR:** Grid searched 1.0–1.2e-4 at bs=8 — range is very flat (65–68%). The bigger gain came from fixing batch size, not LR tuning.
- **Early stopping:** Essential. Best epoch was 11/25 for b5/v7_bs16; without patience=10 the model would have continued degrading on val. ResNet50 v7 (no early stopping) converged cleanly at epoch 30 — B5 peaks earlier and decays faster.

---

### The Cladding Problem

**Summary:** 8-class coarsened cladding is the right scheme for now. The problem is data, not architecture or loss function.

- Brick = ~68% of training buildings. Even perfect focal loss cannot invent minority-class signal that isn't in the data.
- The coarsening (`CLADDING_COARSEN_MAP`, 30→8 classes) consolidates learnable groups. Reverting to 18-class raw (b5/v6) made things worse, not better.
- **Threshold for revisiting 18-class:** When any non-Brick class has ≥200 buildings in the training CSV (currently ~20–80 each).
- **Focal loss / class weighting:** Worth trying with `max=3.0` cap once the data ceiling is confirmed. Do not apply before ruling out data shortage as the primary cause.

---

### ResNet50 vs. B5 Comparison

| Model | Best overall | Stories | Roof | Cladding | Chimney | Setting |
|-------|-------------|---------|------|----------|---------|---------|
| ResNet50 v7 | 71.35% | 73.11% | 52.32% | 55.50% | 93.64% | 81.30% |
| **B5 v7_bs16** | **71.86%** | **73.59%** | **52.81%** | **59.66%** | 92.42% | 80.81% |
| Delta | +0.51% | +0.48% | +0.49% | **+4.16%** | −1.22% | −0.49% |

B5's only meaningful win is **cladding** (+4.2 pp accuracy). The extra model capacity appears to benefit fine-grained texture discrimination (which distinguishes brick from stucco from concrete). Chimney (binary) and setting (multi-label sparse) are effectively at ceiling — no architecture will improve them without more labeled diversity.

**Hypothesis for Phase 2:** B5's advantage will grow on style-based tasks (architectural_style, building_form, roof_features) where fine-grained shape + texture features matter more. ResNet50 should remain competitive on coarse binary tasks.

---

## 🗺️ Training Path Forward After Phase 1

### Immediate: Squeeze Phase 1 Further (Optional)

Before moving to Phase 2 tasks, two low-effort runs are worth attempting if time permits:

1. **B5 bs=32, LR=2.1e-4, WD=0.010** — test whether the bs scaling law continues. If ≥73%, B5 bs=32 becomes the preferred backbone config. If no gain, the bs=16 sweet spot is confirmed.
2. **Focal loss on cladding** — swap `CrossEntropyLoss` for `FocalLoss(γ=2.0)` with `max_weight=3.0` cap. Expected to raise cladding F1 from 22.9% without hurting overall acc. Only run this after confirming the training data count per class hasn't changed.

---

### Phase 2: Expand to Tier 2 Tasks ✅ DONE

**Result:** Two-stage training complete on `data2/image_label_mapping_phase1.csv` (columns were already present; no CSV extension needed).

**Tasks trained (7 total):** 5 retained Phase 1 tasks + `architectural_style` + `building_form`

**⏳ Deferred to next data drop:** `roof_features`, `wall_features`
- `roof_features`: only 75/759 buildings (10%) have any label; best atomic (`Eaves - Boxed`) has just 21 buildings — not trainable
- `wall_features`: 645/759 buildings (85%) labelled, 16 atomics ≥30 buildings — technically trainable, but deferring alongside `roof_features` until next data drop

**Actual results:**

| Task | Accuracy | F1 | Notes |
|------|----------|-----|-------|
| chimney_present | 92.67% | — | ✅ Strong |
| setting | 82.33% Jaccard | — | ✅ Strong |
| stories | 72.13% | — | ✅ Close to Phase 1 |
| primary_cladding | 59.41% | — | Class imbalance ceiling |
| roof_type | 54.52% | — | Multi-label BCE |
| architectural_style | 59.66% | 23.04% | **Gate B (<70%)** |
| building_form | 45.72% | 21.84% | Near-redundant with arch_style |
| **Overall (7-task)** | **66.63%** | — | **Epoch 11, early stopping** |

**Checkpoints:**
- `outputs/data2/b5/phase2_warmup/phase2/best_model_by_acc_phase2.pth` (56.33%, Stage 1 ep5)
- `outputs/data2/b5/phase2_full/phase2/best_model_phase2.pth` (66.63%, Stage 2 ep11) ← **current best**

**Gate B outcome:** arch_style=59.66% < 70% threshold. Recommended next step: image preprocessing (building detection + crop to bounding box at 456×456) before Phase 3. See Gate B block below.

---

### After Phase 2: Decision Gates

#### Gate A — If Phase 2 architectural_style ≥ 70%
Proceed to **Phase 3 tasks** (building_plan, building_category, original_use, current_use).

#### Gate B — If Phase 2 architectural_style < 70%
Investigate before advancing. Likely causes:
1. **Label noise** — `architectural_style` field has free-text entries; check for inconsistent labelling (e.g., "Bungalow" vs "Craftsman Bungalow")
2. **Insufficient style diversity** — data2 may skew heavily toward Bungalow/Minimal Traditional; model has no signal to distinguish rarer styles
3. **Image resolution limit** — style classification benefits from fine detail; consider image preprocessing (building detection + crop) before retraining

**If Gate B:** Run image preprocessing (Track 1 Mask R-CNN pipeline) on data2 photos, crop to building bounding box at 456×456 (B5's native resolution), retrain from Phase 1 checkpoint.

---

### Phase 3 Considerations (Informed by Phase 1 Results)

The strategy originally projected 60–70% for Tier 3 tasks. Based on Phase 1 outcomes, revise expectations:

- **building_plan** — now expected **45–60%** (single front photo rarely shows plan shape)
- **building_category** — **65–75%** (exterior appearance is informative; remains feasible)
- **original_use / current_use** — **50–65%** (depends heavily on signage / context clues in photos)

Multi-view aggregation (Option B: ensemble across 3–8 photos per building) is **strongly recommended** before declaring Phase 3 tasks infeasible. Buildings in data2 average ~3.6 photos. Averaging backbone features across views before the head should give a material boost on shape-dependent tasks like building_plan.

---

## �📚 References

**Multi-Task Learning:**
- "An Overview of Multi-Task Learning in Deep Neural Networks" (Ruder, 2017)
- "Taskonomy: Disentangling Task Transfer Learning" (Zamir et al., 2018)

**Architectural Classification:**
- "Large-scale Classification of Fine-Art Paintings" (Saleh & Elgammal, 2015)
- "Recognizing Architectural Style using Deep Learning" (Xu et al., 2017)

**Implementation:**
- PyTorch Multi-Task Tutorial: https://pytorch.org/tutorials/
- Timm (PyTorch Image Models): https://github.com/rwightman/pytorch-image-models

---

## ✅ Summary

**Your 25 fields make sense, but:**

1. **Prioritize by difficulty:** Start with easy visual tasks, progressively add harder ones
2. **Use multi-task learning:** Shared features improve performance on all tasks
3. **Set realistic expectations:** Some tasks (alterations) may only reach 50-60% accuracy
4. **Plan for 9 weeks:** Progressive training across 4 phases
5. **Get expert validation:** Especially for alteration detection

---

### ~~Current State (July 2026)~~ — SUPERSEDED

> **⚠️ The results below were produced on a corrupted dataset (building ID truncation bug, commit a0d8cc2). They trained on ~759/7,135 buildings (12% of actual data). Accuracy figures are inflated by the tiny validation set. These runs are archived in `mlruns_archived/` and are not valid baselines.**

~~**Phase 2 complete** on `data2/` (7 tasks). Best: **EfficientNet-B5 bs=16 → 66.63% overall** (phase2_full, ep11).~~

---

## 🔄 Post-Bugfix Strategy Reset — May 2026

### The Bug (commit a0d8cc2)

`build_phase1_label_mapping.py` applied a `[1:-1]` slice to building IDs when stripping quotes, corrupting `DIS.3554` → `IS.355`. This caused most cross-neighborhood joins to fail silently, yielding only 759 of 7,135 buildings.

**All runs in `mlruns_archived/` (ResNet50 v1–v7, B5 v1–v7_bs16) trained on 12% of the dataset. Their accuracy/F1 figures cannot be compared to post-fix runs.**

### First Valid Baselines (ResNet50, data2 corrected)

Both runs use `data2/image_label_mapping_phase1.csv` (7,135 buildings, 26,160 images) with ResNet50/224px, bs=32, lr as noted. Checkpoints in `outputs/data2/v1/`.

| Run | Tasks | Epochs | Best acc | Best epoch | Notes |
|-----|-------|--------|----------|------------|-------|
| v1/phase1 | 5 (stories, roof_type, primary_cladding, chimney_present, setting) | 30 | **72.14%** | 27 | No early stopping |
| v1/phase2 | 7 (+architectural_style, building_form) | 30 | **70.13%** | 29 | Loaded phase1 checkpoint, lr=5e-5 |

**Phase 2 per-task breakdown:**

| Task | Accuracy | Notes |
|------|----------|-------|
| chimney_present | 94.3% | ✅ At ceiling |
| setting (exact) | 75.1% | ✅ Strong |
| stories | 64.5% | Harder than expected |
| architectural_style | **71.5%** | ✅ **Gate A passed** (≥70%) |
| building_form | 63.3% | High Cramér's V with arch_style |
| primary_cladding | 57.9% | Class imbalance floor |
| roof_type | 54.9% | Multi-compound tail |

**Gate A outcome:** `architectural_style` = 71.5% ≥ 70% threshold. Phase 3 is unblocked. However, the relatively low per-task F1 on minority classes means targeted improvements are worthwhile before advancing.

---

### What Changed With 9.4× More Data

The bug fix revealed that prior strategy assumptions were wrong:

| Assumption (pre-fix, 759 buildings) | Reality (7,135 buildings) |
|--------------------------------------|--------------------------|
| `architectural_style` unlearnable — top class ≤40 buildings | Victorian Cottage 369, Edwardian 323 — clearly viable |
| `chimney_present`: Yes=18 — focal loss not justified | Yes=221 — focal loss feasible |
| Crop manifest (2,708 crops / 762 buildings) = full coverage | Crops cover only 10.4% of corrected dataset |
| `architectural_style` 37-class head is untrainable | 37 raw classes but 24 have <100 images → need coarsening |
| B5 batch size findings assumed stable gradient variance | Needs re-validation on 9.4× more data per epoch |

---

### Strategy Changes Applied (May 2026)

#### 1. `architectural_style` Coarsening (implemented in `src/loader/architectural_dataset.py`)

Added `normalize_arch_style_label()` to `PRE_ENCODE_TRANSFORMS`. Threshold: keep classes with ≥100 image-level examples; merge the rest into `"Other Style"`.

**Result: 37 raw classes → 14 coarsened classes.**

| Kept classes (≥100 images) | Merged into "Other Style" (<100 images) |
|------|------|
| No Clear Architectural Style (12,774), Craftsman (5,061), Ranch (2,763), Victorian Cottage (1,240), Edwardian (1,163), English Norman Cottage (762), Modern Movement (573), Classical Revival (291), Mixed Style (265), Queen Anne (252), Dutch Colonial Revival (195), Contemporary (157), Mission (114) | Tudor Revival (83), Mediterranean Revival (44), Art Deco (37), Colonial Revival (34), International Style (24), Other Style (23), Exotic Revival (22), Pueblo Revival (22), Rustic (19), Moderne (18), Romanesque Revival (16), Gothic Revival (16), Swiss Chalet (15), and 10 more → **"Other Style" (550 total)** |

#### 2. Crop Regeneration Required

The `crops/data2/crop_manifest.csv` was built from the broken loader and covers 762/7,135 buildings (10.4%). Must be rebuilt with:

```bash
python scripts/crop_dataset.py \
  --csv data2/image_label_mapping_phase1.csv \
  --out crops/data2 \
  --image-root . \
  --target-size 456 \
  --device mps
```

Crops output at 456×456 — native to EfficientNet-B5. This is a prerequisite for any crop-based training run.

---

### Planned v2 Training Runs

| Run | Backbone | Images | Changes vs v1 | Goal |
|-----|----------|--------|---------------|------|
| **v2a** | ResNet50/224px | Full (26,160) | + arch_style coarsening | Establish coarsening benefit vs v1 |
| **v2b** | EfficientNet-B5/456px | Full (26,160) | + coarsening, bs=16, lr=1.5e-4 | Backbone upgrade benefit |
| **v2c** | EfficientNet-B5/456px | Crops (after regen) | + coarsening, bs=16 | Crops + B5 combined |

Run v2a and v2b can start immediately (no crops needed). v2c requires the crop regeneration job to complete first.
