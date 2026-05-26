

**Executive Read**
Your current ceiling is no longer the old May 11 number. Based on outputs plus outputs_archived, the current best validation results are:

| Scope | Best Run | Overall |
|---|---:|---:|
| Phase 1 / 5 easier tasks | `b5_crop_v1/phase1` | **79.87%** |
| Phase 1 full images | `b5_full_v1/phase1` | **78.65%** |
| Phase 2 / 7 tasks | `b5_crop_v3/phase2` | **75.87%** |
| Phase 2 full images | `b5_full_v3/phase2` | **75.58%** |

The biggest historic lift came from **EfficientNet-B5 + 456px + larger current dataset + label coarsening + crops**. That moved you from the older ResNet/B5 baselines around 66-72% into the 75-80% band.

I would **not abandon multi-stage training**, but I would stop thinking of it as “freeze phase 1 and protect it.” The successful pattern is: warm start from the best phase 1 checkpoint, keep all relevant heads adaptable, use cautious backbone movement, and stop early.

**Top 5 Improvements**

| Priority | Recommendation | Expected Overall Accuracy Lift |
|---:|---|---:|
| 1 | **Use a crop/full multi-scale inference or task-routed model** | **+0.7 to +2.0pp** |
| 2 | **Fix the phase-2 training protocol: no frozen heads with trainable backbone; use staged LR groups** | **+0.5 to +1.5pp over current best; +8-9pp vs v5-style freeze failure** |
| 3 | **Reduce multi-task interference in the style group branch** | **+1.0 to +2.5pp** |
| 4 | **Improve class imbalance handling for architectural_style/building_form/roof/cladding** | **+0.5 to +1.5pp accuracy; +5-12pp macro-F1** |
| 5 | **Improve labels/classes: coarsen building_form, audit noisy style labels, add targeted data for tails** | **+1.5 to +4.0pp** |

**1. Multi-Scale Crop + Full Strategy**
The crop and full-image runs are complementary, not one strictly better than the other.

From current best phase 2:

| Task | Crop v3 | Full v3 | Winner |
|---|---:|---:|---|
| architectural_style | **71.98%** | 71.22% | crop |
| building_form | **65.38%** | 63.71% | crop |
| primary_cladding | **76.49%** | 74.31% | crop |
| stories | **75.72%** | 73.60% | crop |
| roof_type | 63.69% | **64.87%** | full |
| setting | 83.02% | **86.34%** | full |
| chimney_present | 94.83% | **94.98%** | tied/full |

A simple task-routed ensemble using crop predictions for facade/style tasks and full-image predictions for setting/roof/chimney would score roughly **76.5%** from existing checkpoints, before any new training. A learned two-branch model could plausibly push that to **77-78%**.

Best next experiment:
- Use crop model for `architectural_style`, `building_form`, `primary_cladding`, `stories`
- Use full model for `setting`, maybe `roof_type`, `chimney_present`
- Evaluate on the same val/test split before training anything new

**2. Fix Phase-2 Training Protocol**
The v5 run proves the failure mode: frozen heads do not preserve phase 1 if the backbone moves. Worse, current checkpoint metadata includes heads that are not actually active in phase 1 metrics, so `--freeze-phase1-heads` can freeze the wrong things or freeze too much.

What worked empirically:
- `b5_crop_v3/phase2`: **75.87%**
- `b5_full_v3/phase2`: **75.58%**
- Both are better than the v5 freeze-style path: **66.81%**

Recommended protocol:
1. Start from `b5_crop_v1/phase1` or `b5_full_v1/phase1`.
2. Do **not** freeze old heads while backbone trains.
3. Use differential LR groups:
   - backbone: `5e-6` to `1e-5`
   - old heads: `1e-5`
   - new/style heads: `5e-5` to `1e-4`
   - optionally `style_group_fc`: its own low/mid LR, because it affects roof/style/form together
4. Early stop around epoch 3-15, because most phase 2 runs peak early.

Expected lift over current best is modest, **+0.5 to +1.5pp**, but it mainly reduces regressions and avoids expensive dead runs.

**3. Reduce Style-Group Interference**
The shared `style_group_fc` in multi_task_classifier.py connects `roof_type`, `architectural_style`, and `building_form`. That is principled because the labels are correlated, but the runs show real gradient conflict:

- `roof_type` often regresses during phase 2
- `architectural_style` and `building_form` dominate the shared branch
- `building_form` is almost label-redundant with style but has 39 classes, so it can inject noisy gradients

Best architectural improvement:
- Keep a shared style feature, but add task-specific adapters:
  - shared `style_group_fc`
  - plus small per-task residual adapters for `roof_type`, `architectural_style`, `building_form`
- Or use PCGrad / GradNorm / uncertainty weighting to reduce conflicting task gradients.

