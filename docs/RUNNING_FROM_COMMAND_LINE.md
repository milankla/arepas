# Running ConfigurableDataLoader from Command Line

## Three Ways to Run

### 1. As a Python Module (Recommended)
```bash
# Use default config (config/data.json)
python -m src.loader.configurable_loader

# Use custom config
python -m src.loader.configurable_loader config/custom.json
```

### 2. Direct Python Execution
```bash
# Use default config
python src/loader/configurable_loader.py

# Use custom config
python src/loader/configurable_loader.py config/data.json
```

### 3. From Python REPL or Script
```python
from src.loader.configurable_loader import ConfigurableDataLoader

# Load and print summary
loader = ConfigurableDataLoader("config/data.json")
data = loader.load_all_datasets()
loader.print_summary(data)
```

## What It Does

When run from command line, the loader will:

1. **Load Configuration** - Reads the JSON config file
2. **Display Config Info** - Shows structure type, datasets, neighborhoods
3. **Load All Datasets** - Loads all data from configured paths
4. **Print Summary** - Beautiful formatted summary with statistics

## Example Output

```
07:42:40 | INFO     | Starting ConfigurableDataLoader with config: config/data.json
07:42:40 | INFO     | Loading configuration from: config/data.json
07:42:40 | INFO     | Configuration valid: 19 datasets

📋 Configuration Info:
  Description: Configuration for data/ folder - Architectural style-based organization
  Structure type: style-based
  Total datasets: 19

🔄 Loading all datasets...
[Loading progress...]

============================================================
DATA LOADING SUMMARY
============================================================

📊 Clayton-Bungalows:
  Buildings: 8
  Buildings with images: 8 (100%)
  Total images: 25

... (more datasets)

============================================================
✅ TOTAL: 19 datasets
   Buildings: 198
   With images: [count] ([percentage]%)
   Total images: [count]
   Avg images/building: [avg]
============================================================

✅ Data loading completed successfully!
```

## Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| None | Use default config | `config/data.json` |
| `<path>` | Path to custom config file | - |

## Examples

### Load default structure
```bash
python -m src.loader.configurable_loader
```

### Load custom configuration
```bash
python -m src.loader.configurable_loader config/custom.json
```

### Load alternative configuration
```bash
python -m src.loader.configurable_loader /path/to/my/config.json
```

## Use Cases

### 1. Quick Data Validation
Run the loader to verify:
- All CSV files exist
- All image directories exist
- Data loads without errors
- Coverage statistics

### 2. Data Summary Report
Get a quick overview of:
- Total buildings
- Image coverage
- Per-neighborhood statistics

### 3. Testing New Configurations
Before using a config in your code:
```bash
python -m src.loader.configurable_loader config/new_config.json
```

### 4. Comparison Between Configurations
```bash
# Load default config
python -m src.loader.configurable_loader config/data.json > report_default.txt

# Load alternative config
python -m src.loader.configurable_loader config/custom.json > report_custom.txt

# Compare
diff report_default.txt report_custom.txt
```

## Integration with Scripts

The `__main__` block makes it easy to test the loader standalone:

```bash
# Quick test during development
python -m src.loader.configurable_loader

# Part of a data pipeline
python -m src.loader.configurable_loader && python my_analysis.py

# Conditional execution
python -m src.loader.configurable_loader || echo "Data loading failed!"
```

## Error Handling

The loader will:
- ✅ Print clear error messages
- ✅ Exit with code 1 on failure
- ✅ Show full traceback for debugging
- ✅ Validate all paths before loading

Example error:
```bash
$ python -m src.loader.configurable_loader config/missing.json
07:42:40 | ERROR    | ❌ Failed to load data: Configuration file not found: config/missing.json
[Traceback...]
```

## Comparison with Other Loaders

| Loader | Command | Config | Output |
|--------|---------|--------|--------|
| `data_loader.py` | `python -m src.loader.data_loader` | Hardcoded | Basic summary |
| `configurable_loader.py` | `python -m src.loader.configurable_loader [config]` | JSON file | Enhanced summary |
| `neighborhood_loader.py` | N/A (library only) | - | - |

## Tips

1. **Always test with default first**: `python -m src.loader.configurable_loader`
2. **Check exit code**: `echo $?` (should be 0 on success)
3. **Redirect output**: `python -m src.loader.configurable_loader > report.txt 2>&1`
4. **Time execution**: `time python -m src.loader.configurable_loader`

## See Also

- `scripts/demo_configurable_loader.py` - Comprehensive demo script
- `docs/SUMMARY_REPORTING.md` - Documentation on summary features
- `config/data.json` - Default configuration file
