# Arepas

[![CI](https://github.com/your-username/arepas/workflows/CI/badge.svg)](https://github.com/your-username/arepas/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Arepas is a project for fine-tuning an AI model (OpenAI Vision) to categorize historical architectural buildings based on multiple attributes. The project features a high-performance data loading system that processes thousands of buildings with their associated images and architectural attributes.

## Features
- 📊 **Flexible JSON-based configuration** for different data structures
- � **Robust CSV parsing** with error recovery
- � **Efficient image matching** with hash-based indexing
- � **Comprehensive validation** and error handling
- 🎯 **Type-safe operations** throughout the codebase
- � **Advanced logging** with configurable levels

## Getting Started
1. Ensure you have Python 3.8+ installed.
2. (Recommended) Create a virtual environment:
   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
4. Run the main data loading pipeline:
   ```sh
   python -m src.fine_tune
   ```

## Project Structure
```
📦 arepas/
├── 🎯 src/
│   ├── loader/                    # Data loading system
│   │   ├── __init__.py           # Package exports
│   │   ├── configurable_loader.py # JSON-driven data loader
│   │   ├── csv_parser.py         # Robust CSV parsing
│   │   ├── image_index.py        # Image indexing
│   │   └── load_config.py        # Configuration infrastructure
│   ├── fine_tune.py              # Main pipeline entry point
│   ├── log_config.py             # Logging configuration
│   └── preprocess.py             # Image preprocessing utilities
├── 🔧 scripts/                   # Utility scripts
├── 📁 data/                      # Attribute files and images
├── 📄 docs/                      # Technical documentation
└── 🎯 requirements.txt           # Python dependencies
```
```
📦 arepas/
├── 🎯 src/
│   ├── loader/                    # Data loading system
│   │   ├── __init__.py           # Package exports
│   │   ├── configurable_loader.py # JSON-driven data loader
│   │   ├── csv_parser.py         # Robust CSV parsing
│   │   ├── image_index.py        # Image indexing
│   │   └── load_config.py        # Configuration infrastructure
│   ├── fine_tune.py              # Main pipeline entry point
│   ├── log_config.py             # Logging configuration
│   └── preprocess.py             # Image preprocessing utilities
├── 🔧 scripts/                   # Utility scripts
├── 📁 data/                      # Attribute files and images
├── 📄 docs/                      # Technical documentation
└── 🎯 requirements.txt           # Python dependencies
```
```
📦 arepas/
├── 🎯 src/
│   ├── loader/                    # Enterprise data loading system
│   │   ├── __init__.py           # Package exports
│   │   ├── config.py             # Configuration management
│   │   ├── configurable_loader.py # JSON-driven data loader
│   │   ├── csv_parser.py         # Robust CSV parsing
│   │   ├── image_index.py        # High-performance image indexing
│   │   └── load_config.py        # Configuration infrastructure
│   ├── fine_tune.py              # Main pipeline entry point
│   ├── log_config.py             # Logging configuration
│   └── preprocess.py             # Image preprocessing utilities
├── 🔧 scripts/
│   ├── test_performance.py       # Performance benchmarking
│   ├── demo_enhanced_api.py      # API demonstration
│   └── README.md                 # Scripts documentation
├── 📁 data/                      # Original attribute files
├── � docs/                      # Technical documentation
│   ├── PROJECT_STRUCTURE.md      # Detailed architecture
│   ├── RUNNING_FROM_COMMAND_LINE.md  # CLI usage guide
│   └── [6 more technical docs]
└── 🎯 requirements.txt           # Python dependencies
```

## Quick Usage

### Load Data
```python
from src.loader import ConfigurableDataLoader

# Load all datasets from configuration
loader = ConfigurableDataLoader('config/data.json')
results = loader.load_all_datasets()

print(f"Loaded {len(results)} datasets")

# Display summary
loader.print_summary()
```

## Development

### Configuration
The system uses JSON configuration files for flexible data structure mapping:
```python
from src.loader import ConfigurableDataLoader

# Load using custom configuration
loader = ConfigurableDataLoader('config/custom_config.json')

# Or use predefined configuration
loader = ConfigurableDataLoader('config/data.json')
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes and test thoroughly
4. Submit a pull request

### Reporting Issues
- Use GitHub Issues for bug reports and feature requests
- Include detailed reproduction steps and environment info
- Check existing issues before creating new ones

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built for processing historical architectural building data
- Optimized for Denver's architectural survey datasets
- Designed for OpenAI Vision fine-tuning workflows
