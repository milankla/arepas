# Arepas — Training Status & Forward Plan

**Date:** May 11, 2026  
**Dataset:** `data2/` — 759 buildings / 2,708 images  
**Split (seed=42):** train 1,911 | val 409 | test 388  
**Backbone:** EfficientNet-B5, image_size=456

---

## Current State of the Model

### Best checkpoints

| Phase | Run | Overall Acc | Cladding | Roof Type | Checkpoint |
|-------|-----|-------------|----------|-----------|------------|
| Phase 1 | `b5/v7_bs16` (pre-crop) | **71.86%** | 59.66% | 52.81% | `outputs/data2/b5/v7_bs16/phase1/best_model_phase1.pth` |
| Phase 1 | `b5/cropped_v2` | 70.91% | 54.03% | 53.06% | `outputs/data2/b5/cropped_v2/phase1/best_model_phase1.pth` |
| Phase 2 | `phase2_full` (pre-crop) | **66.63%** | 59.41% | 54.52% | `outputs/data2/b5/phase2_full/phase2/best_model_phase2.pth` |
| Phase 2 | `cropped_v3_phase2` (diff LR) | 63.72% | 54.03% | 46.21% | `outputs/data2/b5/cropped_v3_phase2/phase2/best_model_phase2.pth` |

Phase 2 adds `architectural_style` (57.5%) and `building_form` (45.2%) on top of the 5 Phase 1 tasks.

---

## What We Learned: Cropped Images

### What "cropping" means in this project

Crops are tight bounding boxes around the full building produced by GroundingDINO. They **do not exclude any part of the building** — the full facade, roofline, and footprint are all present. What they remove is non-building background: sky, neighbouring buildings, street, vegetation.

### Observed effects of cropping (Phase 1)

| Task | Δ vs pre-crop | Interpretation |
|------|--------------|----------------|
| roof_type F1 | **+5.7pp** | Removing sky/background sharpens roofline signal |
| stories acc | **+1.7pp** | Vertical frame aligns with floor-count cues |
| primary_cladding acc | **−5.6pp** | Unexpected — full building is in the crop |
| overall acc | −1.0pp | Partly confounded by lower LR (1e-4 vs 1.5e-4) |

### Why did cladding regress despite full-building crops?

The cladding drop is **not** caused by cutting off facade area. The full facade is visible. The more likely explanations:

1. **Scale normalisation changes material appearance.** When the model sees a building at its native scale in the full image, texture frequency (brick course height, siding lap spacing) is preserved. Tight crops rescaled to 456×456 compress or stretch these frequencies, making cladding materials harder to distinguish.
2. **Context cues removed.** The model may use surrounding context — street-level reference, neighbouring materials, window-to-wall ratio — as indirect cladding signals. Crops eliminate this.
3. **LR confound.** `cropped_v2` used `lr=1e-4` vs `v7_bs16`'s `lr=1.5e-4`. The model was still improving at epoch 14 when early-stopping triggered. With `lr=1.5e-4` and more epochs the gap would likely narrow.

### Recommendation on crops

Keep crops — they improve roof_type and stories. Address cladding by:
- Matching LR (`1.5e-4`) on the next cropped Phase 1 run
- Adding slight padding around the bounding box (5–10% of bbox side) so texture at building edges isn't rescaled as aggressively

---

## What We Learned: Phase 2 Head Freezing

### The failed strategy — freeze Phase 1 heads

`cropped_v2 phase2` froze all 5 Phase 1 task heads (`requires_grad=False`) while keeping the backbone trainable at `lr=1e-4`. The goal was to protect Phase 1 knowledge while the two new heads (arch_style, building_form) bootstrapped.

**What actually happened:**

| Task | Phase 1 best | After Phase 2 (frozen) | Δ |
|------|-------------|------------------------|---|
| primary_cladding | 54.03% | 28.36% | **−25.7pp** |
| stories | 75.31% | 63.57% | −11.7pp |
| roof_type | 53.06% | 54.28% | +1.2pp |
| chimney | 91.44% | 89.00% | −2.4pp |

