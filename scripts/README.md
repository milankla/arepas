# Scripts Directory

Utility scripts for data analysis, model evaluation, and the offline building-crop pipeline.

## Available Scripts

### 📷 `crop_dataset.py`
**Purpose**: Offline building-crop pipeline — detects the main building in every image using GroundingDINO and saves a 456×456 square crop to `crops/data2/`.

**Usage**:
```bash
python scripts/crop_dataset.py \
  --csv data2/image_label_mapping_phase1.csv \
  --out crops/data2 --manifest crops/data2/crop_manifest.csv
```

**Key flags**:
- `--limit N` — process only first N images (for spot-checks)
- `--device auto|cpu|mps|cuda` — inference device
- `--conf-threshold 0.25` — minimum detection confidence before geometric fallback
- `--target-size 456` — output size in pixels (square)
- `--dry-run` — print what would be processed without writing files

Resumes automatically: images with an existing crop are skipped.

### 👁️ `preview_crops.py`
**Purpose**: Side-by-side HTML preview of original vs crop, served on localhost.

**Usage**:
```bash
python scripts/preview_crops.py \
  --manifest crops/data2/crop_manifest.csv \
  --out-root crops/data2 --port 8000
```

### 📊 `field_coverage_report.py`
**Purpose**: Generate comprehensive field coverage analysis across all datasets

**Usage**:
```bash
python scripts/field_coverage_report.py
```

**Features**:
- Field presence analysis across datasets
- Required vs optional field coverage
- Missing field identification
- CSV export of coverage matrix

## Quick Reference

| Script | Purpose |
|--------|--------|
| `crop_dataset.py` | Offline building-crop pipeline (GroundingDINO) |
| `preview_crops.py` | Side-by-side crop preview server |
| `field_coverage_report.py` | Field coverage analysis across datasets |
| `eval_checkpoint.py` | Re-evaluate a saved checkpoint |
| `plot_training_history.py` | Plot loss / accuracy curves from a training log |
| `analyze_image_data.py` | Image statistics analysis |
| `analyze_roof_type.py` | Roof-type label analysis |
| `analyze_stories_gap.py` | Stories val/test gap analysis |
| `attribute_dependency_analysis.py` | Cramér's V between attribute pairs |
| `backfill_mlflow.py` | Back-fill MLflow runs from log files |
| `build_phase1_label_mapping.py` | Build image_label_mapping_phase1.csv |
| `generate_gallery.py` | Generate HTML crop gallery |
| `generate_three_column_gallery.py` | Three-column HTML gallery |
| `test_roof_type_encoding.py` | Sanity-check roof-type encoding |

## Notes

- All scripts are run from the project root.
- `crops/` output is excluded from git (see `.gitignore`).

---

## Model Training & Evaluation Scripts

See [docs/TRAINING_AND_EVALUATION.md](../docs/TRAINING_AND_EVALUATION.md) for the
full reference. Quick start:

```bash
python -m src.models.train_multi_task \
    --csv data2/image_label_mapping_phase1.csv \
    --epochs 30 --batch-size 32 --lr 1e-4 --num-workers 2
```

### `eval_checkpoint.py`
**Purpose**: Re-evaluate any saved checkpoint against the validation set without re-running training.

```bash
python scripts/eval_checkpoint.py \
    --csv data2/image_label_mapping_phase1.csv \
    --checkpoint outputs_data2_v3/phase1/best_model_phase1.pth \
    --phase 1
```

**Options**: `--csv`, `--checkpoint`, `--phase`, `--model-config`, `--batch-size`

### `backfill_mlflow.py`
**Purpose**: Import pre-`ExperimentLogger` training runs into MLflow from
`training_history.json` files. Re-run after wiping `mlflow.db`.

```bash
python scripts/backfill_mlflow.py
# or target one specific run:
python scripts/backfill_mlflow.py \
    --history outputs_data2_v3/phase1/training_history.json
```

### `analyze_roof_type.py`
**Purpose**: Analyse `roof_type` label distribution across buildings to inform
taxonomy coarsening decisions.

```bash
python scripts/analyze_roof_type.py
```

### `test_roof_type_encoding.py`
**Purpose**: Smoke test that verifies `normalize_roof_type_label()` produces
the expected 13 single-label classes.

```bash
python scripts/test_roof_type_encoding.py
```
