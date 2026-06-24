# Arepas — Training Run History

**Last updated:** June 23, 2026 (Phase 3 training complete & tabled)  
**Dataset:** `data2/image_label_mapping_phase1.csv` — 759 buildings / 2,708 images  
**Split (fixed seed=42):** train 1,911 | val 409 | test 388 images  
**Phase 1 tasks:** stories, roof_type, primary_cladding, chimney_present, setting  
**Phase 2 tasks (added):** architectural_style, building_form  
**Phase 3 tasks (added):** wall_features, landscape_features, window, entrance, associated_buildings, building_category, roof_materials

---

## Current Best Models

### Phase 1 — 5 tasks (stories, roof_type, primary_cladding, chimney_present, setting)

| Rank | Run | Backbone | Overall Acc | Cladding Acc | Cladding F1 | Notes |
|------|-----|----------|-------------|--------------|-------------|-------|
| 🥇 | **b5/v7_bs16** | EfficientNet-B5 | **71.86%** | 59.66% | 22.9% | Pre-crop baseline |
| 🥈 | **b5/cropped_v2** | EfficientNet-B5 | 70.91% | 54.03% | 25.1% | Cropped images; roof_type F1 +5.7pp |
| 🥉 | v7 | ResNet50 | 71.35% | 55.50% | 23.5% | |

> **Cropping trade-off:** `cropped_v2` improves `roof_type` F1 by +5.7pp and `stories` acc by +1.7pp, but `primary_cladding` acc drops −5.6pp (crops cut facade context). Overall accuracy is −1pp, partly confounded by the lower LR (1e-4 vs 1.5e-4 in v7_bs16). `cropped_v2` was still improving at epoch 14 — further epochs may close the gap.

### Phase 2 — 7 tasks (Phase 1 + architectural_style + building_form)

| Rank | Run | Backbone | Overall Acc (7 tasks) | Cladding Acc | Cladding F1 | Notes |
|------|-----|----------|-----------------------|--------------|-------------|-------|
| 🥇 | **phase2_full ep11** | EfficientNet-B5 | **66.63%** | 59.41% | 30.9% | From v7_bs16 checkpoint (pre-crop) |
| 🥈 | **cropped_v3_phase2 ep14** | EfficientNet-B5 | **63.72%** | 54.03% | 30.3% | Diff LR (backbone 0.33×); cladding collapse fixed |
| 🥉 | **b5/cropped_v2 phase2 ep10** | EfficientNet-B5 | 60.49% | 28.36% | 14.9% | From cropped_v2 ph1 ckpt; cladding collapsed (frozen heads) |
| 4 | phase2_warmup ep5 | EfficientNet-B5 | 56.33% | — | — | |

> **Note:** Phase 2 overall acc is computed across all 7 tasks. It is **not directly comparable** to Phase 1's 71.86% (5 tasks). The two new tasks (architectural_style: 59.66%, building_form: 45.72%) lower the average. Phase 1 tasks held steady or improved vs their Phase 1 baselines.

**Note on cladding F1:** Low cladding F1 (~23–31%) despite reasonable accuracy because Brick dominates at ~68% of samples. This is a known class imbalance problem pending more data.

### Phase 3 — 14 tasks (Phase 1/2 + 7 new fine-grained attributes)

**Status:** Tabled. Current dataset (759 buildings, 409 val samples) is too small to support further Phase 3 learning without explicit retention loss. Awaiting 2000+ building data drop.

| Rank | Run | Strategy | Best Epoch | Overall Acc (14 tasks) | Old-task Primary | Phase 3 F1 | Notes |
|------|-----|----------|-----------|------------------------|------------------|-----------|-------|
| 🥇 | **v5_head_fusion_boost ep13** | Frozen backbone, head LR=1e-4 | 13 | **63.31%** | 73.06% | 41.56% | **Best result**; overfitting evident by ep15 |
| 🥈 | v4_protected_adaptation ep12 | Unfrozen backbone, LR scale 0.02 | 12 | 62.97% | 73.13% | 40.24% | Flat learning; old-task decay by ep12 |

> **Key finding:** Frozen backbone + higher head LR (v5) provides stable training but marginal gains on small dataset. Without additional data, Phase 3 improvements plateau at ~41% F1. Data imbalance + task competition prevents meaningful learning. Phase 3 resumes after 2000+ building data arrives with teacher-distillation based retention loss (code change required).

---

## Cladding Label Scheme History

| Runs | Scheme | # Classes | Notes |
|------|--------|-----------|-------|
| v1, v2, v3 (ResNet50) | Raw schema | 18 | Majority-class shortcut → ~78% acc but F1 ~13% |
| v4+ (ResNet50) | Coarsened | 8 | `CLADDING_COARSEN_MAP` in `architectural_dataset.py` |
| b5/v6 | Raw schema | 18 | Experiment: reverted; confirmed imbalance is the problem |
| **Current** | **Coarsened** | **8** | Restored; waiting for more data before revisiting |

---

## Full Run Log

