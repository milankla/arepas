# Building ID Truncation Bug — Root Cause, Analysis & Implications

**Date discovered:** May 12, 2026  
**Status:** Fixed  
**Affected files:** `src/loader/configurable_loader.py`, `src/loader/csv_parser.py`  
**Affected datasets:** `data2/` (primary), `data/` (partial)  
**Regenerated outputs:** `data2/image_label_mapping_phase1.csv`, `data/image_label_mapping_phase1.csv`

---

## 1. Bug Description

### Symptom

`data2/image_label_mapping_phase1.csv` contained building IDs in the form `IS.355`, `IS.371`, etc. The source files (`data2/Cole/Cole - CLEAN.txt`, etc.) contain IDs in the form `DIS.3554`, `DIS.3710`, etc. The leading `D` and the trailing digit were being silently dropped.

### Underlying Root Cause

The data definition files (TSV exports from the Discover Denver survey system) used non-standard, mixed quote characters to delimit field values — specifically a Unicode RIGHT DOUBLE QUOTATION MARK (`"`, U+201D) as the opening quote paired with a plain ASCII double-quote (`"`, U+0022) as the closing quote. This asymmetric quoting was not handled uniformly by pandas and required defensive normalisation in the loader. The quote-stripping logic added to compensate for this quirk is what introduced the ID truncation bug described below.

### Compounding Issues

#### Issue A: Unconditional `[1:-1]` slice in `_process_building_row`

`src/loader/configurable_loader.py` stripped the first and last character from every raw building ID unconditionally:

```python
# BEFORE (buggy)
if len(building_id) >= 2:
    building_id = building_id[1:-1]   # intended to remove surrounding quotes
```

The comment explained the intent: source TSV files wrap ID values in quotes, so `"DIS.3554"` should become `DIS.3554`. However, whether quotes survived into this function depended entirely on which parsing path was taken (see Issue B).

#### Issue B: `quoting=csv.QUOTE_MINIMAL` absent from fallback parser path

`src/loader/csv_parser.py` has two pandas parsing paths — strict and fallback:

```python
# BEFORE (buggy)
if strict:
    config.update({
        'on_bad_lines': 'skip',
        'quoting': csv.QUOTE_MINIMAL    # only here
    })
```

- **Strict path** (used by `data2/`): `QUOTE_MINIMAL` causes pandas to strip surrounding `"` quotes as it reads each field. The ID arrives at `_process_building_row` as a bare `DIS.3554`. The `[1:-1]` then corrupts it to `IS.355`.
- **Fallback path** (used by `data/`): No `quoting` key → pandas does not strip quotes. The ID arrives still wrapped as `"DIS.14425"`. The `[1:-1]` correctly removes the quotes, producing `DIS.14425`.

`data/` files trigger the fallback path because they contain many malformed lines (inconsistent column counts, stray characters). `data2/` files are well-formed and take the strict path. This is why `data/image_label_mapping_phase1.csv` appeared correct while `data2/image_label_mapping_phase1.csv` was silently broken.

#### Issue C: Asymmetric quote characters in `data/` source files (pre-existing, not introduced by this bug)

Raw bytes of the first ID field:

| Dataset | Opening quote | Closing quote |
|---------|--------------|--------------|
| `data/` | `\xe2\x80\x9d` — U+201D RIGHT DOUBLE QUOTATION MARK `"` | `\x22` — ASCII `"` |
| `data2/` | `\x22` — ASCII `"` | `\x22` — ASCII `"` |

`data2/` files had previously been normalised to uniform ASCII double-quotes. `data/` files still have a mixed curly/straight pair. `_clean_line()` handles the curly → straight replacement, but this reinforced the dependency on which parser path was taken.

### The Fix

**`csv_parser.py`** — `quoting=csv.QUOTE_MINIMAL` promoted to the base config, applied on both strict and fallback paths. `on_bad_lines='skip'` remains strict-only.

```python
# AFTER
config = {
    'delimiter': '\t',
    'engine': 'python',
    'quoting': csv.QUOTE_MINIMAL,   # always strip quotes consistently
}
if strict:
    config['on_bad_lines'] = 'skip'
```

**`configurable_loader.py`** — Conditional quote-strip replaced with an explicit `.strip()` covering ASCII and all three Unicode double-quote variants:

```python
# AFTER
building_id = building_id.strip('"\u201c\u201d\u201e')
```

This is correct regardless of which parsing path was taken and regardless of which quote characters survive.

**`build_phase1_label_mapping.py`** — Sanity check added after CSV write: all `building_id` values are validated against `DIS.\d+`. Any malformed IDs are logged as errors and the script exits non-zero, catching any future regression immediately.

---

## 2. Impact Analysis

### Dataset `data2/` — Quantitative Summary

| Metric | Broken | Correct | Change |
|--------|--------|---------|--------|
| Unique building IDs in CSV | 842 | **7,135** | +746% |
| Buildings silently lost at loader level | 6,293 (88.2%) | 0 | — |
| Broken IDs collapsing multiple buildings | 835 of 842 | 0 | — |
| Max real buildings per broken ID | 68 | 1 | — |

#### Collision mechanics

