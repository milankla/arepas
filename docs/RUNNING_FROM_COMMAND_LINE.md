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

## Demo Scripts

### 1. Demo ConfigurableDataLoader

```bash
python scripts/demo_configurable_loader.py
```

**Features**:
- Configuration loading
- Individual dataset loading
- Neighborhood-based loading
- Summary statistics
- Schema integration demonstration

### 2. Demo Schema Loader

```bash
python scripts/demo_schema_loader.py
```

**Features**:
- Schema parsing and display
- Field type exploration
- Valid options listing
- Required field identification
- Multipart field structures

### 3. Demo Dataset Validation

```bash
python -m scripts.demo_dataset_validation
```

**Features**:
- Schema-based validation
- Threshold validation (≤10 missing = warnings)
- Top missing field identification
- Per-dataset validation reports

**Example Output**:
```
🔍 Validating datasets against schema...

✅ Validation complete: 27/27 valid records
✅ Validation complete: 8/8 valid records
✅ Validation complete: 7/8 valid records (missing: Building Plan, Roof Features, ...)

📊 OVERALL VALIDATION SUMMARY:
   Total records: 198
   Valid: 194 (98.0%)
   Invalid: 4 (2.0%)
```

### 4. Field Coverage Report

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
# Run full schema validation
python -m scripts.demo_dataset_validation

# Check validation rates and missing fields
```

### 3. Test New Configuration
```bash
# Create new config file
nano config/custom.json

# Test it
python -m src.loader.configurable_loader config/custom.json
```

### 4. Performance Benchmarking
```bash
# Test image matching performance
python scripts/test_performance.py

# Should show ~1.0ms per building
```

### 5. Compare Configurations
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
| `python scripts/demo_configurable_loader.py` | Hardcoded | Run demo script |
| `python -m scripts.demo_dataset_validation` | Both configs | Validate all datasets |

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

## See Also

- [SCHEMA_INTEGRATION.md](SCHEMA_INTEGRATION.md) - Schema system details
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Architecture overview
- [../scripts/README.md](../scripts/README.md) - Script documentation