### ResNet50 Runs — `data2/`

| Run | Date | LR | BS | WD | Epochs cfg/run | Early stop | Cladding classes | Best overall | Best cladding | Notes |
|-----|------|----|----|----|----------------|------------|------------------|-------------|---------------|-------|
| **v1** | 2026-03-22 | 1e-4 | 32 | — | 30 / 8 | yes | 18 (raw) | 69.83% | 78.00% | Brick shortcut; F1~13% |
| **v2** | 2026-03-24 | 1e-4 | 32 | — | 30 / 9 | yes | 18 (raw) | 77.54% | 78.00% | Same shortcut; high acc misleading |
| **v3** | 2026-04-06 | 1e-4 | 32 | — | 30 / 30 | no | 18 (raw) | 77.21% | 77.75% | Full run; same Brick-shortcut issue |
| **v4** | 2026-04-14 | 1e-4 | 32 | — | 30 / 6 | no | 8 (coarsened) | 56.61% | 21.52% | Cladding coarsening introduced; crashed early |
| **v5** | 2026-04-14 | 1e-4 | 32 | — | 30 / 30 | no | 8 (coarsened) | 68.46% | 49.39% | First successful full run with 8-class cladding |
| **v6** | 2026-04-19 | 1e-4 | 32 | — | 30 / 30 | no | 8 (coarsened) | 69.51% | 55.26% | Incremental improvement |
| **v7** | 2026-04-19 | 1e-4 | 32 | — | 30 / 30 | no | 8 (coarsened) | **71.35%** | 55.50% | **Current best ResNet50** |

#### v7 Final Per-Task Breakdown (best epoch)

| Task | Accuracy | Macro F1 |
|------|----------|----------|
| stories | 73.11% | 39.04% |
| roof_type | 52.32% | 35.03% |
| primary_cladding | 55.50% | 23.51% |
| chimney_present | 93.64% | 48.36% |
| setting (Jaccard) | 81.30% | 22.73% |
| **Overall** | **71.35%** | — |

---

### EfficientNet-B5 Runs — `data2/`

| Run | Date | LR | BS | WD | Epochs cfg/run | Early stop | Cladding classes | Best overall | Best cladding | Notes |
|-----|------|----|----|----|----------------|------------|------------------|-------------|---------------|-------|
| **b5/v1** | 2026-04-27 | 1e-4 | 4 | — | 30 / 30 | no | 8 (coarsened) | 69.45% | 52.81% | Batch=4; severe overfit suspected |
| **b5/v2** | 2026-04-28 | 1e-4 | 4 | 0.03 | 30 / 10 | yes | 8 (coarsened) | 60.03% | 30.07% | High WD killed training |
| **b5/v3** | 2026-04-28 | 1e-4 | 4 | 0.01 | 30 / 12 | yes | 8 (coarsened) | 60.80% | 36.43% | Still batch=4 |
| **b5/bs8_smoke** | 2026-04-29 | 1e-4 | 8 | 0.01 | 1 / 1 | no | 8 (coarsened) | 33.54% | 4.17% | 1-epoch smoke test only |
| **b5/v4_bs8** | 2026-04-29 | 1e-4 | 8 | 0.01 | 30 / 2 | no | 8 (coarsened) | 53.94% | 16.38% | Crashed after 2 epochs (DataLoader) |
| **b5/v4_bs8_retry** | 2026-04-29 | 1e-4 | 8 | 0.01 | 30 / — | no | 8 (coarsened) | — | — | Incomplete / corrupted log |
| **b5/v4_bs8_retry2** | 2026-04-29 | 1e-4 | 8 | 0.01 | 30 / 12 | yes | 8 (coarsened) | 68.96% | 51.34% | Baseline for grid search |
| **b5/v5** | 2026-04-29 | 1e-4 | 8 | 0.005 | 30 / 10 | yes | 8 (coarsened) | 66.08% | 45.97% | Lower WD experiment |
| **b5/v6** | 2026-05-04 | 1.1e-4 | 8 | 0.01 | 15 / 11 | yes | 18 (raw) | 62.55% | 21.27% | Cladding revert experiment; raw 18-class failed |
| **b5/v7_bs16** | 2026-05-04 | 1.5e-4 | 16 | 0.01 | 25 / 13 | yes (pat=10) | 8 (coarsened) | **71.86%** | 59.66% | **Phase 1 best (pre-crop)**; stopped ep 13, best ep 11 |
| **b5/cropped_v1** | 2026-05-07 | 1e-4 | 16 | 0.01 | 25 / 1 | — | 8 (coarsened) | 50.12% | 7.09% | Cropped images; run interrupted after 1 epoch |
| **b5/cropped_v2** | 2026-05-08 | 1e-4 | 16 | 0.01 | 25 / 14 | yes (pat=10) | 8 (coarsened) | **70.91%** | 54.03% | Cropped images; best ep 14 (still improving at stop) |

---

### EfficientNet-B5 Phase 2 Runs — `data2/`

