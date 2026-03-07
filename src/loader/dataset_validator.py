"""
Dataset Validator for Discover Denver Schema

Validates building records against the Discover Denver schema to ensure data quality.
Checks required fields, valid options, data types, and multipart field structure.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple, TypedDict
from pathlib import Path
from collections import defaultdict
from enum import Enum
import pandas as pd
from loguru import logger

from .schema_loader import DiscoverDenverSchema, SchemaField, load_schema
from .field_parser import is_empty_value, normalize_value, parse_multi_value, validate_value_against_options


# Constants
NEGATIVE_VALUES = frozenset(['No', 'N', 'None', 'N/A'])
TOP_ISSUES_COUNT = 3
MAX_DISPLAYED_ERRORS = 5
DEFAULT_TOP_N = 10


class ValidationErrorType(Enum):
    """Enumeration of validation error types."""
    MISSING_REQUIRED = 'missing_required'
    INVALID_OPTION = 'invalid_option'
    INVALID_TYPE = 'invalid_type'
    EMPTY_REQUIRED = 'empty_required'


class ErrorDict(TypedDict, total=False):
    """Type definition for error dictionaries."""
    field_name: str
    error_type: ValidationErrorType
    message: str
    current_value: Any
    expected_values: List[str]


@dataclass
class FieldValidationError:
    """Represents a validation error for a specific field."""
    field_name: str
    error_type: ValidationErrorType
    message: str
    current_value: Optional[Any] = None
    expected_values: Optional[List[str]] = None


@dataclass
class RecordValidationResult:
    """Validation results for a single building record."""
    record_id: str
    is_valid: bool
    errors: List[FieldValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, field_name: str, error_type: ValidationErrorType, message: str, 
                  current_value: Any = None, expected_values: List[str] = None):
        """Add a validation error."""
        self.is_valid = False
        self.errors.append(FieldValidationError(
            field_name=field_name,
            error_type=error_type,
            message=message,
            current_value=current_value,
            expected_values=expected_values
        ))
    
    def add_warning(self, message: str):
        """Add a validation warning."""
        self.warnings.append(message)


@dataclass
class DatasetValidationReport:
    """Comprehensive validation report for an entire dataset."""
    dataset_name: str
    total_records: int
    valid_records: int
    invalid_records: int
    record_results: List[RecordValidationResult] = field(default_factory=list)
    
    # Summary statistics (using defaultdict for cleaner increment logic)
    missing_required_fields: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    invalid_option_fields: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    empty_required_fields: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    @property
    def validation_rate(self) -> float:
        """Percentage of valid records."""
        if self.total_records == 0:
            return 0.0
        return (self.valid_records / self.total_records) * 100
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get count of each error type."""
        error_counts = {}
        for result in self.record_results:
            for error in result.errors:
                error_counts[error.error_type] = error_counts.get(error.error_type, 0) + 1
        return error_counts
    
    def get_most_common_errors(self, top_n: int = DEFAULT_TOP_N) -> List[Tuple[str, ValidationErrorType, int]]:
        """Get the most common field errors."""
        field_error_counts: Dict[Tuple[str, ValidationErrorType], int] = {}
        
        for result in self.record_results:
            for error in result.errors:
                key = (error.field_name, error.error_type)
                field_error_counts[key] = field_error_counts.get(key, 0) + 1
        
        # Sort by count
        sorted_errors = sorted(field_error_counts.items(), key=lambda x: x[1], reverse=True)
        return [(field, error_type, count) for (field, error_type), count in sorted_errors[:top_n]]
    
    def print_summary(self):
        """
        Print a formatted validation summary.
        
        DEPRECATED: Use ValidationReportPresenter.print_summary(report) instead.
        This method delegates to the presenter for backward compatibility.
        """
        ValidationReportPresenter.print_summary(self)


