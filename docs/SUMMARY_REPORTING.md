# ConfigurableDataLoader Summary Reporting

## Overview

The `ConfigurableDataLoader` now includes comprehensive summary reporting capabilities, similar to those in `data_loader.py`, providing detailed statistics about loaded datasets.

## New Methods

### 1. `get_summary(data: Dict[str, NeighborhoodData]) -> Dict[str, Any]`

Returns a dictionary with detailed summary statistics.

**Example:**
```python
loader = ConfigurableDataLoader("config/data2.json")
data = loader.load_all_datasets()
summary = loader.get_summary(data)

print(summary)
# {
#     'total_datasets': 8,
#     'total_buildings': 8208,
#     'total_buildings_with_images': 8074,
#     'total_images': 28543,
#     'coverage_percentage': 98.4,
#     'average_images_per_building': 3.5,
#     'datasets': {
#         'Cole': {
#             'buildings': 1335,
#             'buildings_with_images': 1286,
#             'total_images': 4466,
#             'coverage': 96.3
#         },
#         # ... more datasets
#     }
# }
```

### 2. `print_summary(data: Dict[str, NeighborhoodData]) -> None`

Prints a beautifully formatted summary to the console with emoji indicators and color coding.

**Example:**
```python
loader = ConfigurableDataLoader("config/data2.json")
data = loader.load_all_datasets()
loader.print_summary(data)
```

**Output:**
```
============================================================
DATA LOADING SUMMARY
============================================================

📊 Cole:
  Buildings: 1335
  Buildings with images: 1286 (96.3%)
  Total images: 4466

📊 Regis:
  Buildings: 1535
  Buildings with images: 1524 (99.3%)
  Total images: 6125

... (more datasets)

============================================================
✅ TOTAL: 8 datasets
   Buildings: 8208
   With images: 8074 (98.4%)
   Total images: 28543
   Avg images/building: 3.5
============================================================
```

## Usage Examples

### Basic Usage - Load and Print Summary

```python
from src.loader.configurable_loader import ConfigurableDataLoader

# Initialize loader
loader = ConfigurableDataLoader("config/data2.json")

# Load all datasets
data = loader.load_all_datasets()

# Print formatted summary
loader.print_summary(data)
```

### Programmatic Access to Statistics

```python
# Get summary as dict for programmatic use
summary = loader.get_summary(data)

# Access specific stats
total_buildings = summary['total_buildings']
coverage = summary['coverage_percentage']
avg_images = summary['average_images_per_building']

# Per-dataset stats
for dataset_name, stats in summary['datasets'].items():
    print(f"{dataset_name}: {stats['coverage']:.1f}% coverage")
```

### Loading Single Neighborhood with Summary

```python
# Load a specific neighborhood
loader = ConfigurableDataLoader("config/data2.json")
cole_data = loader.load_neighborhood("Cole", merge=False)

# Create summary for single dataset
single_summary = loader.get_summary({"Cole": cole_data})
print(f"Cole has {single_summary['total_images']} images")
```

### Comparing Multiple Configurations

```python
# Load data2 structure
loader_data2 = ConfigurableDataLoader("config/data2.json")
data2 = loader_data2.load_all_datasets()
summary_data2 = loader_data2.get_summary(data2)

# Load data structure (when available)
loader_data = ConfigurableDataLoader("config/data.json")
data = loader_data.load_all_datasets()
summary_data = loader_data.get_summary(data)

# Compare
print(f"data2/: {summary_data2['total_buildings']} buildings")
print(f"data/:  {summary_data['total_buildings']} buildings")
```

## Summary Statistics

### Overall Metrics

| Metric | Description | Calculation |
|--------|-------------|-------------|
| `total_datasets` | Number of datasets loaded | `len(data)` |
| `total_buildings` | Total buildings across all datasets | Sum of all `total_buildings` |
| `total_buildings_with_images` | Buildings that have at least one image | Sum of all `buildings_with_images` |
| `total_images` | Total number of images | Sum of all `total_images` |
| `coverage_percentage` | Percentage of buildings with images | `(buildings_with_images / total_buildings) * 100` |
| `average_images_per_building` | Average images per building | `total_images / total_buildings` |

### Per-Dataset Metrics

Each dataset in the `datasets` dictionary includes:

| Field | Description |
|-------|-------------|
| `buildings` | Number of buildings in this dataset |
| `buildings_with_images` | Buildings with at least one image |
| `total_images` | Total images for this dataset |
| `coverage` | Percentage coverage for this dataset |

## Integration with Existing Code

The summary reporting methods are compatible with all loading methods:

```python
# Works with load_all_datasets()
all_data = loader.load_all_datasets()
loader.print_summary(all_data)

# Works with load_neighborhood() (single)
cole = loader.load_neighborhood("Cole")
loader.print_summary({"Cole": cole})

# Works with multiple load_neighborhood() calls
data = {
    "Cole": loader.load_neighborhood("Cole"),
    "Regis": loader.load_neighborhood("Regis"),
}
loader.print_summary(data)

# Works with load_dataset() (individual)
pearl = loader.load_dataset("StreetcarCommercial-Pearl")
loader.print_summary({"Pearl": pearl})
```

## Real-World Example: data2/ Summary

Running on the actual `data2/` dataset:

```
✅ TOTAL: 8 datasets
   Buildings: 8208
   With images: 8074 (98.4%)
   Total images: 28543
   Avg images/building: 3.5
```

**Breakdown by neighborhood:**
- Cole: 1335 buildings, 96.3% coverage, 4466 images
- Regis: 1535 buildings, 99.3% coverage, 6125 images
- Skyland: 1225 buildings, 99.1% coverage, 4197 images
- South City Park: 495 buildings, 99.0% coverage, 1647 images
- Streetcar Commercial (3 areas): 300 buildings, 97.3% coverage, 910 images
- Sunnyside: 3318 buildings, 98.5% coverage, 11198 images

## Comparison with NeighborhoodDataLoader

Both loaders now provide similar summary capabilities:

| Feature | NeighborhoodDataLoader | ConfigurableDataLoader |
|---------|----------------------|----------------------|
| Summary statistics | ✅ (inline in main) | ✅ (dedicated methods) |
| Formatted output | ✅ Basic | ✅ Enhanced with emoji |
| Programmatic access | ❌ Manual calculation | ✅ `get_summary()` |
| Per-dataset breakdown | ✅ | ✅ |
| Coverage percentages | ❌ | ✅ |
| Average calculations | ❌ | ✅ |

## Benefits

1. **Consistency**: Same reporting interface across loaders
2. **Flexibility**: Both formatted output and programmatic access
3. **Completeness**: Coverage percentages and averages calculated
4. **Usability**: Easy-to-read formatted output with visual indicators
5. **Integration**: Works seamlessly with all loading methods

## Demo Script

See `scripts/demo_configurable_loader.py` for a complete working example that demonstrates:
- Loading all datasets with summary
- Loading single neighborhoods
- Comparing different data structures
- Accessing summary statistics programmatically

Run it with:
```bash
python scripts/demo_configurable_loader.py
```
