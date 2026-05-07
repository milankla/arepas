# Arepas Project Architecture

## 🏗️ Overview

Arepas is a flexible, schema-aware data loading system for processing historical architectural building data with associated images. The system integrates the **Discover Denver Schema** for automatic validation and rich metadata.

## 📦 Project Structure

```
📦 arepas/
├── 🎯 src/                           # Core application source
│   ├── loader/                       # Data loading and validation system
│   │   ├── __init__.py              # Public API exports
│   │   ├── configurable_loader.py   # JSON-driven loader with schema integration
│   │   ├── csv_parser.py            # Robust CSV parsing
│   │   ├── image_index.py           # Image indexing and matching
│   │   ├── load_config.py           # Configuration infrastructure
│   │   ├── schema_loader.py         # Discover Denver Schema loader
│   │   └── dataset_validator.py     # Schema-based validation with thresholds
│   ├── fine_tune.py                 # Pipeline entry point
│   └── preprocess.py                # Image preprocessing
├── 🔧 scripts/                      # Utility scripts
│   ├── crop_dataset.py              # Offline building-crop pipeline (GroundingDINO)
│   ├── preview_crops.py             # Side-by-side crop preview server
│   ├── field_coverage_report.py     # Coverage analysis
│   ├── eval_checkpoint.py           # Re-evaluate a saved checkpoint
│   ├── plot_training_history.py     # Plot training curves
│   └── analyze_*.py / generate_*.py # Data analysis and gallery scripts
├── 📁 data/                         # Style-based organization
│   ├── Bungalows/                   # Bungalow architectural style
│   │   ├── Clayton Data - CLEAN.txt
│   │   ├── Cole Data - CLEAN.txt
│   │   └── Bungalows - Photos/
│   └── Minimal Traditional/         # Minimal Traditional style
│       └── Minimal Traditional - Photos/
├── 📁 data2/                        # Neighborhood-based organization
│   ├── Cole/                        # Neighborhood folder
│   │   ├── Cole - CLEAN.txt
│   │   └── [images]
│   ├── Regis/
│   └── [other neighborhoods]
├── � schema/                       # Schema definitions
│   └── Discover Denver Schema.txt   # 55-field schema definition
├── 📁 config/                       # Configuration files
│   ├── data.json                    # Config for data/ folder
│   └── data2.json                   # Config for data2/ folder
├── 📁 docs/                         # Technical documentation
└── requirements.txt                 # Python dependencies
```

## 🏛️ Core Components

### 1. Data Loading System (`src/loader/`)

| Module | Purpose | Key Features |
|--------|---------|--------------|
| `configurable_loader.py` | Schema-aware data loading | Automatic schema integration, JSON configuration, flexible structure mapping |
| `schema_loader.py` | Schema parsing | Loads 55-field Discover Denver Schema with types, requirements, valid options |
| `dataset_validator.py` | Schema validation | Intelligent threshold-based validation (≤10 missing = valid with warnings) |
| `csv_parser.py` | CSV processing | Error tolerance, field validation, fallback parsing |
| `image_index.py` | Image matching | Hash-based lookups, pattern matching, multi-extension support |
| `load_config.py` | Configuration | JSON loading, validation, dataset queries |

### 2. Schema System

**Discover Denver Schema** (55 fields):
- **24 required fields**: Original Use, Building Form, Roof Type, etc.
- **31 optional fields**: Year Built, Architect, Style, etc.
- **Field types**: single, multi, text, longtext, multipart
- **Multipart fields**: Window (Type, Location, Features), Entrance (Type, Location)
- **Valid options**: Pre-defined choices per field (e.g., 33 Original Use options)

**Validation Thresholds**:
- Records with **≤10 missing required fields**: Valid with warnings
- Records with **>10 missing required fields**: Invalid with errors
- Invalid options always marked as errors

### 3. Data Structure

**Rich Metadata Per Field**:
```python
{
    'field_name': {
        'value': 'Domestic – Single Dwelling',
        'type': 'single',
        'required': True,
        'options': ['Domestic – Single Dwelling', 'Commercial', ...]
    }
}
```

**Additional Metadata** (29 fields):
- `address`, `smithsonianNumber`, `yearBuilt`, `surveyLevel`
- Coordinates: `latitude`, `longitude`
- Timestamps: `surveyedAt`, `createdAt`, `updatedAt`
- Administrative: `city`, `township`, `range`, `section`

## 🚀 Key Features

### Schema Integration
- **Automatic loading**: Schema loaded on ConfigurableDataLoader initialization
- **Column validation**: Warns about missing/unknown columns during loading
- **Field metadata**: Each attribute includes type, requirement status, valid options
- **Type safety**: Dataclass-based schema with comprehensive type hints

### Intelligent Validation
- **Threshold system**: Configurable error threshold (default: 10)
- **Warning vs Error**: Missing fields below threshold = warnings, above = errors
- **Detailed reporting**: Shows top 3 most common missing fields
- **Multipart support**: Special handling for complex fields (Window, Entrance)

### Performance
- **Hash-based indexing**: O(1) image lookups
- **Optimized matching**: ~1.0ms per building
- **Memory efficient**: Pre-built indexes, lazy loading where possible

### Flexibility
- **Any structure**: JSON config supports both `data/` and `data2/` layouts
- **Multiple formats**: Tab-delimited, comma-delimited CSV support
- **Neighborhood merging**: Combine multiple CSVs per neighborhood

## 🎯 Usage Examples

### Basic Loading with Schema
```python
from src.loader import ConfigurableDataLoader

# Schema automatically loaded from schema/Discover Denver Schema.txt
loader = ConfigurableDataLoader('config/data.json')
data = loader.load_all_datasets()

# Access schema information
print(f"Schema fields: {len(loader.schema.fields)}")
print(f"Required fields: {len(loader.schema.get_required_fields())}")
```

### Validation
```python
from src.loader import DatasetValidator

validator = DatasetValidator(loader.schema, error_threshold=10)
results = validator.validate_all_datasets(data)

# Results show ~90% validation rate
print(f"Valid: {results.valid_records}/{results.total_records}")
```

### Rich Data Access
```python
building = data['Clayton-Bungalows'].buildings['DIS.14425']

# Access field with metadata
original_use = building['attributes']['Original Use']
print(original_use['value'])      # "Domestic – Single Dwelling"
print(original_use['required'])   # True
print(original_use['options'])    # List of 33 valid options
```

## 🔄 Design Principles

1. **Schema-First**: Schema drives validation and structure
2. **Threshold Intelligence**: Realistic validation acknowledging data gaps
3. **Type Safety**: Comprehensive type hints throughout
4. **Single Responsibility**: Each module has one clear purpose
5. **Flexibility**: JSON config adapts to any directory structure
6. **Maintainability**: Clean interfaces, comprehensive documentation

## 📊 Validation Results

Across 198 records in 19 datasets:
- **~90% validation rate** (vs 0% before threshold system)
- **Most datasets 87-100% valid**
- **Only 4 records** with >10 missing fields

Common missing fields:
- Building Plan, Roof Features, Architectural Style
- Local/NR Evaluation fields (archival metadata)

This architecture provides a production-ready system for loading, validating, and enriching historical building data for AI training and analysis.