class ValidationReportPresenter:
    """
    Presenter for formatting and displaying validation reports.
    Separates presentation logic from data structures.
    """
    
    @staticmethod
    def print_summary(report: 'DatasetValidationReport') -> None:
        """Print a formatted validation summary."""
        logger.info("=" * 80)
        logger.info(f"VALIDATION REPORT: {report.dataset_name}")
        logger.info("=" * 80)
        logger.info(f"📊 Total Records: {report.total_records}")
        logger.info(f"✅ Valid Records: {report.valid_records} ({report.validation_rate:.1f}%)")
        logger.info(f"❌ Invalid Records: {report.invalid_records}")
        logger.info("")
        
        if report.invalid_records > 0:
            logger.info("🔍 Error Summary:")
            error_summary = report.get_error_summary()
            for error_type, count in error_summary.items():
                logger.info(f"   • {error_type}: {count}")
            logger.info("")
            
            logger.info("🎯 Most Common Field Errors:")
            common_errors = report.get_most_common_errors(DEFAULT_TOP_N)
            for field_name, error_type, count in common_errors:
                logger.info(f"   • {field_name} ({error_type.value}): {count} records")
            logger.info("")
        
        logger.info("=" * 80)
    
    @staticmethod
    def print_detailed_errors(report: 'DatasetValidationReport', 
                            max_errors_per_record: int = MAX_DISPLAYED_ERRORS) -> None:
        """Print detailed errors for invalid records."""
        logger.info("")
        logger.info("📋 Detailed Errors:")
        for result in report.record_results:
            if not result.is_valid:
                logger.info(f"\n❌ Record: {result.record_id}")
                for error in result.errors[:max_errors_per_record]:
                    logger.info(f"   • {error.field_name}: {error.message}")
                if len(result.errors) > max_errors_per_record:
                    remaining = len(result.errors) - max_errors_per_record
                    logger.info(f"   ... and {remaining} more errors")
    
    @staticmethod
    def print_global_summary(reports: Dict[str, 'DatasetValidationReport']) -> None:
        """Print global summary across multiple datasets."""
        # Aggregate error statistics
        all_missing_required: Dict[str, int] = defaultdict(int)
        all_empty_required: Dict[str, int] = defaultdict(int)
        all_invalid_options: Dict[str, int] = defaultdict(int)
        
        for report in reports.values():
            for field, count in report.missing_required_fields.items():
                all_missing_required[field] += count
            for field, count in report.empty_required_fields.items():
                all_empty_required[field] += count
            for field, count in report.invalid_option_fields.items():
                all_invalid_options[field] += count
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("🌍 GLOBAL VALIDATION STATISTICS")
        logger.info("=" * 80)
        
        # Show top empty/missing required fields
        all_required_issues = {}
        all_required_issues.update(all_empty_required)
        for field, count in all_missing_required.items():
            all_required_issues[field] = all_required_issues.get(field, 0) + count
        
        if all_required_issues:
            top_required = sorted(all_required_issues.items(), 
                                key=lambda x: x[1], reverse=True)[:DEFAULT_TOP_N]
            logger.info("⚠️  Most Commonly Empty Required Fields (across all datasets):")
            for field, count in top_required:
                logger.info(f"   • {field}: {count} records")
            logger.info("")
        
        # Show top invalid option fields
        if all_invalid_options:
            top_invalid = sorted(all_invalid_options.items(), 
                               key=lambda x: x[1], reverse=True)[:DEFAULT_TOP_N]
            logger.info("🔴 Most Common Invalid Option Fields (across all datasets):")
            for field, count in top_invalid:
                logger.info(f"   • {field}: {count} records")
            logger.info("")
        
        logger.info("=" * 80)


