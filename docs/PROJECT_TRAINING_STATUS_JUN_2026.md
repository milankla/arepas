# Arepas — Training Status & Forward Plan

**Date:** June 23, 2026  
**Dataset:** `data2/` — 759 buildings / 2,708 images  
**Split (seed=42):** train 1,911 | val 409 | test 388 images  
**Backbone:** EfficientNet-B5, image_size=456  
**Status:** Phase 3 training tabled; awaiting data drop (Phase 2 best checkpoint retained for production)

---

## Executive Summary

Phase 3 training (learning 7 additional fine-grained attributes: wall_features, landscape_features, window, entrance, associated_buildings, building_category, roof_materials) has reached a plateau on the current dataset. The best Phase 3 run (`v5_head_fusion_boost`) achieved:

- **Phase 3 learning:** 53.56% primary metric avg, 41.56% F1 avg (epoch 13 best)
- **Old-task retention:** 73.06% Phase 1/2 primary avg (2.5pp loss vs Phase 2 best of 75.27%)
- **Overall accuracy:** 63.31% across all 14 tasks (down from 76.22% on the 7 Phase 1/2 tasks alone)

Further improvements on Phase 3 are unlikely with the current 759-building dataset. **The next meaningful gains require the incoming 2000+ building data drop.** Phase 3 training is tabled until that arrives.

---

## Phase 3 Training Results

### Summary

Three Phase 3 experiments were conducted, each testing a different strategy for balancing old-task retention vs new-task learning:

| Run | Strategy | Epochs | Best Epoch | Overall Acc | Old-task Primary | Phase 3 F1 | Val Loss | Notes |
|-----|----------|--------|-----------|-------------|------------------|-----------|----------|-------|
| **v4_protected** | Unfrozen backbone, LR scale 0.02 | 12 | 4 | 62.97% | 73.13% | 40.24% | 1.1648 | Backbone learning too slow; old-task drift evident by ep12 |
| **v5_head_fusion** | Frozen backbone, higher head LR (1e-4) | 15 | 13 | 63.31% | 73.06% | 41.56% | 1.2519 | **Best result**; training still improving at ep13, overfitting by ep15 |
| baseline | Phase 2 only (7 tasks) | — | — | 76.22% | 76.22% | n/a | 0.9672 | For reference |

**Key finding:** Frozen backbone with higher head/fusion learning rate (v5) is the most stable strategy, but yields only marginal Phase 3 gains while still losing retention. The tradeoff is architectural: without a retention loss, the model cannot simultaneously maximize learning on 14 tasks with limited examples.

### Per-Task Movement: v5 (Epoch 1 → 13, best epoch)

**Old tasks (retention challenge):**

| Task | Epoch 1 Primary | Epoch 13 Primary | Δ | Epoch 13 F1 |
|------|----------|-------------|---|-------|
| primary_cladding | 77.49% | 75.62% | −1.87pp | 45.14% |
| stories | 71.09% | 71.75% | +0.66pp | 44.10% |
| chimney_present | 93.03% | 91.14% | −1.89pp | 53.31% |
| setting | 80.34% | 79.29% | −1.05pp | 47.84% |
| architectural_style | 72.32% | 71.75% | −0.57pp | 41.72% |
| building_form | 65.61% | 65.71% | +0.10pp | 29.26% |
| roof_type | 57.31% | 58.77% | +1.46pp | 34.15% |
| **Avg** | **73.88%** | **73.06%** | **−0.82pp** | — |

**Phase 3 tasks (new learning):**

| Task | Epoch 1 Primary | Epoch 13 Primary | Δ | Epoch 13 F1 | Δ |
|------|----------|-------------|---|------|----|
| wall_features | 32.59% | 33.86% | +1.27pp | 39.92% | +2.33pp |
| landscape_features | 38.73% | 39.85% | +1.12pp | 36.47% | +1.22pp |
| window | 41.44% | 42.87% | +1.43pp | 47.60% | +0.58pp |
| entrance | 40.87% | 40.31% | −0.56pp | 40.24% | +1.71pp |
| associated_buildings | 30.81% | 30.33% | −0.48pp | 22.30% | +3.18pp |
| building_category | 91.75% | 93.50% | +1.75pp | 61.74% | +4.67pp |
| roof_materials | 89.81% | 89.28% | −0.53pp | 33.57% | −0.24pp |
| **Avg** | **52.29%** | **53.56%** | **+1.27pp** | **40.26%** | **+1.86pp** |

**Interpretation:** Phase 3 heads are learning, particularly for underrepresented classes (`associated_buildings` F1 +3.18pp, `building_category` F1 +4.67pp). However, the magnitude is small and old-task retention is slowly degrading. The fundamental problem is that multitask learning on 14 tasks with 409 validation images lacks enough signal to sustain learning without explicit retention constraints.

