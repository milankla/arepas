# Arepas — Training Run History

**Last updated:** May 4, 2026  
**Dataset:** `data2/image_label_mapping_phase1.csv` — 759 buildings / 2,708 images  
**Split (fixed seed=42):** train 1,911 | val 409 | test 388 images  
**Active Phase 1 tasks:** stories, roof_type, primary_cladding, chimney_present, setting

---

## Current Best Models

| Rank | Run | Backbone | Overall Acc | Cladding Acc | Cladding F1 |
|------|-----|----------|-------------|--------------|-------------|
| 🥇 | **b5/v7_bs16** | EfficientNet-B5 | **71.86%** | 59.66% | 22.9% |
| 🥈 | v7 | ResNet50 | 71.35% | 55.50% | 23.5% |
| 🥉 | grid lr=1.1e-4 wd=0.010 | EfficientNet-B5 | 68.51% | 46.45% | 20.8% |

**Note on cladding F1:** All models have low cladding F1 (~20–24%) despite reasonable accuracy because Brick dominates at ~68% of samples. The model largely defaults to predicting Brick. This is a known class imbalance problem pending more data.

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
| **b5/v7_bs16** | 2026-05-04 | 1.5e-4 | 16 | 0.01 | 25 / 13 | yes (pat=10) | 8 (coarsened) | **71.86%** | 59.66% | **New overall best**; stopped ep 13, best ep 11 |

#### b5/v7_bs16 Final Per-Task Breakdown (best epoch = 11)

| Task | Accuracy | Macro F1 |
|------|----------|----------|
| stories | 73.59% | 38.89% |
| roof_type | 52.81% | 36.21% |
| primary_cladding | 59.66% | 22.91% |
| chimney_present | 92.42% | 48.03% |
| setting (Jaccard) | 80.81% | 24.01% |
| **Overall** | **71.86%** | — |

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
- **B5 bs=16 (v7_bs16): 71.86%** — new overall best; batch=16 gave more stable gradients vs bs=8
- ResNet50 (v7): 71.35% — strong baseline, trains faster per epoch
- B5 best grid (bs=8, lr=1.1e-4): 68.51% — batch=8 too noisy for B5 capacity
- B5 batch=4 (v1): seemed better (69.45%) but suspected overfitting; early stopping not active

### Why batch=16 helped B5
Scaling LR by √2 (1.1e-4 → 1.5e-4) with batch doubling (8→16) follows linear scaling rule. The larger batch reduced gradient noise, allowing B5's stochastic depth and wider layers to converge more reliably. Stopped at epoch 13 (patience=10), best at epoch 11.

---

## Pending / Next Steps

1. **More data** — Cladding minority classes need more examples before revisiting 18-class scheme
2. **Phase 2 tasks** — architectural_style, building_form, roof_features, wall_features not yet trained
3. **Class weighting for cladding** — When more data arrives, try `pos_weight` / focal loss before reverting coarsening
4. **B5 bs=16 LR grid** — v7_bs16 used a single LR (1.5e-4); a small grid around 1.3e-4–1.7e-4 may squeeze out more
5. **B5 bs=32** — Further batch scaling test (LR ~2.1e-4) to see if gradient stability continues to help
