# Scripts Directory

This directory contains utility scripts for testing and demonstrating the Arepas data loading system.

## Available Scripts

### 🎯 `demo_configurable_loader.py`
**Purpose**: Comprehensive demonstration of the ConfigurableDataLoader functionality

**Usage**:
```bash
python scripts/demo_configurable_loader.py
```

**What it demonstrates**:
- Loading configuration from JSON files
- Loading individual datasets
- Loading and merging datasets by neighborhood
- Summary reporting with statistics
- Multi-CSV neighborhood support (Streetcar Commercial)

**Sample Output**:
```
🎯 ConfigurableDataLoader Demo
============================================================

📋 1. Loading Configuration
✅ Configuration loaded: config/data2.json
   Description: Neighborhood-based organization
   Datasets: 8
   Neighborhoods: Cole, Regis, Skyland, SouthCityPark, StreetcarCommercial, Sunnyside

🔄 2. Loading Individual Dataset
✅ Loaded Cole dataset
   Buildings: 1335, With images: 1286 (96.3%), Images: 4466
...
```

### 🔬 `test_performance.py`
**Purpose**: Performance benchmarking and regression testing

**Usage**:
```bash
python scripts/test_performance.py
```

**What it does**:
- Tests image matching performance on real neighborhood datasets
- Measures processing time per building (currently ~1.0ms)
- Validates 10-15x performance optimizations are maintained
- Provides metrics for regression testing

**Sample Output**:
```
Testing performance with neighborhood: Regis
Performance Results:
  Time elapsed: 1.63 seconds
  Buildings processed: 1535
  Buildings with images: 1524
  Total images found: 6125
  Average time per building: 1.0 ms
```

### 📋 `verify_github_ready.py`
**Purpose**: Verify project readiness for GitHub publication

**Usage**:
```bash
python scripts/verify_github_ready.py
```

**What it checks**:
- Essential files (README, LICENSE, requirements.txt, etc.)
- Documentation completeness
- Source code structure integrity
- Module import functionality
- Sensitive files that should be gitignored
- Overall project health

**Sample Output**:
```
🔍 Verifying Arepas GitHub Readiness
📋 Essential Files
✅ Main documentation: README.md
✅ License file: LICENSE
✅ Python dependencies: requirements.txt
🚀 Project is ready for GitHub!
```

## Quick Reference

| Script | Purpose | Run Time |
|--------|---------|----------|
| `demo_configurable_loader.py` | Feature demonstration | ~10s |
| `test_performance.py` | Performance benchmarking | ~5s |
| `verify_github_ready.py` | Project validation | <1s |

## Development Notes

- All scripts automatically adjust paths when run from the `scripts/` directory
- They use relative imports to access the main `src/loader` package
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