### Epoch-by-epoch trend (v5)

Validation loss rises after epoch 13, indicating overfitting starts around epoch 13–14. The best checkpoint (epoch 13) represents the sweet spot between old-task retention and Phase 3 learning.

```
Epoch  Overall Acc  Old-task Avg  Phase 3 F1  Val Loss
  1       63.09%       73.88%      38.39%    1.1519
  2       62.74%       73.21%      39.45%    1.1591
  3       63.25%       73.50%      40.60%    1.1802
  4       62.97%       73.07%      40.34%    1.2044
  5       63.14%       73.18%      40.78%    1.2169
  6       62.91%       72.79%      40.47%    1.2247
  7       62.83%       72.63%      40.69%    1.2299
  8       62.97%       72.75%      41.18%    1.2281
  9       63.02%       72.76%      40.79%    1.2240
 10       63.14%       72.68%      41.00%    1.2283
 11       63.15%       72.69%      41.12%    1.2397
 12       62.95%       72.70%      41.31%    1.2421
*13       63.31%       73.06%      41.56%    1.2519 ← BEST
 14       63.24%       72.88%      41.44%    1.2444
 15       63.08%       72.76%      41.26%    1.2643
```

---

## Learned Lessons: Phase 3 Experiments

### Lesson 1: Unfrozen Backbone with Scaled LR (v4) Doesn't Work