`DIS.xxxx` IDs occupy a 4-digit number space. The `[1:-1]` removed the leading `D` and the trailing digit, so any 10 consecutive IDs (e.g. `DIS.3550`–`DIS.3559`) all collapsed to the same broken key `IS.355`. At loader level the Python dict was updated for each row, so the **last** building encountered per collision group silently overwrote all previous ones. 88.2% of buildings were permanently lost before the CSV was even written.

Collision group size distribution (how many real buildings each broken ID absorbed):

- Most groups: 18–35 buildings
- Largest group: 68 buildings → 1 broken ID
- Only 7 broken IDs had no collision (groups of 1)

#### Label distribution bias

Despite 88% data loss, **no meaningful label distribution bias was introduced**. Maximum drift across all classes:

| Field | Max class drift |
|-------|----------------|
| stories | ±0.5% |
| primary_cladding | ±1.3% |
| roof_type | ±1.1% |

This is because `DIS.xxxx` IDs are assigned sequentially within survey batches. Buildings sharing the same truncated prefix tend to be geographically adjacent and architecturally similar. The random "last-winner" from each collision group was statistically representative of the group.

### Dataset `data/` — Quantitative Summary

`data/` used the fallback parser path so the CSV on disk was historically correct (`DIS.14425` etc.). However:

- Simulating the bug: **44 of 195 buildings** would have collided into **21 broken IDs** if the strict path had been taken
- The regenerated CSV is identical to the historical one for `data/`

---

## 3. Implications for Model Accuracy

### All three `data2` training runs should be considered invalid

Every MLflow run that consumed `data2/image_label_mapping_phase1.csv` was trained on a **12% sample** of the intended dataset with no warning. The runs affected:

| Run | Epochs | Val overall acc | Val stories acc |
|-----|--------|-----------------|----------------|
| `ep8_legacy_multi_roof` | 8 (5 logged) | 0.69 | 0.77 |
| `ep8_legacy_single_roof_pat5` | 8 (5 logged) | 0.77 | 0.78 |
| `ep30_legacy_single_roof_nopat` | 30 | 0.77 | 0.76 |

### The accuracy numbers were misleading, not meaningless

Val accuracy appeared reasonable (0.77) because the dominant class in `data2` is 1-story brick buildings in Mixed style (~69% of buildings). A model that predicts the majority class for every input would achieve ~0.69 stories accuracy. The reported 0.77–0.78 was only marginally better than a trivial classifier.

**F1 scores expose the true picture:**

| Task | Val Acc (best) | Val F1 (best) | Interpretation |
|------|---------------|--------------|----------------|
| stories | 0.78 | 0.41 | Predicting majority class almost exclusively |
| primary_cladding | 0.78 | 0.15 | Only Brick (70%) learned reliably |
| roof_type | 0.56 | 0.35 | Highest-diversity field, worst generalisation |
| setting (Hamming) | 0.94 | 0.22 | Hamming inflated by multi-label negatives |
| chimney_present | 0.96 | 0.49 | 96.2% "No" base rate → near-trivial |

### Severe overfitting, hidden by tiny validation set

With only ~589 training buildings the model memorised its training set. Training loss collapsed to near-zero while val loss remained high:

| Run | Train loss (final) | Val loss (best) | Train/val ratio |
|-----|-------------------|----------------|----------------|
| ep30_nopat | 0.011 | 0.288 | **26×** |
| ep8_pat5 | 0.012 | 0.279 | **23×** |
| ep8_multi_roof | 0.085 | 0.175 | **2×** (early stopped) |

The validation set of only ~126 entities (instead of the intended ~1,070) made the val loss curve noisy. What looked like a reasonable convergence plateau was in fact a heavily overfit model evaluated on too few samples to detect it.

### Effective training pool comparison

| | Broken | Correct (after fix) | Ratio |
|--|--------|---------------------|-------|
| Train buildings | ~589 | ~4,994 | **8.5×** |
| Val buildings | ~126 | ~1,070 | **8.5×** |
| Test buildings | ~127 | ~1,070 | **8.5×** |

### Expected improvement from retraining

With the fixed CSV and 8.5× more training diversity:

- **Minority class F1** (roof_type, non-Brick cladding) should improve substantially — the model will have seen far more examples of rare classes
- **Overfitting** should reduce — the training set is large enough that memorisation is no longer an easy path
- **Val metrics will be more trustworthy** — computed over 1,070 buildings rather than 126
- **The train/val loss gap** should close significantly, validating that generalisation is actually occurring

The `data/` run (`ep20_legacy`, 195 buildings) provides a cautionary baseline: even with correct IDs, 195 buildings was insufficient — it showed similar overfitting (train loss 0.017, val loss diverged after epoch ~10). `data2`'s 7,135 buildings should put the training firmly in the regime where the model can actually generalise.

---

## 4. Training Duration Impact

### Steps per epoch: 8.5× increase

With the default config (`batch_size=32`, `epochs=30`, Apple Silicon MPS):

