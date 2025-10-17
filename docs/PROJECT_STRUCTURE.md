# Arepas Project Architecture

## 🏗️ **Data Loading System**

This document outlines the architecture of the Arepas project, a flexible data loading system for processing historical architectural building data.

## 📊 **Project Overview**

This project provides a flexible data loading system for processing historical architectural building data with associated images.

## 📦 **Complete Project Structure**

```
📦 arepas/
├── 🎯 src/                           # Core application source code
│   ├── loader/                       # Data loading system
│   │   ├── __init__.py              # Package exports and public API
│   │   ├── configurable_loader.py   # JSON-driven loader (any structure)
│   │   ├── csv_parser.py            # Robust CSV parsing with validation
│   │   ├── image_index.py           # Image indexing and matching
│   │   └── load_config.py           # Configuration infrastructure
│   ├── fine_tune.py                 # Main pipeline entry point
│   ├── log_config.py                # Logging configuration
│   └── preprocess.py                # Image preprocessing utilities
├── 🔧 scripts/                      # Development and utility scripts
├── 📁 data/                         # Attribute data and images
│   ├── Bungalows/                   # Bungalow architectural style
│   │   ├── Clayton Data - CLEAN.txt
│   │   ├── Cole Data - CLEAN.txt
│   │   ├── Regis - CLEAN.txt
│   │   ├── [... more neighborhood files]
│   │   └── Bungalows - Photos/
│   └── Minimal Traditional/          # Minimal Traditional architectural style
│       ├── Barnum - CLEAN.txt
│       ├── Clayton - CLEAN.txt
│       ├── [... more neighborhood files]
│       └── Minimal Traditional - Photos/
├── 📁 docs/                         # Technical documentation
│   ├── PROJECT_STRUCTURE.md         # This file - architecture documentation
│   └── [Additional documentation]
├── 📋 README.md                     # Main project documentation
├── 🎯 requirements.txt              # Python dependencies
└── 📁 config/                       # Configuration files
    └── data.json                    # Data structure configuration
```

## 🏛️ **Core Architecture Components**

### 1. 🎯 **src/loader/** - Data Loading System

#### **Core Philosophy: Single Responsibility + Flexibility**

| Module | Purpose | Key Features |
|--------|---------|--------------|
| `configurable_loader.py` | JSON-Driven Loading | Flexible structure mapping, any directory layout, CLI support |
| `csv_parser.py` | Robust CSV Processing | Error tolerance, field validation, fallback parsing |
| `image_index.py` | Image Indexing | Hash-based lookups, pattern matching, multi-extension support |
| `load_config.py` | Configuration Infrastructure | JSON loading, validation, error handling |

### 2. 🔧 **scripts/** - Development Utilities

Utility scripts for development and testing purposes.

### 3. 📁 **Data Organization**

#### **data/** - Attribute Files and Images by Architectural Style
- **Organized by style**: Bungalows, Minimal Traditional
- **Clean format**: Standardized CSV files with building attributes
- **Images**: Associated photos organized by architectural style
- **Naming convention**: `{ID}_{ADDRESS}.{HASH}.jpg`

## 🚀 **Technical Features**

### **Image Matching System**
1. **Hash-Based Index**: Pre-built index for efficient image lookups
2. **Pattern Matching**: Multiple matching strategies (ID, street number, Smithsonian numbers)
3. **Multi-Extension Support**: Handles .jpg, .jpeg, .png formats
4. **Memory Efficiency**: Optimized data structures

## 🎯 **API Usage**

### **ConfigurableDataLoader Usage**
```python
from src.loader import ConfigurableDataLoader

# Load all datasets from configuration
loader = ConfigurableDataLoader('config/data.json')
results = loader.load_all_datasets()

print(f"Loaded {len(results)} datasets")

# Get summary statistics
loader.print_summary()
```

## 🔄 **Architecture Evolution**

The project has evolved through several phases:

1. **Initial Implementation**: Basic CSV loading with hardcoded paths
2. **Optimization**: Image indexing system for efficient lookups
3. **Flexibility**: JSON-based configuration for different data structures
4. **Consolidation**: Cleaned up to minimal, maintainable codebase
5. **Production Ready**: Comprehensive error handling and documentation

## 🎯 **Design Principles**

1. **Single Responsibility**: Each module has one clear purpose
2. **Type Safety**: Comprehensive type hints throughout
3. **Error Handling**: Robust error handling with detailed reporting
4. **Flexibility**: JSON-based configuration for any data structure
5. **Maintainability**: Clear interfaces and documentation
6. **Simplicity**: Minimal dependencies, clean codebase

## 🚀 **Extensibility**

The architecture is designed for easy extension:
- **New data structures**: Add via JSON configuration
- **Different data sources**: Implement custom parsers
- **Additional validation**: Extend validation system
- **Custom workflows**: Build on top of the flexible loader

This flexible architecture processes historical building data for AI model training and analysis.