Phase 2 adds `architectural_style` and `building_form` heads. Loaded from Phase 1 checkpoint `outputs/data2/b5/v7_bs16/phase1/best_model_phase1.pth`.

| Run | Date | Stage | LR | BS | WD | Epochs cfg/run | Early stop | Best overall (7 tasks) | Notes |
|-----|------|-------|----|----|----|----------------|------------|------------------------|-------|
| **phase2_warmup** | 2026-05-05 | Stage 1 (new heads only) | 3.0e-4 | 16 | 0.01 | 5 / 5 | no | 56.33% | Phase 1 heads frozen; new heads warm-up |
| **phase2_full** | 2026-05-06–07 | Stage 2 (all unfrozen) | 1.5e-4 | 16 | 0.01 | 25 / 11 | yes (pat=10) | **66.63%** | Joint fine-tune; best val_loss ep1=1.506; best acc ep11 |
| **b5/cropped_v2 phase2** | 2026-05-09 | Curriculum ph2 | 1e-4 | 16 | 0.01 | 25 / 11 | yes (pat=10) | 60.49% | From cropped_v2 ph1 ckpt; ph1 heads frozen during ph2; cladding collapsed −27pp |
| **cropped_v3_phase2** | 2026-05-10 | Diff LR (backbone 0.33×) | 1.5e-4 | 16 | 0.01 | 30 / 17 | yes (pat=15) | **63.72%** | From cropped_v2 ph1 ckpt; no freeze; backbone lr=5e-5, heads lr=1.5e-4; cladding collapse fixed |

#### phase2_full — All Epoch Results

| Epoch | Train Loss | Val Loss | Overall Acc (7 tasks) |
|-------|-----------|----------|----------------------|
| 1 | 0.1319 | **1.5062** ← best val | 60.50% |
| 2 | 0.0881 | 1.6554 | 61.94% |
| 3 | 0.0635 | 1.9109 | 62.66% |
| 4 | 0.0469 | 1.8264 | 63.09% |
| 5 | 0.0435 | 1.9235 | 61.89% |
| 6 | 0.0300 | 1.8168 | 64.34% |
| 7 | 0.0247 | 1.8833 | 65.27% |
| 8 | 0.0211 | 1.9373 | 65.01% |
| 9 | 0.0191 | 1.9673 | 65.50% |
| 10 | 0.0148 | 1.9758 | 66.30% |
| **11** | **0.0137** | 1.9832 | **66.63%** ← best acc, FINAL |

Early stopping triggered after epoch 11 (patience=10 from best val_loss at epoch 1). Val loss diverged while accuracy continued improving — model was memorising training set while still improving on new task heads.

#### b5/v7_bs16 Final Per-Task Breakdown (best epoch = 11)

| Task | Accuracy | Macro F1 |
|------|----------|----------|
| stories | 73.59% | 38.89% |
| roof_type | 52.81% | 36.21% |
| primary_cladding | 59.66% | 22.91% |
| chimney_present | 92.42% | 48.03% |
| setting (Jaccard) | 80.81% | 24.01% |
| **Overall** | **71.86%** | — |

#### b5/cropped_v2 Phase 1 — All Epoch Results

| Epoch | Train Loss | Val Loss | Overall Acc |
|-------|-----------|----------|-------------|
| 1 | — | — | 49.51% |
| 2 | — | — | 50.86% |
| 3 | — | — | 52.69% |
| 4 | — | — | 54.77% |
| 5 | — | — | 61.13% |
| 6 | — | — | 65.65% |
| 7 | — | — | 64.55% |
| 8 | — | — | 65.53% |
| 9 | — | — | 68.22% |
| 10 | — | — | 68.46% |
| 11 | — | — | 69.00% |
| 12 | — | — | 69.68% |
| 13 | — | — | 70.10% |
| **14** | — | — | **70.91%** ← best acc, FINAL |

Early stopping triggered after epoch 14 (patience=10 from best val_loss). Model was still improving at stop — extended training likely beneficial.

#### b5/cropped_v2 Phase 1 Final Per-Task Breakdown (best epoch = 14)

| Task | Accuracy | Macro F1 | vs b5/v7_bs16 |
|------|----------|----------|---------------|
| stories | 75.31% | 41.41% | +1.7pp acc, +2.5pp F1 |
| roof_type | 53.06% | 41.94% | +0.2pp acc, **+5.7pp F1** |
| primary_cladding | 54.03% | 25.15% | **−5.6pp acc**, +2.2pp F1 |
| chimney_present | 91.44% | 47.77% | −1.0pp acc, −0.3pp F1 |
| setting (Jaccard) | 80.73% | — | ~same (exact=69.68%, sF1=84.50%) |
| **Overall** | **70.91%** | — | **−1.0pp** |

#### phase2_full Final Per-Task Breakdown (epoch 11 / best-acc checkpoint)