Expected lift: **+1.0 to +2.5pp**, mostly by recovering `roof_type` and stabilizing phase 2.

**4. Fix Imbalance Handling Where It Is Still Incomplete**
The docs in MULTI_TASK_STRATEGY.md recommend capped inverse-frequency weights. The loader computes capped weights in architectural_dataset.py, but the loss code only applies those weights to tasks marked with focal loss.

That means the biggest hard tasks, especially:
- `architectural_style`
- `building_form`

are still likely under-optimized for minority classes.

Given the active data distribution:
- `architectural_style`: 37 raw classes, dominated by “No Clear Architectural Style”
- `building_form`: 39 raw classes, long tail
- `primary_cladding`: Brick is ~69%
- `chimney_present`: Yes is only ~4%

Accuracy lift may be small, **+0.5 to +1.5pp**, but macro-F1 could improve much more, **+5-12pp**, which matters if you care about rare styles/forms rather than just the dominant classes.

**5. Improve Label Taxonomy Before Bigger Modeling**
This is the highest-ceiling data science move. `building_form` has 39 raw classes and currently tops out around **63-66%**. Some of that is model difficulty, but a lot is taxonomy granularity and overlap with `architectural_style`.

I would:
- Coarsen `building_form` into fewer visually separable groups
- Keep rare style classes collapsed unless there are enough examples
- Audit “No Clear Architectural Style”, “Mixed Style”, and “Other” labels
- Add targeted examples for tail classes instead of only adding more majority examples
- Keep `alteration_level` out until it is coarsened or relabeled

Expected lift:
- **+1.5 to +4.0pp overall**
- larger gains on `building_form` specifically, likely **+4 to +8pp**

**Bottom Line**
Do not switch to flat “train everything at once” as the main strategy. Your best phase 2 models already come from a phase 1 warm start. The better path is:

1. Use current best checkpoints as baseline: `b5_crop_v3` and `b5_full_v3`.
2. Evaluate crop/full task-routing immediately.
3. Fix phase-2 LR groups and freezing behavior.
4. Add task-conflict mitigation around `style_group_fc`.
5. Improve long-tail label handling, especially `building_form`.

Realistic near-term target without new labels: **77-78% validation overall**.
With better taxonomy and targeted data/label cleanup: **79-81%** is plausible.


----------------

Q: instead of 1. Multi-Scale Crop + Full Strategy, would just training with mix of full/cropped images be better?

A: Short answer: **yes, training with a mix of full + cropped images is probably the better next experiment than only doing crop/full task routing**, because it is simpler operationally and may let one model learn both facade detail and context cues.

But I would be careful about *how* you mix them.

**Best version: paired multi-view training, not naive mixing.**

Naive mixing means treating this as ordinary augmentation:

```text
same building label + either full image or crop image
```

That might help robustness, but it also creates a problem: the model sees two image distributions with different visual framing, and task needs are not equal. `setting` wants full context; `cladding/stories` want crop detail; `architectural_style` seems to benefit from both. If mixed randomly without telling the model which view it is seeing, it may average the two regimes and land between the best crop and best full checkpoints.

A better design:

```text
For each training sample:
  use both views when available:
    full image branch -> context features
    crop image branch -> facade/detail features
  fuse features before task heads
```

That is a true multi-scale / paired-view model. It should beat either single-view model if implemented cleanly.

**Expected outcomes:**

| Approach | Expected Lift vs Current Best 75.9% |
|---|---:|
| Simple random full/crop mixing | **0 to +1pp**, possible no gain |
| 50/50 mixed training with `view_type` embedding or augmentation flag | **+0.5 to +1.5pp** |
| Paired full+crop two-branch model | **+1.0 to +2.5pp** |
| Task-routed ensemble from existing checkpoints | **+0.5 to +1.0pp immediately, no training** |

So my revised recommendation would be:

1. **Immediate cheap check:** evaluate a task-routed ensemble using existing `b5_crop_v3` + `b5_full_v3`.
2. **Next real model experiment:** train a mixed full/crop model.
3. **Best longer-term experiment:** paired full+crop two-branch model.

For a first experiment, I’d do **mixed training as augmentation**, because it is lowest code cost:

```text
Each epoch, randomly choose crop or full image per sample.
Bias by task tradeoff:
  60-70% crop
  30-40% full
```

Why not 50/50? Current results show crops win most tasks, while full mainly wins `setting` and slightly `roof_type`. So I’d start at **70% crop / 30% full**.

Estimated lift: **+0.5 to +1.2pp overall**, with most gain coming from recovering `setting` without sacrificing too much `cladding/stories/style`.

If you want the highest-ceiling version, use a two-branch model. But if the question is “should we try mixed full/crop training before building an ensemble or two-encoder system?” — yes, that is a very reasonable next move.