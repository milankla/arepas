"""
Dataset Validator for Discover Denver Schema

Validates building records against the Discover Denver schema to ensure data quality.
Checks required fields, valid options, data types, and multipart field structure.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple
from pathlib import Path
import pandas as pd
from loguru import logger

from .schema_loader import DiscoverDenverSchema, SchemaField, load_schema


@dataclass
class FieldValidationError:
    """Represents a validation error for a specific field."""
    field_name: str
    error_type: str  # 'missing_required', 'invalid_option', 'invalid_type', 'empty_required'
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
    
    def add_error(self, field_name: str, error_type: str, message: str, 
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
    
    # Summary statistics
    missing_required_fields: Dict[str, int] = field(default_factory=dict)
    invalid_option_fields: Dict[str, int] = field(default_factory=dict)
    empty_required_fields: Dict[str, int] = field(default_factory=dict)
    
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
    
    def get_most_common_errors(self, top_n: int = 10) -> List[Tuple[str, str, int]]:
        """Get the most common field errors."""
        field_error_counts: Dict[Tuple[str, str], int] = {}
        
        for result in self.record_results:
            for error in result.errors:
                key = (error.field_name, error.error_type)
                field_error_counts[key] = field_error_counts.get(key, 0) + 1
        
        # Sort by count
        sorted_errors = sorted(field_error_counts.items(), key=lambda x: x[1], reverse=True)
        return [(field, error_type, count) for (field, error_type), count in sorted_errors[:top_n]]
    
    def print_summary(self):
        """Print a formatted validation summary."""
        logger.info("=" * 80)
        logger.info(f"VALIDATION REPORT: {self.dataset_name}")
        logger.info("=" * 80)
        logger.info(f"📊 Total Records: {self.total_records}")
        logger.info(f"✅ Valid Records: {self.valid_records} ({self.validation_rate:.1f}%)")
        logger.info(f"❌ Invalid Records: {self.invalid_records}")
        logger.info("")
        
        if self.invalid_records > 0:
            logger.info("🔍 Error Summary:")
            error_summary = self.get_error_summary()
            for error_type, count in error_summary.items():
                logger.info(f"   • {error_type}: {count}")
            logger.info("")
            
            logger.info("🎯 Most Common Field Errors:")
            common_errors = self.get_most_common_errors(10)
            for field_name, error_type, count in common_errors:
                logger.info(f"   • {field_name} ({error_type}): {count} records")
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
    
    def _is_empty_value(self, value: Any) -> bool:
        """Check if a value is empty (None, NaN, empty string, etc.)."""
        if value is None:
            return True
        if pd.isna(value):
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        return False
    
    def _normalize_value(self, value: Any) -> str:
        """Normalize a value for comparison."""
        if self._is_empty_value(value):
            return ""
        return str(value).strip()
    
    def _parse_multi_value(self, value: str) -> List[str]:
        """Parse a multi-value field (comma or semicolon separated)."""
        if self._is_empty_value(value):
            return []
        
        # Try different separators
        if ';' in value:
            values = [v.strip() for v in value.split(';')]
        elif ',' in value:
            values = [v.strip() for v in value.split(',')]
        else:
            values = [value.strip()]
        
        return [v for v in values if v]  # Remove empty strings
    
    def _validate_field_options(self, field: SchemaField, value: str) -> Tuple[bool, Optional[List[str]]]:
        """
        Validate that a field value matches allowed options.
        
        Returns:
            (is_valid, expected_values)
        """
        if self._is_empty_value(value):
            return True, None  # Empty values are handled separately
        
        if not field.options:
            return True, None  # No options to validate against
        
        # Get valid option values
        valid_options = {opt.name for opt in field.options}
        
        if field.field_type == 'multi':
            # Multi-select field: check each value
            values = self._parse_multi_value(value)
            invalid_values = [v for v in values if v not in valid_options]
            if invalid_values:
                return False, sorted(list(valid_options))
            return True, None
        else:
            # Single-select field: check exact match
            if value not in valid_options:
                return False, sorted(list(valid_options))
            return True, None
    
    def _validate_multipart_field(self, field: SchemaField, record: Dict[str, Any], 
                                   potential_errors: List[Dict]):
        """Validate a multipart field with subfields, collecting errors for threshold logic."""
        # Check if parent field exists (the "Does building have X?" question)
        parent_value = record.get(field.name)
        
        if self._is_empty_value(parent_value):
            if field.required:
                potential_errors.append({
                    'field_name': field.name,
                    'error_type': 'empty_required',
                    'message': f"Required multipart field '{field.name}' is empty"
                })
            return
        
        # If parent field says "No" or similar, subfields may not be required
        if parent_value in ['No', 'N', 'None', 'N/A']:
            return
        
        # Validate each subfield
        if field.subfields:
            for subfield in field.subfields:
                subfield_value = record.get(subfield.name)
                
                if self._is_empty_value(subfield_value):
                    if subfield.required:
                        potential_errors.append({
                            'field_name': subfield.name,
                            'error_type': 'empty_required',
                            'message': f"Required subfield '{subfield.name}' of '{field.name}' is empty"
                        })
                elif subfield.options:
                    # Validate subfield options
                    valid_options = {opt.name for opt in subfield.options}
                    
                    if subfield.field_type == 'multi':
                        values = self._parse_multi_value(str(subfield_value))
                        invalid_values = [v for v in values if v not in valid_options]
                        if invalid_values:
                            potential_errors.append({
                                'field_name': subfield.name,
                                'error_type': 'invalid_option',
                                'message': f"Invalid options in subfield '{subfield.name}': {invalid_values}",
                                'current_value': subfield_value,
                                'expected_values': sorted(list(valid_options))
                            })
                    else:
                        if str(subfield_value) not in valid_options:
                            potential_errors.append({
                                'field_name': subfield.name,
                                'error_type': 'invalid_option',
                                'message': f"Invalid value for subfield '{subfield.name}': '{subfield_value}'",
                                'current_value': subfield_value,
                                'expected_values': sorted(list(valid_options))
                            })
    
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
        
        # Collect all errors first, then decide if they should be errors or warnings
        potential_errors = []
        
        # 1. Check for missing required fields
        record_fields = set(record.keys())
        missing_required = self.required_fields - record_fields
        
        for field_name in missing_required:
            potential_errors.append({
                'field_name': field_name,
                'error_type': 'missing_required',
                'message': f"Required field '{field_name}' is missing from record"
            })
        
        # 2. Validate each field in the record
        for field_name, value in record.items():
            field = self.schema.get_field(field_name)
            
            if field is None:
                # Field not in schema - add warning
                result.add_warning(f"Field '{field_name}' not found in schema")
                continue
            
            # Check if required field is empty
            if field.required and self._is_empty_value(value):
                potential_errors.append({
                    'field_name': field_name,
                    'error_type': 'empty_required',
                    'message': f"Required field '{field_name}' is empty",
                    'current_value': value
                })
                continue
            
            # Handle multipart fields specially
            if field.field_type == 'multipart':
                self._validate_multipart_field(field, record, potential_errors)
                continue
            
            # Validate field options
            normalized_value = self._normalize_value(value)
            if normalized_value:  # Only validate non-empty values
                is_valid, expected_values = self._validate_field_options(field, normalized_value)
                
                if not is_valid:
                    result.add_error(
                        field_name,
                        'invalid_option',
                        f"Invalid value for field '{field_name}': '{normalized_value}'",
                        current_value=value,
                        expected_values=expected_values
                    )
        
        # Apply threshold logic: if <= threshold missing/empty fields, convert to warnings
        # Invalid options always remain as errors
        required_field_errors = [e for e in potential_errors 
                                if e['error_type'] in ('missing_required', 'empty_required')]
        invalid_option_errors = [e for e in potential_errors 
                                if e['error_type'] == 'invalid_option']
        
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
        
        # Validate each record
        for idx, row in df.iterrows():
            # Get record ID
            if id_column in row:
                record_id = str(row[id_column])
            else:
                record_id = f"Record_{idx}"
            
            # Convert row to dictionary
            record = row.to_dict()
            
            # Validate record with threshold
            result = self.validate_record(record, record_id, error_threshold=self.error_threshold)
            report.record_results.append(result)
            
            # Update counts
            if result.is_valid:
                report.valid_records += 1
            else:
                report.invalid_records += 1
                
                # Track error frequencies
                for error in result.errors:
                    if error.error_type == 'missing_required':
                        report.missing_required_fields[error.field_name] = \
                            report.missing_required_fields.get(error.field_name, 0) + 1
                    elif error.error_type == 'invalid_option':
                        report.invalid_option_fields[error.field_name] = \
                            report.invalid_option_fields.get(error.field_name, 0) + 1
                    elif error.error_type == 'empty_required':
                        report.empty_required_fields[error.field_name] = \
                            report.empty_required_fields.get(error.field_name, 0) + 1
        
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
            
            # Sort by frequency and get top 3
            top_issues = sorted(all_issues.items(), key=lambda x: x[1], reverse=True)[:3]
            
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
    
    # Print report
    report.print_summary()
    
    # Show detailed errors for invalid records
    logger.info("")
    logger.info("📋 Detailed Errors:")
    for result in report.record_results:
        if not result.is_valid:
            logger.info(f"\n❌ Record: {result.record_id}")
            for error in result.errors[:5]:  # Show first 5 errors
                logger.info(f"   • {error.field_name}: {error.message}")