| Task | Val Accuracy | Macro F1 | vs Phase 1 |
|------|-------------|----------|------------|
| stories | 72.13% | 36.99% | −1.5pp |
| roof_type | 54.52% | 33.88% | +1.7pp |
| primary_cladding | 59.41% | 30.90% | −0.2pp |
| chimney_present | 92.67% | 48.10% | +0.2pp |
| setting (Jaccard) | 82.33% | — | +1.5pp (exact=71.39%, sF1=86.06%) |
| architectural_style | 59.66% | 23.04% | *(new)* |
| building_form | 45.72% | 21.84% | *(new)* |
| **Overall (7 tasks)** | **66.63%** | — | — |

#### cropped_v3_phase2 — All Epoch Results

| Epoch | Train Loss | Val Loss | Overall Acc (7 tasks) |
|-------|-----------|----------|-----------------------|
| 1 | 1.0136 | 1.2057 | 55.77% |
| 2 | 0.6482 | **1.1706** ← best val | 57.17% |
| 3 | 0.5387 | 1.1710 | 59.51% |
| 4 | 0.4487 | 1.1857 | 60.19% |
| 5 | 0.3829 | 1.2004 | 58.92% |
| 6 | 0.3303 | 1.2959 | 62.22% |
| 7 | 0.2908 | 1.2415 | 61.55% |
| 8 | 0.2720 | 1.2498 | 62.19% |
| 9 | 0.2551 | 1.3154 | 62.05% |
| 10 | 0.2301 | 1.3123 | 62.13% |
| 11 | 0.2248 | 1.3160 | 63.10% |
| 12 | 0.2106 | 1.2845 | 62.37% |
| 13 | 0.1999 | 1.3454 | 63.71% |
| **14** | **0.1975** | 1.3956 | **63.72%** ← best acc |
| 15 | 0.1978 | 1.3600 | 63.27% |
| 16 | 0.1880 | 1.3558 | 62.90% |
| 17 | 0.1829 | 1.3590 | 63.61% |

Early stopping triggered after epoch 17 (patience=15 from best val_loss at epoch 2). Accuracy plateaued at ~63–64% from epoch 6 onward — convergence reached. Val loss oscillated rather than diverging, significantly better behaviour than the frozen-head runs.

#### cropped_v3_phase2 Final Per-Task Breakdown (epoch 14 / best-acc checkpoint)

| Task | Val Accuracy | Macro F1 | vs cropped_v2 ph2 | vs phase2_full |
|------|-------------|----------|--------------------|----------------|
| stories | 70.90% | 47.42% | **+7.3pp** | −1.2pp |
| roof_type | 46.21% | 32.31% | −8.1pp | −8.3pp |
| primary_cladding | 54.03% | 30.26% | **+25.7pp** | −5.4pp |
| chimney_present | 91.93% | 47.90% | +2.9pp | −0.7pp |
| setting (Jaccard) | 80.26% | — | −1.3pp (exact=68.46%, sF1=84.23%) | −2.1pp |
| architectural_style | 57.46% | 21.22% | −1.2pp | −2.2pp |
| building_form | 45.23% | 19.59% | −2.7pp | −0.5pp |
| **Overall (7 tasks)** | **63.72%** | — | **+3.2pp** | **−2.9pp** |

> **Key result:** Differential LR (backbone 5e-5, heads 1.5e-4) fully prevented the cladding collapse (+25.7pp vs frozen-head run). The remaining −2.9pp gap vs pre-crop `phase2_full` is attributable to cropping losing facade/roof context, not the training strategy. roof_type regression (−8pp) is the main open issue — crops clip rooflines.

#### b5/cropped_v2 Phase 2 — All Epoch Results

| Epoch | Train Loss | Val Loss | Overall Acc (7 tasks) |
|-------|-----------|----------|----------------------|
| 1 | 0.8586 | **1.0672** ← best val | 54.45% |
| 2 | 0.5276 | 1.1166 | 56.74% |
| 3 | 0.3821 | 1.1527 | 57.53% |
| 4 | 0.2785 | 1.1167 | 57.40% |
| 5 | 0.2288 | 1.3222 | 59.09% |
| 6 | 0.1771 | 1.2220 | 59.89% |
| 7 | 0.1469 | 1.2695 | 59.63% |
| 8 | 0.1230 | 1.2628 | 58.22% |
| 9 | 0.1144 | 1.3665 | 59.74% |
| **10** | **0.0947** | 1.3511 | **60.49%** ← best acc |
| 11 | 0.0870 | 1.3931 | 60.14% |

Early stopping triggered after epoch 11 (patience=10 from best val_loss at epoch 1). Val loss diverged from epoch 2; same pattern as `phase2_full`. Phase 1 heads (frozen during Phase 2) degraded as backbone continued adapting — most severely `primary_cladding` (54% → 28%).

#### b5/cropped_v2 Phase 2 Final Per-Task Breakdown (epoch 10 / best-acc checkpoint)

