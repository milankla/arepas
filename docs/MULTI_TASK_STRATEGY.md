# Multi-Task Learning Strategy for 25 Building Attributes

## Overview

Your project requires predicting **25 architectural attributes** from building photos. This is a complex multi-task learning problem that requires a staged approach.

---

## ✅ Field Feasibility Analysis

### **Tier 1: EASY (85-95% Accuracy Expected)**
Directly observable from single photo, clear visual features:

1. **Stories** - Count visible floors (1, 1.5, 2, 2.5, 3+)
2. **Roof Type** - Geometric pattern (Hip, Gable, Flat, Gambrel, Mansard)
3. **Primary Cladding** - Surface material (Brick, Wood, Stucco, Stone, Vinyl)
4. **Setting** - Spatial context (Detached, Attached, Set back from sidewalk)
5. **Chimney** - Presence, location, material
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

**Approach Options:**
1. **YOLOv8 Object Detection**
   - Pre-trained on COCO dataset (includes "building" class)
   - Fast inference (~100-200ms per image)
   - Detects bounding box → crop → resize
   - **Pros:** Fast, easy to implement
   - **Cons:** May miss houses or include multiple buildings

2. **Detectron2 Instance Segmentation**
   - More precise boundaries than YOLO
   - ~200-300ms per image
   - Better for complex scenes with multiple buildings
   - **Pros:** More accurate crops
   - **Cons:** Slightly slower

3. **SAM (Segment Anything Model)**
   - State-of-the-art segmentation
   - ~500ms-1s per image
   - Most precise building boundaries
   - **Pros:** Best quality crops
   - **Cons:** Slowest, requires more GPU memory

**Recommended:** Start with **YOLOv8** (fastest), upgrade to Detectron2/SAM if needed

**Pipeline Steps:**
```python
# Preprocessing Pipeline (Track 1)
1. Load raw image from /data/
2. Run YOLOv8 to detect building bounding box
3. Crop image to building region (with 10% padding)
4. Resize to 512x512 (higher res for fine details)
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
Shared Features: [Batch, 2048, 7, 7]
  ↓
Global Average Pooling: [Batch, 2048]
  ↓
Task Heads (7 Tier 1 heads ONLY):
  - stories: 6 classes
  - roof_type: 8 classes
  - primary_cladding: 7 classes
  - chimney_present: 2 classes
  - setting: 3 classes
  - window_type: 7 classes
  - entrance_type: 5 classes

# NOTE: Tier 2 tasks deferred to Phase 2
# Will add architectural_style, building_form, roof_features, wall_features in Phase 2
```

**Model Flexibility (See Implementation section):**
- Swap backbones via config file: `model.backbone: resnet50 | efficientnet_b3 | vit_b_16`
- Compare accuracy across architectures
- All models output same feature dimension → reuse task heads

