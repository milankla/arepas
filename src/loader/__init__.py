"""
Arepas Data Loader Package

This package contains all the data loading functionality for the Arepas project,
including CSV parsing, image indexing, and JSON-driven configuration.
"""

# Core loading classes
from .configurable_loader import ConfigurableDataLoader, NeighborhoodData

# Specialized components
from .csv_parser import RobustCSVParser, CSVParseError
from .image_index import ImageIndex

# Convenience exports for common usage patterns
__all__ = [
    # Main classes
    'ConfigurableDataLoader',
    'NeighborhoodData',
    
    # Components
    'RobustCSVParser',
    'ImageIndex',
    
    # Exceptions
    'CSVParseError',
]