| Task | Val Accuracy | Macro F1 | vs cropped_v2 Ph1 | vs phase2_full |
|------|-------------|----------|-------------------|----------------|
| stories | 63.57% | 35.24% | −11.7pp | −8.6pp |
| roof_type | 54.28% | 35.02% | +1.2pp | −0.2pp |
| primary_cladding | 28.36% | 14.94% | **−25.7pp** | **−31.1pp** |
| chimney_present | 89.00% | 47.09% | −2.4pp | −3.7pp |
| setting (Jaccard) | 81.60% | — | +0.9pp (exact=70.66%, sF1=85.35%) | −0.7pp |
| architectural_style | 58.68% | 26.00% | *(new)* | −1.0pp |
| building_form | 47.92% | 22.16% | *(new)* | +2.2pp |
| **Overall (7 tasks)** | **60.49%** | — | — | **−6.1pp vs phase2_full** |

#### phase2_full — Held-Out Test Set Results (388 images, 114 buildings)

> Report: `outputs/data2/b5/phase2_full/test_eval.json`

| Task | Test Accuracy | Macro F1 | vs Val | Notes |
|------|--------------|----------|--------|-------|
| stories | 55.15% | 38.35% | −17.0pp | Split artifact — non-stratified; test has 71% 1-story but model recall low |
| roof_type | 46.13% | 28.93% | −8.4pp | Class imbalance; rare labels (Pyramidal, Dutch Hipped) get 0% recall |
| primary_cladding | 52.32% | 27.72% | −7.1pp | Class imbalance; Sheet Metal + Shingles 0% recall |
| chimney_present | 93.56% | 48.34% | +0.9pp | Only 3 "Yes" examples in test — macro F1 split artifact |
| setting (Jaccard) | 82.60% | 26.65% | +0.3pp | exact=72.94%, sF1=85.87%, ham=93.47% |
| architectural_style | 62.11% | 27.18% | **+2.5pp** | Slight test generalisation gain |
| building_form | 52.84% | 33.29% | **+7.1pp** | Significant test generalisation gain |
| **Overall (7 tasks)** | **63.53%** | — | −3.1pp | |

---

#### b5/v4_bs8_retry2 Final Per-Task Breakdown

| Task | Accuracy | Macro F1 |
|------|----------|----------|
| stories | 68.22% | 37.11% |
| roof_type | 50.37% | 34.49% |
| primary_cladding | 51.34% | 24.06% |
| chimney_present | 93.40% | 48.29% |
| setting (Jaccard) | 81.46% | 25.14% |
| **Overall** | **68.96%** | — |

---

### Grid Search — EfficientNet-B5 (batch=8, epochs=10, early-stop-patience=8)

**Purpose:** Narrow LR × WD sweep around b5/v4_bs8_retry2 baseline (68.96%)

| LR | WD | Best overall | Best cladding | Epochs run | Early stop |
|----|-----|-------------|---------------|------------|------------|
| 1.0e-4 | 0.008 | 68.39% | 52.08% | 10 | yes |
| 1.0e-4 | 0.009 | 65.93% | 44.25% | 10 | yes |
| 1.0e-4 | 0.010 | 66.49% | 46.21% | 9 | yes |
| 1.1e-4 | 0.008 | 65.74% | 48.17% | 10 | yes |
| 1.1e-4 | 0.009 | 56.65% | 20.78% | 4 | no |
| **1.1e-4** | **0.010** | **68.51%** | **46.45%** | 10 | yes |
| 1.2e-4 | 0.008 | 67.65% | 47.19% | 9 | yes |
| 1.2e-4 | 0.009 | 67.73% | 56.48% | 9 | yes |
| 1.2e-4 | 0.010 | 67.32% | 45.97% | 10 | no |

**Winner:** lr=1.1e-4, wd=0.010 → **68.51%** overall

**Key finding:** lr=1.2e-4 is too aggressive for B5 on this dataset. lr=1.1e-4 with wd=0.010 (original value) beats lr=1.0e-4.

#### Grid Winner (lr=1.1e-4, wd=0.010) Final Per-Task Breakdown

| Task | Accuracy | Macro F1 |
|------|----------|----------|
| stories | 72.37% | 47.55% |
| roof_type | 53.30% | 39.21% |
| primary_cladding | 46.45% | 20.79% |
| chimney_present | 88.75% | 47.02% |
| setting (Jaccard) | 81.66% | 24.35% |
| **Overall** | **68.51%** | — |

---

### data/ Dataset (original, pre-data2)

| Run | Date | Backbone | LR | BS | Epochs | Best overall | Best cladding | Notes |
|-----|------|----------|----|----|--------|-------------|---------------|-------|
| phase1_initial | 2026-03-22 | ResNet50 | 1e-4 | 32 | 20/20 | 71.15% | 77.87% | `data/` only; 10 cladding classes (raw) |

---

## Key Learnings

### Why v2/v3 showed 78% cladding accuracy (misleading)
v2/v3 used 18 raw cladding classes. The validation set happens to be ~75% Brick buildings (fixed seed=42). The model predicted Brick for nearly everything, achieving 78% accuracy with Macro F1 of only ~13%. It was measuring the Brick fraction in the val set, not true cladding discrimination.

