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
