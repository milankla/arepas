# Technical Documentation

Technical documentation for the Arepas historical architectural building data system.

## Core Documentation

### Architecture & Design

- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Project architecture overview
  - Data loading system design
  - Schema integration
  - Performance optimizations
  - Directory structure

- **[SCHEMA_INTEGRATION.md](SCHEMA_INTEGRATION.md)** - Schema-aware data loading
  - Discover Denver Schema integration
  - Validation system with intelligent thresholds
  - Rich data structures with field metadata
  - Usage examples

### Usage Guides

- **[RUNNING_FROM_COMMAND_LINE.md](RUNNING_FROM_COMMAND_LINE.md)** - CLI usage guide
  - Running loaders and validators from command line
  - Configuration file usage
  - Demo scripts overview

## Quick Start

```python
from src.loader import ConfigurableDataLoader

# Load data with automatic schema integration
loader = ConfigurableDataLoader('config/data.json')
data = loader.load_all_datasets()

# Validate against schema
from src.loader import DatasetValidator
validator = DatasetValidator(loader.schema)
results = validator.validate_dataset(data)
```

## Additional Resources

- Main project documentation: [../README.md](../README.md)
- Script documentation: [../scripts/README.md](../scripts/README.md)
- Configuration examples: [../config/](../config/)
- Schema definition: [../schema/Discover Denver Schema.txt](../schema/)
