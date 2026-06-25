# Phase 3 — Forward Plan

**Date:** June 24, 2026
**Status:** Phase 3 tabled (data-limited). This document captures the agreed plan
for when we return to Phase 3, derived from the field audit and the v1/v2/v4/v5
training results.

Source material:
- Field audit: [PHASE3_LABEL_AUDIT.md](PHASE3_LABEL_AUDIT.md), `outputs/phase3_label_audit/`
- Training results: [PROJECT_TRAINING_STATUS_JUN_2026.md](PROJECT_TRAINING_STATUS_JUN_2026.md)
- Per-label / calibration reports: `outputs/data2/phase3_per_label_reports/`

---

## What the results showed

### 1. The model over-predicts — precision is the bottleneck

Across every multi-label field, predicted positives exceed true support by a large
margin (calibrated thresholds, val split):

| Field | Pred / Support | Calibrated macro-F1 | Read |
|---|---|---|---|
| `window` | 34.9k / 23.8k (1.47×) | **0.50** | strongest |
| `entrance` | 16.4k / 10.0k (1.64×) | 0.44 | solid |
| `wall_features` | 17.3k / 10.4k (1.66×) | 0.42 | solid |
| `landscape_features` | 24.7k / 14.1k (1.75×) | 0.40 | moderate |
| `roof_materials` | 4.3k / 3.9k (1.10×) | 0.40 (acc ~88%) | minority dead |
| `associated_buildings` | 6.2k / 2.8k (2.22×) | **0.26** | weakest |

The per-label CSV confirms the pattern (e.g. `Belt Course` precision 0.45 / recall
0.81). Root cause: the multi-label BCE `pos_weight` clamp at **10.0** pushes recall
at the expense of precision. This is a **tuning lever, not a data wall** —
per-label threshold calibration alone already recovered +2–3pp.

### 2. A tail of labels is genuinely dead

`Driveway - Ribbon` (112 support, 0 TP), `Walkway - Brick` (87, 0 TP),
`Fence - Historic` (60, F1 0.03), `Rowlock Course` (F1 0.10). No learnable signal at
current volume; they drag macro-F1 down and should not be in the loss.

### 3. The "imbalance/use" fields are not really vision tasks

`building_category` (94.7% residential), `current_use` / `original_use`
(~82–84% single-dwelling) score high on accuracy but that is the majority-class
freebie — macro-F1 stays low because minority classes have 30–340 examples.
`roof_materials` is the same (88% asphalt).

### 4. Retention cost is small and architectural

v5 (frozen backbone + head LR 1e-4) lost only −0.82pp on old tasks and was the
stable winner; v4 (unfrozen, 0.02× LR) drifted. The ~41% F1 plateau is
**data-limited, not capacity-limited**.

---

## Plan for when we return to Phase 3

### A. Re-scope the fields (do not train all 7–9 at once)

- **Train (strong visual signal):** `window`, `entrance`, `wall_features`.
- **Train with pruning:** `landscape_features` — drop view-dependent / dead labels
  (ribbon driveways, historic fences, side-specific fences); keep
  walkways / driveways / front-fence / retaining-wall.
- **Coarsen, don't multiclass:** `roof_materials` → Asphalt / Tile / Metal / Other;
  `building_category` → binary Residential vs Non-residential.
- **Defer out of Phase 3:** `associated_buildings` (0.26 F1, 66% coverage,
  angle-dependent), `current_use`, `original_use` (function/history, not
  appearance). Track in audit reports only.

### B. Make label inclusion a hard, data-driven gate

Enforce a minimum positive threshold (config already defines
`minimum_initial_positive_buildings: 100` plus probation/exclude lists). Any label
under threshold is dropped from the loss automatically — not hand-maintained.
Re-run `scripts/phase3_label_audit.py` on the merged dataset first and promote
probation labels only when they cross the bar.

> Implemented as `PHASE3_MIN_POSITIVE_COUNT` in
> `src/loader/architectural_dataset.py` (default `0` = off). Set to the desired
> minimum (e.g. `100`) to enable the runtime gate.

### C. Fix precision before chasing more data

- Lower the multi-label `pos_weight` clamp from **10 → ~3–4**
  (`MULTILABEL_POS_WEIGHT_CLAMP` in `src/loader/architectural_dataset.py`).
- Make per-label threshold calibration on val a standard post-training step
  (script exists and works).

### D. Implement teacher-distillation retention loss

KL on old-task logits (λ ≈ 0.3) against the Phase 2 checkpoint so the backbone can
unfreeze safely. This is the architectural fix for the −0.82pp drift and should
lift the ceiling. (Already scoped in the June status report.)

### E. Gate everything on the data drop

Binding constraint: 759 buildings / 409 val images / 14 tasks. With 2000+
buildings, minority counts move from 50–100 → 300–500 and stratified splits become
possible. Sequence:

1. Merge `data2` + `data3` crops → re-run the label audit / counts.
2. Retrain Phase 1, then Phase 2 on merged data.
3. Train Phase 3 with the re-scoped field set + retention loss + calibrated
   thresholds + reduced `pos_weight` clamp.

---

## One-line summary

Return with a **narrower, precision-fixed scope** — train `window`, `entrance`,
`wall_features`, pruned `landscape_features`; coarsen `roof_materials` /
`building_category`; **drop** `associated_buildings`, `current_use`,
`original_use`; ship teacher-distillation retention loss + per-label threshold
calibration — all gated on the 2000+ building data drop.

---

## Tunable knobs already prepared (default-off / behavior-preserving)

| Knob | Location | Default | Forward-plan use |
|---|---|---|---|
| `MULTILABEL_POS_WEIGHT_CLAMP` | `src/loader/architectural_dataset.py` | `10.0` | Lower to ~3–4 to fix over-prediction (item C) |
| `PHASE3_MIN_POSITIVE_COUNT` | `src/loader/architectural_dataset.py` | `0` (off) | Set ~100 to drop dead labels from the loss (item B) |

---

## Performance follow-ups (do before the 2000+ building drop)

- **Vectorize multi-label `class_weights`.** The multi-label branch of
  `ArchitecturalDataset.class_weights` (`src/loader/architectural_dataset.py`)
  counts positives with a nested Python loop over *every class for every row*
  (`O(n × classes)`). Acceptable at 759 buildings; will be a hotspot at 2000+.
  Fix: reuse the already-fitted `MultiLabelBinarizer` —
  `enc.transform([parse_multilabel_value(col, v) for v in self.df[col]]).sum(axis=0)` —
  which removes the per-class scan (only the unavoidable per-row string parse
  remains) and runs the accumulation in numpy. The downstream
  `negatives`/`pos_weight`/clamp logic is unchanged. Add a one-row equivalence
  test asserting the vectorized counts match the current loop, and verify
  `transform` silently dropping out-of-class labels is intended (it is, for the
  `PHASE3_MIN_POSITIVE_COUNT` filtered-atomics case). `class_counts` is already
  `O(n × labels_per_row)` and does not need this.