**Phase 1 Loss Function (Tier 1 Only):**
```python
# Weighted multi-task loss (7 tasks)
Total Loss = 0.15 * L_stories 
           + 0.15 * L_roof_type 
           + 0.15 * L_primary_cladding
           + 0.15 * L_chimney
           + 0.15 * L_setting
           + 0.125 * L_window
           + 0.125 * L_entrance

# Phase 2 will add:
# + 0.25 * L_architectural_style (PRIMARY TARGET)
# + 0.05 * L_building_form
# + 0.02 * L_roof_features (multi-label BCE)
# + 0.02 * L_wall_features (multi-label BCE)
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
   - **Add 4 Tier 2 tasks:** Architectural Style, Building Form, Roof Features, Wall Features
   - **Total: 11 tasks** (7 from Phase 1 + 4 new)
   - **PRIMARY TARGET:** Architectural Style classification (12 classes)

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

**Expected Results:**
- **Tier 1 tasks:** **90-95%** accuracy (improvement from cropped images)
- **Tier 2 tasks:**
  - Architectural Style: **75-85%** (PRIMARY TARGET)
  - Building Form: **80-90%**
  - Roof Features: **70-80%** (multi-label is harder)
  - Wall Features: **70-80%** (multi-label)
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
        
        heads = {}
        
        # Tier 1: Easy single-label tasks
        if 'stories' in active_tasks:
            heads['stories'] = nn.Linear(feature_dim, 6)
        if 'roof_type' in active_tasks:
            heads['roof_type'] = nn.Linear(feature_dim, 8)
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
        
        # Tier 2: Architectural classification (PRIMARY TARGET)
        if 'architectural_style' in active_tasks:
            heads['architectural_style'] = nn.Linear(feature_dim, 12)
        if 'building_form' in active_tasks:
            heads['building_form'] = nn.Linear(feature_dim, 8)
        
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
        
        # Task-specific predictions
        outputs = {}
        for task_name, head in self.task_heads.items():
            outputs[task_name] = head(features)
        
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

#### **Track 1: Image Preprocessing Pipeline (Weeks 1-4)**

**Week 1: Setup Object Detection**

1. ⏳ **Install YOLOv8**
   ```bash
   pip install ultralytics
   ```

2. ⏳ **Test YOLOv8 on Sample Images**
   ```bash
   python scripts/test_yolo_detection.py \
     --images data/Bungalows\ -\ Photos/ \
     --num-samples 10
   ```
   - Verify detection works on architectural photos
   - Check confidence scores (should be >0.7 for "building" class)
   - Visualize bounding boxes

3. ⏳ **Build Preprocessing Script**
   ```python
   # scripts/preprocess_images.py
   
   from ultralytics import YOLO
   import cv2
   from pathlib import Path
   
   def preprocess_image(image_path, output_dir, model):
       # Load image
       img = cv2.imread(str(image_path))
       
       # Detect building
       results = model(img)
       buildings = [r for r in results[0].boxes if r.cls == 'building']
       
       if len(buildings) > 0:
           # Get highest confidence building
           best_box = max(buildings, key=lambda x: x.conf)
           x1, y1, x2, y2 = best_box.xyxy[0].cpu().numpy()
           
           # Add 10% padding
           h, w = img.shape[:2]
           pad_x = int((x2 - x1) * 0.1)
           pad_y = int((y2 - y1) * 0.1)
           x1, y1 = max(0, x1-pad_x), max(0, y1-pad_y)
           x2, y2 = min(w, x2+pad_x), min(h, y2+pad_y)
           
           # Crop and resize
           cropped = img[int(y1):int(y2), int(x1):int(x2)]
           resized = cv2.resize(cropped, (512, 512))
           
           # Save
           output_path = output_dir / image_path.name
           cv2.imwrite(str(output_path), resized)
           
           return {
               'image_id': image_path.stem,
               'bbox': [x1, y1, x2, y2],
               'confidence': float(best_box.conf),
               'status': 'success'
           }
       else:
           # Fallback: center crop
           h, w = img.shape[:2]
           size = min(h, w)
           y1, x1 = (h-size)//2, (w-size)//2
           cropped = img[y1:y1+size, x1:x1+size]
           resized = cv2.resize(cropped, (512, 512))
           
           output_path = output_dir / image_path.name
           cv2.imwrite(str(output_path), resized)
           
           return {
               'image_id': image_path.stem,
               'bbox': None,
               'confidence': 0.0,
               'status': 'fallback_center_crop'
           }
   ```

**Week 2-3: Process All Images**

4. ⏳ **Preprocess `/data/` Images**
   ```bash
   python scripts/preprocess_images.py \
     --data-dir data/ \
     --output-dir data/preprocessed/ \
     --model yolov8m.pt
   ```
   - Process all images in `Bungalows - Photos/` and `Minimal Traditional - Photos/`
   - Save to `data/preprocessed/`
   - Generate metadata CSV with detection results

5. ⏳ **Quality Control Review**
   ```bash
   python scripts/review_crops.py \
     --original data/Bungalows\ -\ Photos/ \
     --cropped data/preprocessed/ \
     --num-samples 100
   ```
   - Manually review 100 random crops (side-by-side with originals)
   - Flag poor crops (confidence < 0.7 or bad framing)
   - Calculate success metrics:
     - Detection rate: % images with building detected
     - Avg confidence score
     - Fallback rate: % using center crop

**Week 4: Prepare for Phase 2**

6. ⏳ **Process `/data2/` Images**
   ```bash
   python scripts/preprocess_images.py \
     --data-dir data2/ \
     --output-dir data2/preprocessed/ \
     --model yolov8m.pt
   ```
   - Apply preprocessing to larger `/data2/` dataset
   - Generate `data2/preprocessed/` folder
   - Ready for Phase 2 training

7. ⏳ **Generate Preprocessing Report**
   ```bash
   python scripts/preprocessing_report.py \
     --metadata data/preprocessed/metadata.csv \
     --output reports/preprocessing_quality.pdf
   ```
   - Detection success rate by style category
   - Confidence score distribution
   - Example crops (good vs bad)
   - Recommendations for improvement

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

10. ⏳ **Fine-tune on `/data2/` with Tier 2 Tasks**
    ```bash
    python src/models/train_multi_task.py \
      --config config/model_config_phase2.yaml \
      --data data2/image_label_mapping_phase2_clean.csv \
      --load-weights outputs/phase1_baseline/best_model.pth \
      --tasks stories roof_type primary_cladding chimney setting window_type entrance_type \
              architectural_style building_form roof_features wall_features \
      --image-size 384 \
      --epochs 30 \
      --two-stage-training
    ```
    - Initialize Tier 1 heads with Phase 1 weights
    - Add new Tier 2 heads (architectural_style, building_form, roof_features, wall_features)
    - Two-stage training:
      - Stage 1: Freeze Tier 1, train Tier 2 only (5 epochs)
      - Stage 2: Fine-tune all tasks jointly (25 epochs)
    - Use **cropped 384x384 images** (higher resolution)
    - Lower learning rate (0.0005) for fine-tuning

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

### **4. Interpretability**

**Why Important:** Architectural experts need to **trust** the model

**Approaches:**
- **Attention Maps:** Visualize which regions model focuses on
- **Feature Attribution:** Which attributes drive style prediction?
- **Error Analysis:** When model fails, understand why

---

## 📈 Expected Timeline

| Phase | Duration | Focus | Dataset | Expected Accuracy | Status |
|-------|----------|-------|---------|-------------------|--------|
| **Setup** | 1 week | Pipeline infrastructure | N/A | N/A | 🔄 Ready |
| **Phase 1** | 3-4 weeks | Pipeline + baseline model | `/data/` only (style-based) | 80-85% avg | ⏳ Pending |
| ↳ Data prep | 1 week | Image-label mapping, class analysis | `/data/` | N/A | - |
| ↳ Tier 1 tasks | 1 week | Easy visual features (7 tasks) | `/data/` | 85-90% | - |
| ↳ Tier 2 tasks | 1-2 weeks | + Architectural style (4 tasks) | `/data/` | 70-80% | - |
| ↳ Model comparison | 1 week | Test ResNet vs EfficientNet vs ViT | `/data/` | Compare | - |
| **Phase 2** | 2-3 weeks | Scale to full dataset | `/data2/` (neighborhood-based) | 75-85% avg | ⏳ Pending |
| ↳ Data migration | 3 days | Map `/data2/`, deduplicate | `/data2/` | N/A | - |
| ↳ Transfer learning | 1-2 weeks | Fine-tune on larger dataset | `/data2/` | 75-85% | - |
| ↳ Generalization test | 2 days | Held-out neighborhood validation | `/data2/` | Test | - |
| **Phase 3** | 2 weeks | Advanced tasks (OPTIONAL) | `/data2/` | 60-70% | ⏳ Future |
| **Phase 4** | 2 weeks | Alteration detection (RESEARCH) | Both | 50-65% | ⏳ Future |
| **Total** | **6-8 weeks** | **Core pipeline + 11 tasks** | **Both datasets** | **75-85% avg** | |

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

## 📚 References

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

**The model architecture (`multi_task_classifier.py`) and training script (`train_multi_task.py`) are ready!**

**Next: Create image-label mapping CSV to begin Phase 1 training.**