class DatasetValidator:
    """
    Validates building records against the Discover Denver schema.
    
    Usage:
        validator = DatasetValidator(schema)
        report = validator.validate_dataframe(df, 'Clayton-Bungalows')
        report.print_summary()
    """
    
    def __init__(self, schema: DiscoverDenverSchema, survey_level: int = 2, 
                 error_threshold: int = 10):
        """
        Initialize validator with schema.
        
        Args:
            schema: The Discover Denver schema to validate against
            survey_level: Survey level to use for required fields (default: 2 = Basic Survey)
            error_threshold: Number of missing/empty required fields before marking record invalid
                           (default: 10). Records with <= threshold errors get warnings instead.
        """
        self.schema = schema
        self.survey_level = survey_level
        self.error_threshold = error_threshold
        self.required_fields = self._get_required_field_names()
        logger.info(f"🔍 Validator initialized with {len(self.required_fields)} required fields")
        logger.info(f"   Error threshold: {error_threshold} missing fields allowed as warnings")
    
    def _get_required_field_names(self) -> Set[str]:
        """Get names of all required fields for the current survey level."""
        required = set()
        for field in self.schema.get_required_fields(self.survey_level):
            required.add(field.name)
        return required
    
    def _create_error_dict(self, field_name: str, error_type: ValidationErrorType, 
                          message: str, current_value: Any = None, 
                          expected_values: Optional[List[str]] = None) -> ErrorDict:
        """Create a standardized error dictionary."""
        error_dict: ErrorDict = {
            'field_name': field_name,
            'error_type': error_type,
            'message': message
        }
        if current_value is not None:
            error_dict['current_value'] = current_value
        if expected_values is not None:
            error_dict['expected_values'] = expected_values
        return error_dict
    
    def _validate_field_options(self, field: SchemaField, value: str) -> Tuple[bool, Optional[List[str]]]:
        """
        Validate that a field value matches allowed options.
        
        Returns:
            (is_valid, expected_values)
        """
        if is_empty_value(value):
            return True, None  # Empty values are handled separately
        
        if not field.options:
            return True, None  # No options to validate against
        
        # Get valid option values
        valid_options = {opt.name for opt in field.options}
        
        # Use shared parser for validation
        is_valid, _ = validate_value_against_options(value, valid_options, field.field_type)
        
        if not is_valid:
            return False, sorted(valid_options)
        return True, None
    
    def _validate_multipart_field(self, field: SchemaField, record: Dict[str, Any], 
                                   potential_errors: List[ErrorDict]) -> None:
        """Validate a multipart field with subfields, collecting errors for threshold logic."""
        # Check if parent field exists (the "Does building have X?" question)
        parent_value = record.get(field.name)
        
        if is_empty_value(parent_value):
            if field.required:
                potential_errors.append(self._create_error_dict(
                    field.name,
                    ValidationErrorType.EMPTY_REQUIRED,
                    f"Required multipart field '{field.name}' is empty"
                ))
            return
        
        # If parent field says "No" or similar, subfields may not be required
        if parent_value in NEGATIVE_VALUES:
            return
        
        # Validate each subfield
        if field.subfields:
            for subfield in field.subfields:
                subfield_value = record.get(subfield.name)
                
                if is_empty_value(subfield_value):
                    if subfield.required:
                        potential_errors.append(self._create_error_dict(
                            subfield.name,
                            ValidationErrorType.EMPTY_REQUIRED,
                            f"Required subfield '{subfield.name}' of '{field.name}' is empty"
                        ))
                elif subfield.options:
                    # Validate subfield options using shared field_parser
                    valid_options = {opt.name for opt in subfield.options}
                    is_valid, invalid_values = validate_value_against_options(
                        subfield_value, valid_options, subfield.field_type
                    )
                    
                    if not is_valid:
                        if invalid_values:
                            message = f"Invalid options in subfield '{subfield.name}': {invalid_values}"
                        else:
                            message = f"Invalid value for subfield '{subfield.name}': '{subfield_value}'"
                        
                        potential_errors.append(self._create_error_dict(
                            subfield.name,
                            ValidationErrorType.INVALID_OPTION,
                            message,
                            current_value=subfield_value,
                            expected_values=sorted(valid_options)
                        ))
    
    def _collect_validation_errors(self, record: Dict[str, Any], 
                                   result: RecordValidationResult) -> List[ErrorDict]:
        """
        Collect all validation errors for a record.
        
        Returns:
            List of error dictionaries
        """
        potential_errors = []
        
        # 1. Check for missing required fields
        record_fields = set(record.keys())
        missing_required = self.required_fields - record_fields
        
        for field_name in missing_required:
            potential_errors.append(self._create_error_dict(
                field_name,
                ValidationErrorType.MISSING_REQUIRED,
                f"Required field '{field_name}' is missing from record"
            ))
        
        # 2. Validate each field in the record
        for field_name, value in record.items():
            field = self.schema.get_field(field_name)
            
            if field is None:
                # Field not in schema - add warning
                result.add_warning(f"Field '{field_name}' not found in schema")
                continue
            
            # Check if required field is empty
            if field.required and is_empty_value(value):
                potential_errors.append(self._create_error_dict(
                    field_name,
                    ValidationErrorType.EMPTY_REQUIRED,
                    f"Required field '{field_name}' is empty",
                    current_value=value
                ))
                continue
            
            # Handle multipart fields specially
            if field.field_type == 'multipart':
                self._validate_multipart_field(field, record, potential_errors)
                continue
            
            # Validate field options
            normalized_value = normalize_value(value)
            if normalized_value:  # Only validate non-empty values
                is_valid, expected_values = self._validate_field_options(field, normalized_value)
                
                if not is_valid:
                    potential_errors.append(self._create_error_dict(
                        field_name,
                        ValidationErrorType.INVALID_OPTION,
                        f"Invalid value for field '{field_name}': '{normalized_value}'",
                        current_value=value,
                        expected_values=expected_values
                    ))
        
        return potential_errors
    
    def _apply_threshold_policy(self, potential_errors: List[ErrorDict], 
                               result: RecordValidationResult, 
                               error_threshold: int) -> None:
        """
        Apply threshold policy to convert errors to warnings based on count.
        
        Args:
            potential_errors: List of error dictionaries
            result: Result object to populate
            error_threshold: Threshold for required field errors
        """
        # Separate required field errors from invalid option errors
        required_field_errors = [
            e for e in potential_errors 
            if e['error_type'] in (ValidationErrorType.MISSING_REQUIRED, 
                                  ValidationErrorType.EMPTY_REQUIRED)
        ]
        invalid_option_errors = [
            e for e in potential_errors 
            if e['error_type'] == ValidationErrorType.INVALID_OPTION
        ]
        
        if len(required_field_errors) <= error_threshold:
            # Convert required field errors to warnings
            for error_info in required_field_errors:
                result.add_warning(
                    f"⚠️  {error_info['message']} "
                    f"({len(required_field_errors)}/{error_threshold} threshold)"
                )
            # But invalid options remain as errors
            for error_info in invalid_option_errors:
                result.add_error(
                    error_info['field_name'],
                    error_info['error_type'],
                    error_info['message'],
                    current_value=error_info.get('current_value'),
                    expected_values=error_info.get('expected_values')
                )
        else:
            # Add all errors - record is invalid
            for error_info in potential_errors:
                result.add_error(
                    error_info['field_name'],
                    error_info['error_type'],
                    error_info['message'],
                    current_value=error_info.get('current_value'),
                    expected_values=error_info.get('expected_values')
                )
    
    def validate_record(self, record: Dict[str, Any], record_id: str, 
                       error_threshold: int = 10) -> RecordValidationResult:
        """
        Validate a single building record.
        
        Args:
            record: Dictionary of field names to values
            record_id: Identifier for the record (e.g., address, ID)
            error_threshold: Number of missing/empty required fields that trigger invalid status.
                           If <= threshold, errors become warnings instead.
        
        Returns:
            RecordValidationResult with validation errors and warnings
        """
        result = RecordValidationResult(record_id=record_id, is_valid=True)
        
        # Collect all validation errors
        potential_errors = self._collect_validation_errors(record, result)
        
        # Apply threshold policy to determine warnings vs errors
        self._apply_threshold_policy(potential_errors, result, error_threshold)
        
        return result
    
    def validate_dataframe(self, df: pd.DataFrame, dataset_name: str, 
                           id_column: str = 'Address') -> DatasetValidationReport:
        """
        Validate an entire DataFrame of building records.
        
        Args:
            df: DataFrame containing building records
            dataset_name: Name of the dataset for reporting
            id_column: Column to use as record identifier
        
        Returns:
            DatasetValidationReport with comprehensive validation results
        """
        logger.info(f"🔍 Validating dataset: {dataset_name}")
        logger.info(f"   Records: {len(df)}")
        logger.info(f"   Columns: {len(df.columns)}")
        
        report = DatasetValidationReport(
            dataset_name=dataset_name,
            total_records=len(df),
            valid_records=0,
            invalid_records=0
        )
        
        # Validate each record (using to_dict('records') for better performance)
        records = df.to_dict('records')
        for idx, record in enumerate(records):
            # Get record ID
            if id_column in record:
                record_id = str(record[id_column])
            else:
                record_id = f"Record_{idx}"
            
            # Validate record with threshold
            result = self.validate_record(record, record_id, error_threshold=self.error_threshold)
            report.record_results.append(result)
            
            # Update counts
            if result.is_valid:
                report.valid_records += 1
            else:
                report.invalid_records += 1
                
                # Track error frequencies (using defaultdict for clean increments)
                for error in result.errors:
                    if error.error_type == ValidationErrorType.MISSING_REQUIRED:
                        report.missing_required_fields[error.field_name] += 1
                    elif error.error_type == ValidationErrorType.INVALID_OPTION:
                        report.invalid_option_fields[error.field_name] += 1
                    elif error.error_type == ValidationErrorType.EMPTY_REQUIRED:
                        report.empty_required_fields[error.field_name] += 1
        
        # Build validation message with missing field info
        if report.valid_records == report.total_records:
            logger.success(f"✅ Validation complete: {report.valid_records}/{report.total_records} valid records")
        else:
            # Get top 3 most common missing/empty fields
            missing_summary = []
            
            # Combine empty and missing required fields
            all_issues = {}
            all_issues.update(report.empty_required_fields)
            all_issues.update(report.missing_required_fields)
            
            # Sort by frequency and get top N
            top_issues = sorted(all_issues.items(), key=lambda x: x[1], reverse=True)[:TOP_ISSUES_COUNT]
            
            if top_issues:
                field_names = [name for name, _ in top_issues]
                missing_summary = f" (missing: {', '.join(field_names)})"
            else:
                missing_summary = ""
            
            logger.success(f"✅ Validation complete: {report.valid_records}/{report.total_records} valid records{missing_summary}")
        
        return report
    
    def validate_dataset_dict(self, dataset: Dict[str, pd.DataFrame]) -> Dict[str, DatasetValidationReport]:
        """
        Validate multiple datasets at once.
        
        Args:
            dataset: Dictionary of dataset_name -> DataFrame
        
        Returns:
            Dictionary of dataset_name -> DatasetValidationReport
        """
        reports = {}
        
        logger.info(f"🔍 Validating {len(dataset)} datasets")
        
        for dataset_name, df in dataset.items():
            report = self.validate_dataframe(df, dataset_name)
            reports[dataset_name] = report
        
        # Print overall summary
        total_records = sum(r.total_records for r in reports.values())
        total_valid = sum(r.valid_records for r in reports.values())
        overall_rate = (total_valid / total_records * 100) if total_records > 0 else 0
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("OVERALL VALIDATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"📊 Total Datasets: {len(dataset)}")
        logger.info(f"📊 Total Records: {total_records}")
        logger.info(f"✅ Valid Records: {total_valid} ({overall_rate:.1f}%)")
        logger.info(f"❌ Invalid Records: {total_records - total_valid}")
        logger.info("=" * 80)
        
        return reports


def validate_dataset_file(csv_path: str, schema_path: str = "schema/Discover Denver Schema.txt",
                          survey_level: int = 2) -> DatasetValidationReport:
    """
    Convenience function to validate a CSV file against the schema.
    
    Args:
        csv_path: Path to CSV file
        schema_path: Path to schema file
        survey_level: Survey level for required fields
    
    Returns:
        DatasetValidationReport
    """
    # Load schema
    schema = load_schema(schema_path)
    
    # Load CSV
    df = pd.read_csv(csv_path)
    dataset_name = Path(csv_path).stem
    
    # Validate
    validator = DatasetValidator(schema, survey_level)
    report = validator.validate_dataframe(df, dataset_name)
    
    return report


if __name__ == "__main__":
    # Demo validation
    logger.info("🔍 Dataset Validator Demo")
    logger.info("=" * 80)
    
    # Load schema
    schema = load_schema()
    logger.success(f"✅ Schema loaded: {len(schema.fields)} fields")
    
    # Create sample data for testing
    sample_data = pd.DataFrame([
        {
            'Address': '123 Main St',
            'Original Use': 'Single Dwelling',
            'Current Use': 'Single Dwelling',
            'Stories': '1',
            'Building Category': 'Residential',
            'Building Form': 'Bungalow',
            'Building Plan': 'Rectangle',
            'Architectural Style': 'Craftsman',
            'Setting': 'Streetcar Suburb',
            'Landscape Features': 'Lawn',
            'Roof Type': 'Gable',
            'Roof Materials': 'Asphalt Shingles',
            'Roof Features': 'Exposed Rafters',
            'Primary Cladding': 'Wood - Horizontal Siding',
            'Wall Features': 'None',
            'Alteration Level': '2',
            'Alterations-Additions': 'None',
            'Alterations-Entrances': 'None',
            'Alterations-Roof': 'None',
            'Alterations-Cladding': 'None',
            'Alterations-Windows': 'None',
            'Local Evaluation - Individual': 'Contributing',
            'Local Evaluation - District': 'Contributing',
            'NR Evaluation - Individual': 'Individually Eligible',
            'NR Evaluation - District': 'District Eligible'
        },
        {
            'Address': '456 Oak Ave',
            'Original Use': 'Single Dwelling',
            # Missing many required fields
            'Architectural Style': 'InvalidStyle',  # Invalid option
        }
    ])
    
    # Validate
    validator = DatasetValidator(schema, survey_level=2)
    report = validator.validate_dataframe(sample_data, "Sample Dataset")
    
    # Print report using presenter
    ValidationReportPresenter.print_summary(report)
    
    # Show detailed errors for invalid records using presenter
    ValidationReportPresenter.print_detailed_errors(report)