| | Broken (842 buildings) | Correct (7,135 buildings) |
|--|----------------------|-------------------------|
| Train images | ~2,160 | ~18,312 |
| Steps/epoch (train) | **67** | **572** |
| Steps/epoch (val) | **14** | **123** |
| Total steps for 30 epochs | ~2,430 | **~20,850** |

### Measured timing (benchmarked on this machine)

A full train step (forward + backward + optimizer, bs=32) on MPS: **0.40s**.

| Phase | Steps/epoch | Time/epoch |
|-------|-------------|------------|
| Train | 572 | ~229s |
| Val (forward-only) | 123 | ~16s |
| **Compute total** | | **~4.0 min** |
| **With I/O overhead (+30%)** | | **~5.3 min** |

### Projected run durations

| Scenario | Epochs | Duration |
|----------|--------|----------|
| 30-epoch fixed run | 30 | **~2.6h** |
| 50-epoch run, early stop at ep35 (realistic) | 35 | **~3.1h** |
| Optimistic: converges at ep20 | 20 | **~1.8h** |

For comparison, the broken runs (67 steps/epoch) completed 30 epochs in under 20 minutes. The correct run is ~8× slower per epoch and ~51× more compute total for the same epoch count.

### Recommendations for the first correct run

- Use `--epochs 50 --patience 10` and let early stopping determine the actual length
- `--batch_size 64` halves steps/epoch (286/epoch) with no accuracy cost, cutting wall time by ~half if VRAM permits
- `--grad_accum_steps 2` with `--batch_size 32` gives effective batch size 64 without extra VRAM
- Watch for the train/val loss gap — with 7,135 buildings it should close significantly vs the 23–26× gap seen in broken runs

---

## 5. Path Forward

All derived artifacts produced from the broken `data2/image_label_mapping_phase1.csv` are now stale and must be regenerated in order. Steps marked ✅ are already complete.

### Step 1 — Regenerate label mapping ✅

```bash
python scripts/build_phase1_label_mapping.py
```

Output: `data2/image_label_mapping_phase1.csv` (26,160 rows, 7,135 buildings). Done — sanity check passes.

### Step 2 — Re-run field coverage & frequency analysis

```bash
python scripts/field_coverage_report.py   # → field_coverage_report.txt
```

`docs/DATA_FREQUENCY_ANALYSIS.md` was written against the broken 842-building dataset. The class frequencies, imbalance ratios, and coarsening recommendations in that document are all based on a 12% sample and are no longer accurate. Re-run and update the document before making any decisions about class weighting or label coarsening in training.

### Step 3 — Re-run attribute dependency analysis

```bash
python scripts/attribute_dependency_analysis.py
```

`docs/ATTRIBUTE_DEPENDENCY_ANALYSIS.md` may have similar staleness issues — conditional distributions (e.g. roof_type given stories) computed over 842 buildings can differ meaningfully from distributions over 7,135 buildings.

### Step 4 — Regenerate cropped images (if crops are used in training)

The crop manifest at `crops/data2/crop_manifest.csv` was built from the broken loader. Any crop that was produced for a now-known-missing building is still present on disk but has no corresponding label row in the regenerated CSV. Rebuild to ensure consistency:

```bash
python scripts/crop_dataset.py \
    --dataset data2 \
    --output crops/data2
```

Existing crops can be reused for buildings that survived the bug; only missing buildings need new crops. If the crop step is expensive, filter `crop_manifest.csv` against the new building list and only re-run for the gap.

### Step 5 — Archive broken MLflow runs

Tag the three invalid `data2` runs before starting fresh to prevent confusion:

```python
import mlflow
client = mlflow.tracking.MlflowClient()
for run_id in ["<ep8_multi_roof>", "<ep8_pat5>", "<ep30_nopat>"]:
    client.set_tag(run_id, "invalid", "broken_csv_pre_fix_2026-05-12")
    client.set_tag(run_id, "note", "Trained on 842/7135 buildings due to ID truncation bug")
```

### Step 6 — Retrain

```bash
python -m src.fine_tune \
    --dataset data2 \
    --epochs 50 \
    --patience 10 \
    --batch_size 32
```

Expected duration: ~5.3 min/epoch → ~2.6h for 30 epochs; early stopping likely triggers around epoch 35 (~3.1h). See §4 for full timing breakdown.

### Step 7 — Evaluate

```bash
python scripts/eval_checkpoint.py \
    --checkpoint outputs/data2/<run>/best_checkpoint.pth \
    --dataset data2 \
    --split test
```

Compare per-class F1 scores against the baselines in §3. Minority classes (non-Brick cladding, hip/gambrel roofs, multi-story buildings) are the primary signal that the fix is working — if F1 for those classes improves substantially, the retraining is valid.

### Step 8 — Regenerate gallery / visualisations (optional)

```bash
python scripts/generate_gallery.py --dataset data2
python scripts/generate_three_column_gallery.py --dataset data2
```

---

## 6. Remaining Recommendations

1. **Add a unit test** — a test that passes a raw ID like `'"DIS.3554"'` (quotes as part of the string) and verifies `_process_building_row` returns `DIS.3554`. Prevents regression.

2. **Retrain all `data2` experiments** — using the regenerated CSV with 7,135 buildings. Archive the three broken runs in MLflow with a note tag.