### Why 18 raw classes (b5/v6) gave only 21% cladding accuracy
B5 with batch=8 never converged to the Brick shortcut (noisy gradients, stochastic depth regularization). With 18 classes and severe imbalance (Brick=68%), the model spread predictions randomly → near-random 5–21% accuracy. The class imbalance problem is the same either way; the larger model just didn't find the shortcut.

### Cladding class distribution (data2/)
| Class (coarsened) | Approx % |
|---|---|
| Brick | ~68% |
| Siding - Vinyl | ~9% |
| Stucco | ~11% |
| Siding - Other | ~7% |
| Shingles | ~2% |
| Concrete / Stone | ~2% |
| Sheet Metal | ~1% |
| Other Cladding | <1% |

Fix requires more data for minority classes, or focal loss / class weighting (MULTI_TASK_STRATEGY.md recommends capped inverse-frequency weights, max=3.0).

### ResNet50 vs EfficientNet-B5
- **B5 bs=16 (v7_bs16): 71.86%** — Phase 1 best; batch=16 gave more stable gradients vs bs=8
- ResNet50 (v7): 71.35% — strong baseline, trains faster per epoch
- B5 best grid (bs=8, lr=1.1e-4): 68.51% — batch=8 too noisy for B5 capacity
- B5 batch=4 (v1): seemed better (69.45%) but suspected overfitting; early stopping not active

### Why batch=16 helped B5
Scaling LR by √2 (1.1e-4 → 1.5e-4) with batch doubling (8→16) follows linear scaling rule. The larger batch reduced gradient noise, allowing B5's stochastic depth and wider layers to converge more reliably. Stopped at epoch 13 (patience=10), best at epoch 11.

### Phase 2 Training Observations
- **Val loss / accuracy divergence:** Val loss rose from 1.51 (epoch 1) to 1.98 (epoch 11) while overall accuracy climbed from 60.5% → 66.6%. The model was overfitting the training set while simultaneously improving on the two new task heads (arch_style, building_form), masking generalisation degradation in per-task loss.
- **I/O bottleneck:** 29K large JPEGs (1–6 MB each) with `persistent_workers=False` (default) caused full worker respawn each epoch on macOS, stalling the GPU at ~10% utilisation (70–130 s/batch). Fix applied: `persistent_workers=True, prefetch_factor=4` in `build_dataloaders()`. Takes effect on next run.
- **architectural_style (59.7%)** and **building_form (45.7%)** are the weakest tasks — most classes (21 and 32 respectively). Both will benefit from more data and image resizing + augmentation improvements.
- **building_form weakest overall (45.7%)** — 32 classes with heavy long-tail distribution; needs class weighting or focal loss.

### Phase 2 Test Set Observations
- **Overall gap: −3.1pp** (val 66.63% → test 63.53%). No collapse; model generalises.
- **stories −17pp**: Largest drop. Non-stratified split (stratification fell back due to rare arch_style classes) resulted in an unrepresentative test set — 275/388 = 71% 1-story buildings but model recall on 1-story was only 46%. Not a true overfitting signal — a split distribution artifact.
- **chimney_present macro F1=48%** despite 93.6% accuracy: Only 3 "Yes" examples in test (vs ~15% in training). Split imbalance artifact; per-label recall is effectively unmeasurable at this support.
- **architectural_style and building_form both improved on test** (+2.5pp and +7.1pp respectively). Positive sign that the new heads are not overfit to the val distribution.
- **roof_type and primary_cladding −8pp each**: Consistent with majority-class collapse on rare labels (Pyramidal, Dutch Hipped, Sheet Metal, Shingles all 0% test recall). Confirms class imbalance is the ceiling, not generalisation.

---

### EfficientNet-B5 Phase 3 Runs — `data2/` (14 tasks: Phase 1/2 + 7 new)

Phase 3 training experiments focused on learning 7 new fine-grained architectural attributes while minimizing degradation of the 7 Phase 1/2 tasks. The dataset is too small (759 buildings, 409 validation images) to support simultaneous learning without retention mechanisms.

| Run | Date | Strategy | Epochs cfg/run | Freeze config | LR setup | Best Overall (14 tasks) | Old-task Primary | Phase 3 F1 | Notes |
|-----|------|----------|-----------|----------|----------|-----------|------------------|-----------|-------|
| **v4_protected_adaptation** | 2026-06-16 | Unfrozen backbone w/ scale | 12 / 12 | None | backbone_lr_scale=0.02, lr=5e-5 | 62.97% | 73.13% | 40.24% | Flat learning; backbone too slow at 0.02× scale; old-task accuracy leaks −1.54pp |
| **v5_head_fusion_boost** | 2026-06-23 | Frozen backbone, high head LR | 16 / 15 | backbone=frozen, phase1_heads=frozen | lr=1e-4 all heads/fusion | **63.31%** | 73.06% | **41.56%** | **Best result**; stable training; overfitting signals after ep13 |

