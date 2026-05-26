# Training and Evaluation Guide

End-to-end reference for training the multi-task architectural classifier,
evaluating checkpoints, and comparing runs in MLflow.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Training a Model](#training-a-model)
3. [Experiment Tracking with MLflow](#experiment-tracking-with-mlflow)
4. [Evaluating a Checkpoint](#evaluating-a-checkpoint)
5. [Comparing Runs](#comparing-runs)
6. [Scripts Reference](#scripts-reference)
7. [Backfilling Legacy Runs](#backfilling-legacy-runs)

---

## Quick Start

```bash
# Activate environment
source .venv/bin/activate

# Train on data2/ — output dir auto-derived from run params
python -m src.models.train_multi_task \
    --csv data2/image_label_mapping_phase1.csv \
    --model-config config/models/resnet50.json \
    --epochs 30 --batch-size 32 --lr 1e-4 --num-workers 2

# Open MLflow UI to review the run
mlflow ui --port 5001 --host 127.0.0.1 --backend-store-uri sqlite:///mlflow.db
```

---

## Training a Model

### Command

```bash
python -m src.models.train_multi_task \
    --csv <path-to-csv> \
    --model-config <path-to-model-config> \
    [options]
```

### All Options

| Flag | Default | Description |
|---|---|---|
| `--csv` | *(required)* | Label-mapping CSV (`data/` or `data2/`) |
| `--model-config` | `config/models/resnet50.json` | Backbone preset |
| `--start-phase` | `1` | First training phase (1–4) |
| `--end-phase` | `1` | Last training phase inclusive (1–4) |
| `--epochs` | `20` | Epochs per phase |
| `--batch-size` | `32` | Samples per GPU batch |
| `--lr` | `1e-4` | AdamW initial learning rate |
| `--num-workers` | `4` | DataLoader worker processes |
| `--output-dir` | *(auto)* | Root output dir; defaults to `runs/<slug>/` |
| `--run-name` | *(auto)* | Human-readable run name; auto-slugged if omitted |
| `--dataset-version` | *(auto)* | Short label for the dataset (e.g. `data2`) |
| `--early-stopping-patience` | *(disabled)* | Stop if val_loss doesn't improve for N epochs |
| `--max-batches` | *(disabled)* | Limit batches per epoch — useful for smoke tests |
| `--cropped-root` | *(disabled)* | Root of pre-cropped images; single-view training prefers crops when set |
| `--paired-views` | `false` | Train paired full-image + crop inputs instead of one image tensor |
| `--paired-fusion` | `concat_mlp` | Paired fusion mode: `concat_mlp`, `crop_residual`, or `task_gated_residual` |
| `--paired-gate-init` | `crop_prior` | Initial task-gate bias policy for `task_gated_residual` |
| `--paired-gate-overrides` | *(empty)* | Comma-separated task gate probabilities, e.g. `roof_type=0.03,stories=0.01` |
| `--paired-residual-scales` | *(empty)* | Comma-separated trainable full-residual scales, e.g. `roof_type=0.5,stories=0.25` |
| `--paired-crop-bypass-tasks` | *(empty)* | Comma-separated tasks that use crop features only, e.g. `stories` |

### Auto-slug Output Directory

When `--output-dir` is omitted the trainer generates a slug from the key
parameters and writes to `runs/<slug>/phase<N>/`:

```
runs/resnet50_data2_ph1-1_lr1e-04_bs32_ep30_b1529c5/phase1/
├── best_model_phase1.pth       ← checkpoint with lowest val_loss
├── checkpoint_epoch5.pth
├── checkpoint_epoch10.pth
├── run_config.json             ← full parameter snapshot
└── training_history.json       ← per-epoch metrics
```

### Typical Recipes

```bash
# Full 30-epoch run, no early stopping
python -m src.models.train_multi_task \
    --csv data2/image_label_mapping_phase1.csv \
    --epochs 30 --batch-size 32 --lr 1e-4 --num-workers 2

# With early stopping (stop if no improvement for 5 epochs)
python -m src.models.train_multi_task \
    --csv data2/image_label_mapping_phase1.csv \
    --epochs 30 --batch-size 32 --lr 1e-4 --num-workers 2 \
    --early-stopping-patience 5

# Lower learning rate experiment with a custom name
python -m src.models.train_multi_task \
    --csv data2/image_label_mapping_phase1.csv \
    --epochs 30 --batch-size 32 --lr 5e-5 --num-workers 2 \
    --run-name "lower-lr-5e5"

# Smoke test (3 batches per epoch, fast iteration)
python -m src.models.train_multi_task \
    --csv data2/image_label_mapping_phase1.csv \
    --epochs 2 --max-batches 3

# Log to a named output dir instead of auto-slug
python -m src.models.train_multi_task \
    --csv data2/image_label_mapping_phase1.csv \
    --epochs 30 --output-dir ./outputs_my_run
```

### Paired Full + Crop Training

Use `--paired-views` when the model should receive both the original full image
and the detected building crop. This requires `--cropped-root`; missing crops
fall back to the full image so training can continue.

Fusion modes:

- `concat_mlp`: original paired-v1 behavior; concatenates full and crop features
    through a randomly initialized projection.
- `crop_residual`: starts as exact crop passthrough and learns a global full-image
    residual.
- `task_gated_residual`: starts from crop-heavy task gates and lets each task learn
    its own full/crop balance.

For Phase 1 experiments that specifically protect `roof_type` and `stories`, use
task-gated residual fusion with stronger crop preservation:

```bash
python -m src.models.train_multi_task \
        --csv data2/image_label_mapping_phase1.csv \
        --model-config config/models/efficientnet_b5.json \
        --start-phase 1 --end-phase 1 \
        --epochs 30 \
        --lr 1.5e-4 \
        --scheduler cosine \
        --batch-size 6 \
        --grad-accum-steps 4 \
        --weight-decay 0.01 \
        --cropped-root crops/data2 \
        --paired-views \
        --paired-fusion task_gated_residual \
        --paired-gate-init crop_prior \
        --paired-gate-overrides roof_type=0.03,stories=0.01 \
        --paired-residual-scales roof_type=0.5,stories=0.25 \
        --paired-crop-bypass-tasks stories \
        --output-dir outputs/data2/b5_pair_v3_preserve_roof_stories \
        --run-name b5_pair_v3_preserve_roof_stories_phase1
```

This keeps `stories` crop-only at the fusion layer and lets `roof_type` retain a
small, trainable full-image residual. Use `--paired-crop-bypass-tasks
stories,roof_type` for a more aggressive crop-only protection test.

### What Gets Logged During Training

At the end of each epoch the terminal prints:

```
  Overall Accuracy : 77.21%

  Task                      Metric           Value     Macro F1
  ──────────────────────────────────────────────────────────────────────────────
  stories                   accuracy        75.06%      38.69%
  roof_type                 accuracy        55.99%      33.53%
  primary_cladding          accuracy        76.53%      14.84%
  chimney_present           accuracy        95.60%      48.88%
  setting                   jaccard         82.86%      22.42%   exact=72.13% ...
```

Simultaneously, every metric is sent to MLflow as a time-series data point.

---

## Experiment Tracking with MLflow

### Starting the UI

```bash
mlflow ui --port 5001 --host 127.0.0.1 --backend-store-uri sqlite:///mlflow.db
```

Then open **http://127.0.0.1:5001** (port 5000 is blocked by macOS AirPlay).

> **After a `pip install --upgrade mlflow`** run the schema migration before
> starting the UI:
> ```bash
> mlflow db upgrade sqlite:///mlflow.db
> ```

### What's Tracked Per Run

| Category | Logged as |
|---|---|
| All `RunConfig` fields (backbone, lr, epochs, …) | Parameters |
| `train_loss_total`, `val_loss_total` per epoch | Metric time-series |
| `val_overall_accuracy` per epoch | Metric time-series |
| Per-task accuracy/F1/Jaccard per epoch | Metric time-series (`val_<task>_acc`, …) |
| `best_overall_accuracy` at best val_loss epoch | Summary metric |
| `best_val_loss` | Summary metric |
| Path to best checkpoint | Parameter |

All accuracy/F1/Jaccard values are stored as **percentages (0–100)** so the
MLflow UI shows `77.21` rather than `0.7721`.

### Useful UI Workflows

**See all runs ranked by accuracy:**
1. Experiments → **arepas**
2. Click **Columns** → enable `peak_overall_accuracy`, `best_overall_accuracy`, `best_val_loss`
3. Click the `peak_overall_accuracy` column header to sort descending

**Compare epoch curves across runs:**
1. Check all runs → click **Compare**
2. Line Chart → select `val_overall_accuracy`

**Inspect a single run:**
- Click the run name → **Metrics** tab shows all time-series charts
- **Parameters** tab shows the full `RunConfig` snapshot

### Files Created Locally (gitignored)

| File/Dir | Contents |
|---|---|
| `mlflow.db` | SQLite experiment store |
| `mlruns/` | Artifact store (if file-based backend is used) |
| `runs/` | Training output dirs auto-created by the trainer |

---

## Evaluating a Checkpoint

Use `scripts/eval_checkpoint.py` to re-evaluate any saved `.pth` file against
the validation set without re-running training.

```bash
python scripts/eval_checkpoint.py \
    --csv data2/image_label_mapping_phase1.csv \
    --checkpoint outputs_data2_v3/phase1/best_model_phase1.pth \
    --phase 1 \
    --model-config config/models/resnet50.json \
    --batch-size 32
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--csv` | *(required)* | Same CSV used during training |
| `--checkpoint` | *(required)* | Path to `.pth` checkpoint file |
| `--phase` | `1` | Phase the checkpoint was trained on |
| `--model-config` | `config/models/resnet50.json` | Backbone preset |
| `--batch-size` | `32` | Evaluation batch size |

### Example Output

```
  Overall Accuracy : 77.21%

  Task                      Metric           Value     Macro F1
  ──────────────────────────────────────────────────────────────────────────────
  stories                   accuracy        75.06%      38.69%
  roof_type                 accuracy        55.99%      33.53%
  primary_cladding          accuracy        76.53%      14.84%
  chimney_present           accuracy        95.60%      48.88%
  setting                   jaccard         82.86%      22.42%   exact=72.13% ...
```

### Tip: Best Epoch vs Peak Accuracy Epoch

The checkpoint saved as `best_model_phase<N>.pth` is the one with the **lowest
validation loss** — not necessarily the highest accuracy epoch.
Accuracy often peaks a few epochs later as the model becomes more confident.
Use `eval_checkpoint.py` on individual `checkpoint_epoch<N>.pth` files to find
the accuracy-peak checkpoint manually.

---

## Comparing Runs

### Quick terminal comparison (no MLflow required)

```bash
python -c "
import json, glob
from src.models.metrics import format_metrics_table

for path in sorted(glob.glob('outputs*/phase1/training_history.json')):
    h = json.load(open(path))
    best = max(h, key=lambda e: e['val_metrics']['overall_accuracy'])
    print(f'── {path}  (epoch {best[\"epoch\"]}) ──')
    print(format_metrics_table(best['val_metrics']))
    print()
"
```

### Changing a single variable (controlled experiment)

To isolate the effect of one hyperparameter, keep everything else fixed and
use `--run-name` to label the run:

```bash
# Baseline
python -m src.models.train_multi_task --csv data2/... --lr 1e-4 --run-name "lr-1e4"

# Experiment: halve the learning rate
python -m src.models.train_multi_task --csv data2/... --lr 5e-5 --run-name "lr-5e5"
```

Then compare `val_overall_accuracy` curves side-by-side in the MLflow
**Compare** view.

---

## Scripts Reference

### `scripts/eval_checkpoint.py`

Standalone checkpoint evaluator. See [Evaluating a Checkpoint](#evaluating-a-checkpoint).

### `scripts/backfill_mlflow.py`

Imports pre-`ExperimentLogger` training runs into MLflow by reading
`training_history.json` files. Re-run any time after wiping `mlflow.db`.

```bash
python scripts/backfill_mlflow.py

# Target a specific history file
python scripts/backfill_mlflow.py \
    --history outputs_data2_v3/phase1/training_history.json

# Target a custom tracking URI
python scripts/backfill_mlflow.py --tracking-uri sqlite:///mlflow.db
```

### `scripts/analyze_roof_type.py`

Analyses `roof_type` label distribution across buildings — useful when
considering further coarsening of the roof taxonomy.

```bash
python scripts/analyze_roof_type.py
```

### `scripts/test_roof_type_encoding.py`

Smoke test that verifies the `normalize_roof_type_label()` function and the
`LabelEncoder` produce the expected 13 clean classes.

```bash
python scripts/test_roof_type_encoding.py
```

---

## Backfilling Legacy Runs

If `mlflow.db` is deleted (e.g. to start fresh), all historical runs can be
re-imported from the `training_history.json` files that live alongside every
checkpoint:

```bash
rm -f mlflow.db
python scripts/backfill_mlflow.py
mlflow db upgrade sqlite:///mlflow.db   # apply latest schema migrations
mlflow ui --port 5001 --host 127.0.0.1 --backend-store-uri sqlite:///mlflow.db
```

The backfill script skips directories whose path contains `smoke` (smoke-test
runs) by default. Pass `--skip-smoke-tests false` to include them.

### Known Runs

| Output dir | Dataset | roof_type | Stopped | Notes |
|---|---|---|---|---|
| `outputs/` | `data/` | multi-label (19 classes) | epoch 20 | Original baseline |
| `outputs_data2/` | `data2/` | multi-label (19 classes) | epoch 5 (patience=5) | data2 baseline |
| `outputs_data2_v2/` | `data2/` | single-label (13 classes) | epoch 5 (patience=5) | +Compound folding |
| `outputs_data2_v3/` | `data2/` | single-label (13 classes) | epoch 30 (no patience) | Best accuracy: 77.21% |

---

## Adding a New Training Task

The model constructs heads **data-driven**: it builds exactly one head per task
listed in `TRAINING_LABEL_COLS` in `src/loader/architectural_dataset.py`.

**Steps to add a task (e.g. `building_category`):**

1. **Register a loss config** — confirm an entry exists in `TaskConfig` in
   `src/models/multi_task_classifier.py` (e.g. in `MEDIUM_TASKS`).  Set a
   meaningful `loss_weight`; the classes list is informational only (the data
   drives actual class count at runtime).

2. **Activate in `TRAINING_LABEL_COLS`** — add the column name to the list:
   ```python
   TRAINING_LABEL_COLS: List[str] = [
       ...,
       "building_category",   # ← add here
   ]
   ```

3. **Verify the CSV** — run a quick check that the column exists and has
   acceptable coverage:
   ```bash
   python -c "
   import pandas as pd
   df = pd.read_csv('data2/image_label_mapping_phase1.csv')
   print(df['building_category'].value_counts(dropna=False))
   "
   ```

4. **Train** — no other code changes required.  The trainer auto-builds the
   new head and `MultiTaskLoss` automatically computes its loss each batch.