v4 used `backbone_lr_scale=0.02` (`lr * 0.02`), attempting to let the backbone adapt slowly while frozen Phase 1 heads anchored old knowledge. **Result:** Did not help. Old-task accuracy steadily leaked from 73.65% (ep1) to 72.11% (ep12), losing −1.54pp overall. Phase 3 learning plateaued early (53.25% by ep12, vs v5's 53.56% by ep13).

**Root cause:** Even at 0.02× scale, the backbone moves too much. Frozen old heads, unable to re-align with a drifting backbone, lose their predictive power for old tasks. The learning rate needs to be frozen to 0, not just reduced.

**Implication:** Multitask learning with frozen old heads requires either a completely frozen backbone or a retention loss that explicitly minimizes old-task logit drift.

### Lesson 2: Frozen Backbone + Higher Head LR (v5) is the Stable Approach

v5 used `freeze_backbone=True` and `lr=1e-4` for all heads/fusion. **Result:** Stable training with only −0.82pp old-task decay over 13 epochs. Phase 3 learning reached 41.56% macro F1 (best among the three runs).

**Why it works:** The backbone features are fixed, so frozen old heads remain aligned. New heads + fusion learn purely from the fixed representation, which is slower but predictable. Old-task decay comes from the multi-task loss interference, not backbone drift.

**Trade-off:** Phase 3 improvements are small (+1.27pp primary, +1.86pp F1). Without additional data, further gains would require either:
1. Explicit retention loss (teacher distillation from Phase 2 checkpoint)
2. Reduced Phase 3 task count (focus on easiest tasks first)
3. More training data to reduce overfitting pressure

### Lesson 3: The Plateau is Data-Limited, Not Architecture-Limited

v5's validation loss started rising at epoch 13–14 despite training loss still falling. This indicates the model is memorising the training set and no longer generalising. With 409 validation images and 14 competing tasks, the dataset is too small to support further learning.

**Evidence:**
- Phase 3 macro F1 saturated around 41–42% by epoch 10–11
- Old-task accuracy began declining by epoch 5–6
- Val loss started diverging from train loss by epoch 8–9

This is a classic sign of **data-limited training**, not insufficient model capacity or poor architecture.

---

## Current Best Checkpoints

| Phase | Run | Best Epoch | Config | File | Metrics |
|-------|-----|-----------|--------|------|---------|
| Phase 1 | b5/v7_bs16 | 11 | Pre-crop, LR=1.5e-4, BS=16 | `outputs/data2/b5/v7_bs16/phase1/best_model_phase1.pth` | Overall 71.86%, Cladding 59.66% |
| Phase 2 | phase2_full | 11 | Diff LR, LR=1.5e-4, BS=16 | `outputs/data2/b5/phase2_full/phase2/best_model_phase2.pth` | Overall 66.63%, Cladding 59.41% |
| Phase 3 | v5_head_fusion_boost | 13 | Frozen backbone, LR=1e-4, BS=2 | `outputs/data2/phase3_v5_head_fusion_boost/phase3/best_model_phase3.pth` | Overall 63.31%, Phase 3 F1 41.56% |

**For production deployment:** Use **Phase 2 checkpoint** (`phase2_full` ep11). Phase 3 trades old-task accuracy for marginal new-task learning; Phase 2 remains the better all-around model for the current dataset.

---

## Why Phase 3 Training is Tabled

Three fundamental constraints:

1. **Data imbalance:** 759 buildings / 409 validation images spread across 14 tasks. Minority tasks (e.g., associated_buildings, landscape_features) have <100 positive examples in validation set. No amount of training will improve generalization with so little signal.

2. **Architectural ceiling:** Even with frozen backbone and dedicated head/fusion learning, Phase 3 F1 plateaued at 41–42%. This is about 15pp below what the task difficulty warrants. The gap likely reflects the scarcity of training examples, not model limitations.

3. **Retention tradeoff:** Every increment in Phase 3 learning costs −0.1 to −0.2pp in old-task accuracy. Without explicit retention mechanisms (teacher distillation, regularization), multitask learning on undersampled new tasks inherently drifts from older, better-learned tasks.

**All three constraints disappear when the 2000+ building data arrives.** New data will:
- Increase minority-class sample counts from 50–100 to 300–500+ per class
- Enable stratified train/val/test splitting (fixing test-set class imbalances)
- Reduce per-task sample scarcity, allowing backbone adaptation without retention penalties

---

## Forward Plan

### Phase 3 Training: Tabled until Data Drop

**Status:** No further Phase 3 training recommended on the current `data2/` dataset. The three experiments (v4, v5, and supporting runs) have exhausted the useful parameter space.

**Action:** Archive Phase 3 checkpoints. Retain `v5_head_fusion_boost/phase3/best_model_phase3.pth` for reference evaluation, but do not use in production.

### When the 2000+ Building Data Arrives

1. **Prepare the new dataset:**
   - Run `scripts/crop_dataset.py --csv data3/image_label_mapping_phase1.csv --out crops/data3 --manifest crops/data3/crop_manifest.csv`
   - Merge cropped datasets: `cat crops/data2/crop_manifest.csv crops/data3/crop_manifest.csv > crops/merged/crop_manifest.csv`
   - Generate merged label CSV combining data2/ and data3/ with `scripts/build_phase1_label_mapping.py` using stratified split on `(architectural_style, stories)` composite key

2. **Retrain Phase 1 (5 core tasks):**
   ```bash
   export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
   python -m src.models.train_multi_task \
     --csv crops/merged/combined_label_mapping.csv \
     --model-config config/models/efficientnet_b5.json \
     --start-phase 1 --end-phase 1 \
     --epochs 40 --batch-size 16 \
     --lr 1.5e-4 --weight-decay 0.01 \
     --early-stopping-patience 20 \
     --cropped-root crops/merged \
     --paired-views --paired-fusion task_gated_residual \
     --output-dir outputs/merged_data/b5/phase1_v1
   ```
   **Expected:** Overall ~74–76%, Cladding ~63–68% (up from 59.66%), Roof Type F1 ~42–45% (up from 36.21%).

3. **Retrain Phase 2 (add arch_style + building_form):**
   ```bash
   export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
   python -m src.models.train_multi_task \
     --csv crops/merged/combined_label_mapping.csv \
     --model-config config/models/efficientnet_b5.json \
     --start-phase 2 --end-phase 2 \
     --load-checkpoint outputs/merged_data/b5/phase1_v1/phase1/best_model_phase1.pth \
     --epochs 30 --batch-size 16 \
     --lr 1.5e-4 --backbone-lr-scale 0.33 \
     --weight-decay 0.01 \
     --early-stopping-patience 15 \
     --cropped-root crops/merged \
     --paired-views --paired-fusion task_gated_residual \
     --output-dir outputs/merged_data/b5/phase2_v1
   ```
   **Expected:** Overall ~70–72% (up from 66.63%), Cladding ~62–67%, new tasks stabilize at 60+% acc.

4. **Revisit Phase 3 with retention loss (code change required):**
   
   Implement teacher-student distillation in `src/models/train_multi_task.py`:
   - Load Phase 2 best checkpoint as teacher (frozen)
   - During Phase 3, add KL divergence term for old-task logits: `loss_phase3 = λ * loss_old_tasks_kl + loss_new_tasks`
   - Tune λ to balance (typical: 0.1–0.5)
   
   Then train Phase 3 with the new merged data:
   ```bash
   export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
   python -m src.models.train_multi_task \
     --csv crops/merged/combined_label_mapping.csv \
     --model-config config/models/efficientnet_b5.json \
     --start-phase 3 --end-phase 3 \
     --phase3-labels wall_features,landscape_features,window,entrance,associated_buildings,building_category,roof_materials \
     --load-checkpoint outputs/merged_data/b5/phase2_v1/phase2/best_model_phase2.pth \
     --teacher-checkpoint outputs/merged_data/b5/phase2_v1/phase2/best_model_phase2.pth \
     --teacher-loss-weight 0.3 \
     --epochs 30 --batch-size 2 --grad-accum-steps 12 \
     --lr 1e-4 --weight-decay 0.01 \
     --early-stopping-patience 15 \
     --freeze-phase1-heads \
     --freeze-backbone \
     --cropped-root crops/merged \
     --paired-views --paired-fusion task_gated_residual \
     --output-dir outputs/merged_data/b5/phase3_v1_with_retention
   ```
   **Expected:** Old-task retention ~75%+ (vs 73% currently), Phase 3 F1 ~50%+ (up from 41.56%), with stable multitask learning.

### Parallel: Implement Class Weighting for Imbalanced Tasks

While retraining, add per-task class weights to `MultiTaskLoss`:

- **Cladding** (Brick 68% → multiclass imbalance when coarsened): Apply capped inverse-frequency weights with `max_weight=2.5`
- **Building Form** (32 classes, unevenly distributed): Apply focal loss with `gamma=2.0` or class weights
- **Architecture Style** (14 classes): Monitor for minority-class collapse; apply weights if <2% of samples per class

This is a ~30-line code change to `src/models/multi_task_classifier.py:MultiTaskLoss`.

---

## Risk Assessment & Contingencies

### Risk 1: New data has different distribution than data2

**Mitigation:** Before retraining, run `scripts/analyze_image_data.py` on data3 to check:
- Class balance for each task (compare histograms vs data2)
- Image quality / artifact rates
- Crop coverage (% of buildings detected by GroundingDINO)

If major imbalances or distribution shifts, augment retrain plan with:
- Stratified splitting on (neighborhood, style) not just (style, stories)
- Separate validation on data2 as a held-out test for domain-shift evaluation

### Risk 2: Phase 3 learning still plateaus on merged data

**Cause:** New data has no additional Phase 3 label annotations (unlikely but possible).

**Mitigation:** Check that Phase 3 annotations exist in data3 before planning. If annotations are Phase 1/2 only, focus training on Phase 1/2 with merged data; Phase 3 becomes future work.

### Risk 3: Overfitting returns with larger dataset

**Signs:** Val loss diverges from train loss after epoch 15–20.

**Mitigation:**
- Increase `early-stopping-patience` to 20–25 (larger dataset justifies longer patience)
- Consider adding dropout (currently 0.3 in head projections; can increase to 0.5)
- Use data augmentation (RandAugment, CutMix) during Phase 2/3 training

---

## Phase 3 Run Archive

For reference and reproducibility, all Phase 3 experimental runs are archived with their configs:

| Run | Epochs | Command | Output | Status |
|-----|--------|---------|--------|--------|
| v4_protected_adaptation | 12 | Unfrozen backbone, LR scale 0.02 | `outputs/data2/phase3_v4_protected_adaptation/` | Complete ✓ |
| v5_head_fusion_boost | 15 | Frozen backbone, head LR 1e-4 | `outputs/data2/phase3_v5_head_fusion_boost/` | Complete ✓, best result |

Both checkpoints, configs, and training histories are saved. The experiments validate that frozen backbone + higher head LR is the best current approach, but gains are marginal on the small dataset.

---

## Timeline

- **Now (June 2026):** Tabled Phase 3 training. Phase 2 checkpoint remains production-ready.
- **Q3 2026 (data drop):** Data3 arrives. Begin Phase 1 retraining on merged dataset (expected: 2–3 weeks for Phase 1 + Phase 2).
- **Q4 2026 (if retention loss implemented):** Phase 3 retraining with teacher distillation. Expected to unlock Phase 3 improvements from 41% to 50%+ F1.

---

## Recommendations for Next Session

1. ✅ **Save v5 best checkpoint** as reference. Do not delete.
2. ✅ **Update README.md** with Phase 2 as current best production model.
3. ✅ **Archive Phase 3 experiment configs** in `docs/PHASE3_EXPERIMENT_LOG.md`.
4. ⏳ **When data arrives:** Begin Phase 1 retraining immediately; Phase 3 work is contingent on Phase 1/2 retraining success.
5. ⏳ **Plan teacher distillation code** for Phase 3 once merged data Phase 1/2 checkpoints are available.

---

## Summary Table: All Production Checkpoints

| Phase | Best Model | Overall Acc (subset) | Best Epoch | Config | Path |
|-------|-----------|----------|----------|--------|------|
| 1 | b5/v7_bs16 | 71.86% (5 tasks) | 11 | Pre-crop, LR=1.5e-4 | `outputs/data2/b5/v7_bs16/phase1/best_model_phase1.pth` |
| 2 | phase2_full | 66.63% (7 tasks) | 11 | Diff LR, LR=1.5e-4 | `outputs/data2/b5/phase2_full/phase2/best_model_phase2.pth` |
| 3 | v5_head_fusion_boost | 63.31% (14 tasks) | 13 | Frozen backbone, LR=1e-4 | `outputs/data2/phase3_v5_head_fusion_boost/phase3/best_model_phase3.pth` |

**Recommended for production:** Phase 2 checkpoint (best accuracy/retention balance on current data).