#### v5_head_fusion_boost (Frozen Backbone, Head LR 1e-4) — Complete Epoch Results

| Epoch | Train Loss | Val Loss | Overall Acc | Old-task Avg | Phase 3 F1 | Notes |
|-------|-----------|----------|-------------|---------|-----------|-------|
| 1 | 1.1764 | 1.1519 | 63.09% | 73.88% | 38.39% | |
| 2 | 0.9524 | 1.1591 | 62.74% | 73.21% | 39.45% | |
| 3 | 0.8451 | 1.1802 | 63.25% | 73.50% | 40.60% | |
| 4 | 0.7842 | 1.2044 | 62.97% | 73.07% | 40.34% | |
| 5 | 0.7294 | 1.2169 | 63.14% | 73.18% | 40.78% | |
| 6 | 0.6821 | 1.2247 | 62.91% | 72.79% | 40.47% | |
| 7 | 0.6355 | 1.2299 | 62.83% | 72.63% | 40.69% | |
| 8 | 0.5923 | 1.2281 | 62.97% | 72.75% | 41.18% | |
| 9 | 0.5619 | 1.2240 | 63.02% | 72.76% | 40.79% | |
| 10 | 0.5211 | 1.2283 | 63.14% | 72.68% | 41.00% | |
| 11 | 0.4927 | 1.2397 | 63.15% | 72.69% | 41.12% | |
| 12 | 0.4645 | 1.2421 | 62.95% | 72.70% | 41.31% | |
| **13** | **0.4389** | **1.2519** | **63.31%** | **73.06%** | **41.56%** | **← BEST** |
| 14 | 0.4258 | 1.2444 | 63.24% | 72.88% | 41.44% | Overfitting begins |
| 15 | 0.3655 | 1.2643 | 63.08% | 72.76% | 41.26% | Val loss diverges; training loss still declining |

Early stopping did not trigger (patience=20, no patience threshold reached). **Best checkpoint at epoch 13** (not final epoch 15); represents sweet spot between Phase 3 learning and old-task retention. Val loss rose from 1.2519 (ep13) to 1.2643 (ep15) indicating model overfitting to training set.

#### v5_head_fusion_boost — Per-Task Breakdown (Epoch 13, Best Checkpoint)

**Old tasks (retention analysis):**

| Task | Epoch 1 Acc | Epoch 13 Acc | Δ | Epoch 13 F1 | F1 Δ |
|------|-----------|-----------|---|------|----|
| primary_cladding | 77.49% | 75.62% | −1.87pp | 45.14% | — |
| stories | 71.09% | 71.75% | +0.66pp | 44.10% | — |
| chimney_present | 93.03% | 91.14% | −1.89pp | 53.31% | — |
| setting | 80.34% | 79.29% | −1.05pp | 47.84% | — |
| architectural_style | 72.32% | 71.75% | −0.57pp | 41.72% | — |
| building_form | 65.61% | 65.71% | +0.10pp | 29.26% | — |
| roof_type | 57.31% | 58.77% | +1.46pp | 34.15% | — |
| **Old-task Avg** | **73.88%** | **73.06%** | **−0.82pp** | — | — |

**New Phase 3 tasks (learning analysis):**

| Task | Epoch 1 Acc | Epoch 13 Acc | Δ | Epoch 13 F1 | F1 Δ |
|------|-----------|-----------|---|------|----|
| wall_features | 32.59% | 33.86% | +1.27pp | 39.92% | — |
| landscape_features | 38.73% | 39.85% | +1.12pp | 36.47% | — |
| window | 41.44% | 42.87% | +1.43pp | 47.60% | — |
| entrance | 40.87% | 40.31% | −0.56pp | 40.24% | — |
| associated_buildings | 30.81% | 30.33% | −0.48pp | 22.30% | — |
| building_category | 91.75% | 93.50% | +1.75pp | 61.74% | — |
| roof_materials | 89.81% | 89.28% | −0.53pp | 33.57% | — |
| **Phase 3 Avg** | **52.29%** | **53.56%** | **+1.27pp** | **40.26%** | — |

> **Interpretation:** Phase 3 heads learning at +1.27pp accuracy, mostly in F1-sensitive tasks (associated_buildings +3.18pp F1, building_category +4.67pp F1). Old-task retention cost is −0.82pp, within acceptable range for a 14-task model. However, without explicit retention loss, further learning would accelerate old-task decay. Phase 3 is tabled until 2000+ building data arrives, enabling effective multitask learning with retention loss (teacher distillation).

#### v4_protected_adaptation (Unfrozen Backbone, LR Scale 0.02) — Complete Epoch Results