**Root cause:** The freeze only applied to task heads, not the backbone. The backbone kept shifting its feature representations to serve the new heads. The frozen Phase 1 heads, unable to update, lost alignment with the drifting backbone features — catastrophic forgetting by proxy.

> **Rule:** Never freeze task heads while the backbone trains freely. The head and its corresponding backbone features must move together or not at all.

### The working strategy — differential learning rates

`cropped_v3_phase2` used no head freezing and a two-group optimizer:
- Backbone: `lr = 5e-5` (`1.5e-4 × 0.33`)  
- All task heads: `lr = 1.5e-4`

**Result:** Cladding recovered from 28% to **54%** (+25.7pp). Overall Phase 2 accuracy improved from 60.5% to **63.7%**. Val loss oscillated rather than diverging — training remained stable throughout 17 epochs.

**Why it works:** The backbone drifts slowly enough that Phase 1 heads can continuously re-align. Phase 2 new heads get a 3× higher LR to bootstrap their new classification boundaries from scratch. Knowledge is preserved without any freezing.

---

## Remaining Gap vs Pre-Crop Phase 2 Baseline

`phase2_full` (pre-crop): **66.63%**  
`cropped_v3_phase2` (cropped, diff LR): **63.72%** — gap: **−2.9pp**

| Task | phase2_full | cropped_v3 | Δ | Most likely cause |
|------|------------|-----------|---|-------------------|
| roof_type | 54.52% | 46.21% | −8.3pp | Resolution/scale change at 456px input |
| primary_cladding | 59.41% | 54.03% | −5.4pp | Same scale issue + context removal |
| arch_style | 59.66% | 57.46% | −2.2pp | Less context |
| stories | 72.13% | 70.90% | −1.2pp | Near parity |
| chimney | 92.67% | 91.93% | −0.7pp | Near parity |

The gap is **data/scale-related, not training-strategy-related.** The training strategy is now correct.

---

## Forward Plan

### Context: 2000+ new buildings incoming

This is the highest-leverage event on the horizon. More buildings will:
- Directly address minority-class collapse in cladding (~68% Brick today), arch_style (21 classes), and building_form (32 classes)
- Enable stratified train/val/test splitting (currently non-stratified, causing stories to be 71% 1-story in the test set)
- Potentially allow per-class LR tuning and focal loss to be more effective

**Until the new data arrives, the improvements below are largely diminishing returns. The plan is ordered by priority given the current dataset size.**

---

### Priority 1 — Retrain Phase 1 on crops with correct LR

**Goal:** Close the −1pp Phase 1 gap between `cropped_v2` (70.91%) and `v7_bs16` (71.86%).  
**Action:** Run a new Phase 1 with `lr=1.5e-4` (matching `v7_bs16`) and `--early-stopping-patience 15` (model was still improving at ep14 with patience=10).

```bash
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
python -m src.models.train_multi_task \
  --csv data2/image_label_mapping_phase1.csv \
  --model-config config/models/efficientnet_b5.json \
  --start-phase 1 --end-phase 1 \
  --epochs 30 --batch-size 16 \
  --lr 1.5e-4 --weight-decay 0.01 \
  --early-stopping-patience 15 \
  --cropped-root crops/data2 \
  --output-dir outputs/data2/b5/cropped_v4_phase1
```

**Expected outcome:** Phase 1 overall ~72–73%, cladding ~57–60% (matching pre-crop baseline).

---

### Priority 2 — Phase 2 from the new Phase 1 checkpoint (diff LR)

Once Priority 1 completes, run Phase 2 with the proven differential LR strategy:

