# Scripts Directory

Utility scripts for testing, demonstrating, and validating the Arepas data loading and schema validation system.

## Available Scripts

### 🎯 `demo_configurable_loader.py`
**Purpose**: Demonstrate the ConfigurableDataLoader with schema integration

**Usage**:
```bash
python scripts/demo_configurable_loader.py
```

**Features**:
- Load data from JSON configuration
- Automatic schema loading and validation
- Dataset loading (individual and by neighborhood)
- Summary reporting with statistics
- Multi-CSV neighborhood merging support

### 🔍 `demo_schema_loader.py`
**Purpose**: Demonstrate the Discover Denver Schema loading and querying

**Usage**:
```bash
python scripts/demo_schema_loader.py
```

**Features**:
- Load and parse schema from text file
- Display field types, requirements, and valid options
- Query fields by name
- Filter by survey level
- Show multipart field structures

### ✅ `demo_dataset_validation.py`
**Purpose**: Validate datasets against the Discover Denver Schema

**Usage**:
```bash
python -m scripts.demo_dataset_validation
```

**Features**:
- Schema-based validation with intelligent thresholds
- Records with ≤10 missing required fields = valid with warnings
- Records with >10 missing required fields = invalid
- Detailed validation reports showing top missing fields
- Per-dataset validation statistics

### � `field_coverage_report.py`
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

### 🔬 `test_performance.py`
**Purpose**: Performance benchmarking and regression testing

**Usage**:
```bash
python scripts/test_performance.py
```

**Features**:
- Image matching performance metrics
- Processing time per building (~1.0ms)
- Validation of 10-15x performance optimizations

### 📋 `verify_github_ready.py`
**Purpose**: Verify project readiness for publication

**Usage**:
```bash
python scripts/verify_github_ready.py
```

**Checks**:
- Essential files (README, LICENSE, requirements.txt)
- Documentation completeness
- Source code structure
- Module imports
- Sensitive file exclusions

## Quick Reference

| Script | Purpose | Run Time |
|--------|---------|----------|
| `demo_configurable_loader.py` | Feature demonstration | ~10s |
| `demo_schema_loader.py` | Schema exploration | <1s |
| `demo_dataset_validation.py` | Schema validation | ~5s |
| `field_coverage_report.py` | Coverage analysis | ~10s |
| `test_performance.py` | Performance benchmarking | ~5s |
| `verify_github_ready.py` | Project validation | <1s |

## Notes

- Scripts automatically adjust paths when run from any directory
- Use `python -m scripts.<script_name>` for module execution
- All scripts use the schema from `schema/Discover Denver Schema.txt`
- These scripts serve different purposes than production code and are kept separate
- Run performance and validation tests after significant changes
- Demo script is useful for understanding the ConfigurableDataLoader API

## Running from Different Locations

All scripts can be run from the project root or from within the `scripts/` directory:

```bash
# From project root
python scripts/demo_configurable_loader.py
python scripts/test_performance.py
python scripts/verify_github_ready.py

# From scripts directory
cd scripts
python demo_configurable_loader.py
python test_performance.py
python verify_github_ready.py
```

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
