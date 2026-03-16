"""
Arepas data loader package.

This package provides flexible data loading capabilities for historical
architectural building datasets with CSV attributes and associated images.
"""

from .configurable_loader import ConfigurableDataLoader, NeighborhoodData
from .csv_parser import RobustCSVParser, CSVParseError
from .image_index import ImageIndex
from .schema_loader import SchemaLoader, DiscoverDenverSchema, load_schema
from .architectural_dataset import ArchitecturalDataset, make_splits, PHASE1_LABEL_COLS, LABEL_COLS
from .dataset_validator import (
    DatasetValidator,
    DatasetValidationReport,
    RecordValidationResult,
    FieldValidationError,
    validate_dataset_file
)
from .field_parser import (
    is_empty_value,
    normalize_value,
    parse_multi_value,
    validate_value_against_options,
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
    'ArchitecturalDataset',
    'make_splits',
    'PHASE1_LABEL_COLS',
    'LABEL_COLS',
    'DatasetValidator',
    'DatasetValidationReport',
    'RecordValidationResult',
    'FieldValidationError',
    'validate_dataset_file',
    'is_empty_value',
    'normalize_value',
    'parse_multi_value',
    'validate_value_against_options',
]
