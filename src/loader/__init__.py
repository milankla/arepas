"""
Arepas data loader package.

This package provides flexible data loading capabilities for historical
architectural building datasets with CSV attributes and associated images.
"""

from .configurable_loader import ConfigurableDataLoader, NeighborhoodData
from .csv_parser import RobustCSVParser, CSVParseError
from .image_index import ImageIndex
from .schema_loader import SchemaLoader, DiscoverDenverSchema, load_schema
from .dataset_validator import (
    DatasetValidator,
    DatasetValidationReport,
    RecordValidationResult,
    FieldValidationError,
    validate_dataset_file
)

__all__ = [
    'ConfigurableDataLoader',
    'NeighborhoodData',
    'RobustCSVParser',
    'CSVParseError',
    'ImageIndex',
    'SchemaLoader',
    'DiscoverDenverSchema',
    'load_schema',
    'DatasetValidator',
    'DatasetValidationReport',
    'RecordValidationResult',
    'FieldValidationError',
    'validate_dataset_file',
]