```bash
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
python -m src.models.train_multi_task \
  --csv data2/image_label_mapping_phase1.csv \
  --model-config config/models/efficientnet_b5.json \
  --start-phase 2 --end-phase 2 \
  --load-checkpoint outputs/data2/b5/cropped_v4_phase1/phase1/best_model_phase1.pth \
  --epochs 30 --batch-size 16 \
  --lr 1.5e-4 --backbone-lr-scale 0.33 \
  --weight-decay 0.01 \
  --early-stopping-patience 15 \
  --cropped-root crops/data2 \
  --output-dir outputs/data2/b5/cropped_v4_phase2
```

**Expected outcome:** Phase 2 overall ~65–67%, possibly matching or exceeding `phase2_full`.

---

### Priority 3 — Add class weighting for cladding and building_form

The cladding F1 (~25–30%) is disproportionately low vs accuracy (~54–60%) because Brick (~68%) dominates. Focal loss or capped inverse-frequency weights would force the model to learn minority classes.

`MULTI_TASK_STRATEGY.md` already documents the recommended approach: capped inverse-frequency weights with `max_weight=3.0`. This is a code change to `MultiTaskLoss` in `src/models/multi_task_classifier.py`.

**Implement when:** Ready to invest a training run specifically on F1 improvement (vs accuracy).

---

### Priority 4 — Retrain everything on the new 2000+ building dataset

When the new data arrives:

1. **Re-run `scripts/crop_dataset.py`** on new images to extend `crops/data2/` and generate a new combined CSV.
2. **Re-run `scripts/build_phase1_label_mapping.py`** with stratified splitting — use `sklearn.model_selection.train_test_split(stratify=...)` on a composite key of `architectural_style + stories` to ensure rare classes appear in train/val/test.
3. **Retrain Phase 1 from scratch** (or fine-tune from current best) with the larger dataset. With 2× more data, consider increasing `--epochs 40` and `--early-stopping-patience 20`.
4. **Retrain Phase 2** with differential LR from the new Phase 1 checkpoint.

**Expected outcome:** Cladding F1 should improve from ~25% to ~40%+ once Brick is no longer 68% of samples. arch_style and building_form accuracy should improve substantially with 21/32-class coverage.

---

### Priority 5 — Investigate roof_type crop regression

Roof_type dropped −8pp in Phase 2 with cropped images (`cropped_v3`) vs pre-crop (`phase2_full`). Since the full building roofline is in the crop, this is likely a **resolution or aspect-ratio issue** — at 456×456 input, a very wide building's roof gets more compressed than in the full image.

**Experiment:** Add 15% bbox padding in `scripts/crop_dataset.py` before rescaling. This gives the model more "breathing room" around the building and a slightly more natural scale.

**Only worth running after Priority 1/2** — if the Phase 1 cropped run still shows a large roof_type gap, this is the next variable to isolate.

---

## Quick Reference: Working Run Command (current best practice)

```bash
# Phase 1 — cropped, correct LR
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
python -m src.models.train_multi_task \
  --csv data2/image_label_mapping_phase1.csv \
  --model-config config/models/efficientnet_b5.json \
  --start-phase 1 --end-phase 1 \
  --epochs 30 --batch-size 16 \
  --lr 1.5e-4 --weight-decay 0.01 \
  --early-stopping-patience 15 \
  --cropped-root crops/data2 \
  --output-dir outputs/data2/b5/<run_name>

# Phase 2 — from Phase 1 checkpoint, differential LR, no head freezing
python -m src.models.train_multi_task \
  --csv data2/image_label_mapping_phase1.csv \
  --model-config config/models/efficientnet_b5.json \
  --start-phase 2 --end-phase 2 \
  --load-checkpoint outputs/data2/b5/<run_name>/phase1/best_model_phase1.pth \
  --epochs 30 --batch-size 16 \
  --lr 1.5e-4 --backbone-lr-scale 0.33 \
  --weight-decay 0.01 \
  --early-stopping-patience 15 \
  --cropped-root crops/data2 \
  --output-dir outputs/data2/b5/<run_name>_phase2
```

**Do not use `--freeze-phase1-heads`.** The differential LR (`--backbone-lr-scale 0.33`) is the correct head-protection strategy.