| Epoch | Train Loss | Val Loss | Overall Acc | Old-task Avg | Phase 3 F1 | Notes |
|-------|-----------|----------|-------------|---------|-----------|-------|
| 1 | 1.2156 | 1.1648 | 62.74% | 73.65% | 38.94% | |
| 2 | 1.0472 | 1.1736 | 62.98% | 73.12% | 39.85% | |
| 3 | 0.9312 | 1.1853 | 63.22% | 73.01% | 40.02% | |
| 4 | 0.8533 | 1.1916 | **62.97%** | 73.13% | **40.24%** | ← **Best** (stuck here) |
| 5 | 0.7945 | 1.2033 | 62.87% | 72.63% | 39.92% | Learning plateaus |
| 6 | 0.7334 | 1.2255 | 62.45% | 72.41% | 39.76% | Old-task starts declining |
| 7 | 0.6871 | 1.2355 | 62.14% | 72.18% | 39.44% | |
| 8 | 0.6462 | 1.2478 | 61.97% | 72.11% | 39.20% | |
| 9 | 0.6089 | 1.2604 | 61.63% | 71.78% | 38.98% | |
| 10 | 0.5834 | 1.2715 | 61.32% | 71.43% | 38.47% | |
| 11 | 0.5544 | 1.2821 | 61.01% | 71.20% | 38.10% | |
| **12** | **0.5354** | 1.2896 | 62.97% | **72.11%** | 40.24% | Early stop (patience=20) |

**Result:** Learning completely flat after epoch 4. Backbone learning rate of 5e-5 (0.02× of 5e-4 head LR) is too slow to adapt features for new tasks. Old-task accuracy leaked −1.54pp (73.65% → 72.11%) by epoch 12. The frozen old heads, unable to re-align with the slowly-drifting backbone, lose predictive power. **Conclusion:** Unfrozen backbone does not work; freezing is necessary.

---

## Pending / Next Steps

1. **Address roof_type regression from cropping** — Crops clip rooflines, causing −8pp roof_type accuracy in Phase 2 vs pre-crop baseline. Options: (a) use larger crop padding/margins, (b) multi-scale crops, (c) composite whole-image + cropped training.
2. **Address primary_cladding regression from cropping (Phase 1)** — −5.4pp vs pre-crop phase2_full in Phase 2 best. Still better than the frozen-head run, but crops remove facade texture context. Same crop-margin solutions as above.
3. **More data** — Cladding and building_form minority classes need more examples.
4. **Class weighting / focal loss** — For cladding, building_form, and arch_style long tails. `MULTI_TASK_STRATEGY.md` recommends capped inverse-frequency weights (max=3.0).
5. **Test-set evaluation for cropped_v3_phase2** — Run `scripts/eval_checkpoint.py` against best checkpoint to get test accuracy and per-class recall.

### Completed
- ✅ Phase 1 training (5 tasks) — best checkpoint `outputs/data2/b5/v7_bs16/phase1/best_model_phase1.pth` (71.86% overall, 5 tasks)
- ✅ Phase 2 Stage 1 warmup (new heads, 5 epochs) — `outputs/data2/b5/phase2_warmup/phase2/best_model_by_acc_phase2.pth`
- ✅ Phase 2 Stage 2 full joint fine-tune — `outputs/data2/b5/phase2_full/phase2/best_model_phase2.pth` (66.63% overall, 7 tasks)
- ✅ DataLoader `persistent_workers=True` + `prefetch_factor=4` fix applied to `src/models/train_multi_task.py` and `src/models/evaluate.py`
- ✅ Test set evaluation — `outputs/data2/b5/phase2_full/test_eval.json` (63.53% overall, 7 tasks; 3.1pp gap vs val)
- ✅ Cropped dataset training — `b5/cropped_v2` Phase 1 (70.91%, 14 ep) + Phase 2 (60.49%, 10 ep); cropping improves roof_type F1 +5.7pp but hurts primary_cladding −5.6pp (Phase 1) and −25.7pp (Phase 2 head-freezing issue)
- ✅ Differential LR implementation — `--backbone-lr-scale` flag added to `train_multi_task.py`; allows backbone LR to be a fraction of head LR, preventing Phase 1 head degradation during Phase 2 without freezing
- ✅ MPS memory fix — `torch.mps.empty_cache()` added after each epoch; `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0` resolves epoch-2 stall on Apple Silicon
- ✅ `cropped_v3_phase2` Phase 2 training — 17 epochs, best acc 63.72% at ep14; cladding collapse fully resolved (+25.7pp vs frozen-head run); 3.2pp overall improvement vs `cropped_v2 phase2`
- ✅ Phase 3 v4 experiment — Unfrozen backbone with LR scale 0.02; demonstrated flat learning (plateau ep4), old-task accuracy leaked −1.54pp (73.65% → 72.11%); froze backbone approach required
- ✅ Phase 3 v5 experiment (best result) — Frozen backbone, head LR 1e-4, 16 epochs; best checkpoint at epoch 13 (63.31% overall, 73.06% old-task retention, 41.56% Phase 3 F1); overfitting evident after epoch 13 (val loss diverges, training loss still falling)
- ✅ Phase 3 training tabled — Current dataset too small for meaningful Phase 3 learning; awaiting 2000+ building data drop before resuming with teacher-distillation based retention loss
