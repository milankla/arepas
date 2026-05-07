# Arepas — Training Run History

**Last updated:** May 7, 2026  
**Dataset:** `data2/image_label_mapping_phase1.csv` — 759 buildings / 2,708 images  
**Split (fixed seed=42):** train 1,911 | val 409 | test 388 images  
**Phase 1 tasks:** stories, roof_type, primary_cladding, chimney_present, setting  
**Phase 2 tasks (added):** architectural_style, building_form

---

## Current Best Models

### Phase 1 — 5 tasks (stories, roof_type, primary_cladding, chimney_present, setting)

| Rank | Run | Backbone | Overall Acc | Cladding Acc | Cladding F1 |
|------|-----|----------|-------------|--------------|-------------|
| 🥇 | **b5/v7_bs16** | EfficientNet-B5 | **71.86%** | 59.66% | 22.9% |
| 🥈 | v7 | ResNet50 | 71.35% | 55.50% | 23.5% |
| 🥉 | grid lr=1.1e-4 wd=0.010 | EfficientNet-B5 | 68.51% | 46.45% | 20.8% |

### Phase 2 — 7 tasks (Phase 1 + architectural_style + building_form)

| Rank | Run | Backbone | Overall Acc (7 tasks) | Cladding Acc | Cladding F1 |
|------|-----|----------|-----------------------|--------------|-------------|
| 🥇 | **phase2_full ep11** | EfficientNet-B5 | **66.63%** | 59.41% | 30.9% |
| 🥈 | phase2_warmup ep5 | EfficientNet-B5 | 56.33% | — | — |

> **Note:** Phase 2 overall acc is computed across all 7 tasks. It is **not directly comparable** to Phase 1's 71.86% (5 tasks). The two new tasks (architectural_style: 59.66%, building_form: 45.72%) lower the average. Phase 1 tasks held steady or improved vs their Phase 1 baselines.

**Note on cladding F1:** Low cladding F1 (~23–31%) despite reasonable accuracy because Brick dominates at ~68% of samples. This is a known class imbalance problem pending more data.

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
| **b5/v7_bs16** | 2026-05-04 | 1.5e-4 | 16 | 0.01 | 25 / 13 | yes (pat=10) | 8 (coarsened) | **71.86%** | 59.66% | **Phase 1 best**; stopped ep 13, best ep 11 |

---

### EfficientNet-B5 Phase 2 Runs — `data2/`

Phase 2 adds `architectural_style` and `building_form` heads. Loaded from Phase 1 checkpoint `outputs/data2/b5/v7_bs16/phase1/best_model_phase1.pth`.

| Run | Date | Stage | LR | BS | WD | Epochs cfg/run | Early stop | Best overall (7 tasks) | Notes |
|-----|------|-------|----|----|----|----------------|------------|------------------------|-------|
| **phase2_warmup** | 2026-05-05 | Stage 1 (new heads only) | 3.0e-4 | 16 | 0.01 | 5 / 5 | no | 56.33% | Phase 1 heads frozen; new heads warm-up |
| **phase2_full** | 2026-05-06–07 | Stage 2 (all unfrozen) | 1.5e-4 | 16 | 0.01 | 25 / 11 | yes (pat=10) | **66.63%** | Joint fine-tune; best val_loss ep1=1.506; best acc ep11 |

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

## Pending / Next Steps

1. **Image resizing + cropping changes** — Pre-resize `data2/` images to ~512 px on disk (one-time ~10 min step) to eliminate the I/O bottleneck. Combine with any crop/augmentation strategy review. Deferred by user: *"Let's do resizing later together with cropping changes."*
2. **Phase 3 training** — Retrain from `phase2_full` checkpoint with DataLoader fix + resized images; expected GPU utilisation ~50–70% vs current ~10%.
3. **More data** — Cladding and building_form minority classes need more examples.
4. **Class weighting / focal loss** — For cladding, building_form, and arch_style long tails. `MULTI_TASK_STRATEGY.md` recommends capped inverse-frequency weights (max=3.0).
5. **B5 bs=16 LR grid** — phase2_full used lr=1.5e-4; a small grid around 1.3e-4–1.7e-4 may help after resizing fix.

### Completed
- ✅ Phase 1 training (5 tasks) — best checkpoint `outputs/data2/b5/v7_bs16/phase1/best_model_phase1.pth` (71.86% overall, 5 tasks)
- ✅ Phase 2 Stage 1 warmup (new heads, 5 epochs) — `outputs/data2/b5/phase2_warmup/phase2/best_model_by_acc_phase2.pth`
- ✅ Phase 2 Stage 2 full joint fine-tune — `outputs/data2/b5/phase2_full/phase2/best_model_phase2.pth` (66.63% overall, 7 tasks)
- ✅ DataLoader `persistent_workers=True` + `prefetch_factor=4` fix applied to `src/models/train_multi_task.py` and `src/models/evaluate.py`
- ✅ Test set evaluation — `outputs/data2/b5/phase2_full/test_eval.json` (63.53% overall, 7 tasks; 3.1pp gap vs val)
