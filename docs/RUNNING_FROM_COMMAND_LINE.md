# Running from Command Line

## Overview

The Arepas data system can be run from the command line for quick data validation, testing, and exploration. All loaders automatically integrate the Discover Denver Schema for validation.

## ConfigurableDataLoader

### Running the Loader

```bash
# Use default config (config/data.json)
python -m src.loader.configurable_loader

# Use custom config
python -m src.loader.configurable_loader config/data2.json

# Alternative: Direct execution
python src/loader/configurable_loader.py config/data.json
```

### What It Does

1. **Load Configuration** - Reads JSON config file
2. **Load Schema** - Automatically loads Discover Denver Schema
3. **Validate Columns** - Checks CSV columns against schema
4. **Load All Datasets** - Loads data with image matching
5. **Print Summary** - Displays statistics and coverage

### Example Output

```
07:42:40 | INFO     | Starting ConfigurableDataLoader with config: config/data.json
07:42:40 | INFO     | Loading schema from: schema/Discover Denver Schema.txt
07:42:40 | INFO     | Schema loaded: 55 fields defined
07:42:40 | INFO     | Configuration valid: 19 datasets

============================================================
DATA LOADING SUMMARY
============================================================

📊 Clayton-Bungalows:
  Buildings: 8
  Buildings with images: 8 (100%)
  Total images: 25

============================================================
✅ TOTAL: 19 datasets
   Buildings: 198
   Images: [count]
============================================================
```

## Scripts

### Field Coverage Report

```bash
python scripts/field_coverage_report.py
```

**Features**:
- Field presence analysis
- Required vs optional coverage
- Missing field matrix
- CSV export capability

## Configuration Files

### For data/ folder (style-based)
```bash
python -m src.loader.configurable_loader config/data.json
```

Config structure:
```json
{
  "version": "1.0",
  "description": "Style-based organization",
  "base_path": ".",
  "datasets": [
    {
      "name": "Clayton-Bungalows",
      "csv_file": "data/Bungalows/Clayton Data - CLEAN.txt",
      "images_dir": "data/Bungalows/Bungalows - Photos"
    }
  ]
}
```

### For data2/ folder (neighborhood-based)
```bash
python -m src.loader.configurable_loader config/data2.json
```

Config structure:
```json
{
  "version": "1.0",
  "description": "Neighborhood-based organization",
  "base_path": ".",
  "datasets": [
    {
      "name": "Cole",
      "csv_file": "data2/Cole/Cole - CLEAN.txt",
      "images_dir": "data2/Cole"
    }
  ]
}
```

## Use Cases

### 1. Quick Data Validation
```bash
# Validate all data loads correctly
python -m src.loader.configurable_loader config/data.json

# Check for errors or warnings in output
```

### 2. Schema Validation
```bash
# Check field coverage across datasets
python scripts/field_coverage_report.py
```

### 3. Test New Configuration
```bash
# Create new config file
nano config/custom.json

# Test it
python -m src.loader.configurable_loader config/custom.json
```

### 4. Compare Configurations
```bash
# Generate reports for different configs
python -m src.loader.configurable_loader config/data.json > report_data.txt
python -m src.loader.configurable_loader config/data2.json > report_data2.txt

# Compare
diff report_data.txt report_data2.txt
```

## Python REPL Usage

```python
from src.loader import ConfigurableDataLoader, DatasetValidator

# Load data with schema
loader = ConfigurableDataLoader("config/data.json")
data = loader.load_all_datasets()

# Print summary
loader.print_summary(data)

# Validate
validator = DatasetValidator(loader.schema)
# ... validation code
```

## Command Line Arguments

| Command | Config | Description |
|---------|--------|-------------|
| `python -m src.loader.configurable_loader` | Default (`config/data.json`) | Load with default config |
| `python -m src.loader.configurable_loader <path>` | Custom path | Load with custom config |

## Error Handling

The system provides clear error messages:

```bash
# Missing config
$ python -m src.loader.configurable_loader config/missing.json
ERROR - Configuration file not found: config/missing.json

# Missing CSV
$ python -m src.loader.configurable_loader config/bad.json
ERROR - CSV file not found: data/Missing/file.txt

# Schema validation warnings
WARNING - Dataset Cole: Missing 3 required fields: Building Plan, Roof Features, ...
```

## Tips

1. **Test configuration first**: Always run loader to verify paths
2. **Check exit codes**: `echo $?` should be 0 on success
3. **Redirect output**: `... > report.txt 2>&1` for log files
4. **Time execution**: `time python -m ...` for performance
5. **Use module syntax**: `python -m` handles imports correctly

## Model Training

### Prerequisites

Build the label-mapping CSV for the dataset you want to train on.
This only needs to be run once (or whenever the underlying `.txt` files change):

```bash
# data/ dataset
python scripts/build_phase1_label_mapping.py --config config/data.json

# data2/ dataset
python scripts/build_phase1_label_mapping.py --config config/data2.json
```

Both commands produce `<dataset>/image_label_mapping_phase1.csv`.

---

### Quick Start

```bash
# Phase 1, ResNet-50, data2/ dataset
python -m src.models.train_multi_task \
  --csv data2/image_label_mapping_phase1.csv \
  --model-config config/models/resnet50.json \
  --epochs 20 \
  --batch-size 32 \
  --output-dir outputs/resnet50_data2
```

```bash
# Phase 1, data/ dataset
python -m src.models.train_multi_task \
  --csv data/image_label_mapping_phase1.csv \
  --model-config config/models/resnet50.json \
  --epochs 20 \
  --output-dir outputs/resnet50_data
```

---

### CLI Reference

| Flag | Default | Description |
|---|---|---|
| `--csv` | *(required)* | Path to `image_label_mapping_phase1.csv` |
| `--model-config` | `config/models/resnet50.json` | Backbone preset (see `config/models/`) |
| `--start-phase` | `1` | First phase to train (1–4) |
| `--end-phase` | `1` | Last phase to train inclusive (1–4) |
| `--epochs` | `20` | Training epochs per phase |
| `--batch-size` | `32` | Samples per GPU batch |
| `--lr` | `1e-4` | AdamW initial learning rate |
| `--output-dir` | `./outputs` | Root dir for checkpoints and history |
| `--num-workers` | `4` | DataLoader worker processes |
| `--max-batches` | `None` | Limit batches per epoch (smoke test use) |

---

### Switching Backbone

The pipeline is model-agnostic — any `config/models/*.json` preset works:

```bash
# EfficientNet-B0
python -m src.models.train_multi_task \
  --csv data2/image_label_mapping_phase1.csv \
  --model-config config/models/efficientnet_b0.json

# Lightweight ResNet-18
python -m src.models.train_multi_task \
  --csv data2/image_label_mapping_phase1.csv \
  --model-config config/models/resnet18.json

# CLIP ViT-B/32
python -m src.models.train_multi_task \
  --csv data2/image_label_mapping_phase1.csv \
  --model-config config/models/clip_vit_b32.json
```

Image resolution and normalisation statistics are read automatically from the
chosen preset — no other changes needed.

---

### Progressive Multi-Phase Training

```bash
# Train phases 1 and 2 back-to-back (phase 2 warm-starts from phase 1 best)
python -m src.models.train_multi_task \
  --csv data2/image_label_mapping_phase1.csv \
  --model-config config/models/resnet50.json \
  --start-phase 1 \
  --end-phase 2 \
  --epochs 20 \
  --output-dir outputs/progressive
```

Phase checkpoints are saved under `<output-dir>/phase<N>/`:

```
outputs/progressive/
  phase1/
    best_model_phase1.pth
    training_history.json
  phase2/
    best_model_phase2.pth
    training_history.json
```

---

### Smoke Test (CPU, 3 batches)

Verifies the full pipeline — data loading → model forward → loss → backward —
without running a full epoch:

```bash
python -m src.models.train_multi_task \
  --csv data2/image_label_mapping_phase1.csv \
  --model-config config/models/resnet18.json \
  --epochs 1 \
  --batch-size 8 \
  --num-workers 0 \
  --max-batches 3 \
  --output-dir outputs/smoke_test
```

Expected output (abridged):
```
Device: cpu | Backbone: resnet18 | CSV: data2/image_label_mapping_phase1.csv
Encoders fitted — class counts: architectural_style: 21, building_form: 32, roof_type: 19(multi), primary_cladding: 18, stories: 8, alteration_level: 5
Dataset splits — train: 1911, val: 409, test: 388
Class counts per task: architectural_style: 21, ...

============================================================
PHASE 1: EASY VISUAL FEATURES (stories, roof type, cladding)
============================================================
Active tasks: ['stories', 'roof_type', 'primary_cladding', 'chimney_present', 'setting']
Epoch 1 [Train]:   1%|▏  | 3/238 ...  loss=0.657
Epoch 1 [Val]:   6%|▉   | 3/52  ...  loss=0.568
  Train Loss: 0.6571
  Val Loss:   0.5684
  Task Accuracies:
    primary_cladding: 0.583
    roof_type: 0.000
    stories: 0.500
✓ New best model saved (val_loss: 0.5684)
Phase 1 complete. Best checkpoint → outputs/smoke_test/phase1/best_model_phase1.pth
```

---

## See Also

- [SCHEMA_INTEGRATION.md](SCHEMA_INTEGRATION.md) - Schema system details
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Architecture overview
- [MULTI_TASK_STRATEGY.md](MULTI_TASK_STRATEGY.md) - Multi-task learning strategy
- [../scripts/README.md](../scripts/README.md) - Script documentation
