"""
Demo: Dataset Validation with Discover Denver Schema

Shows how to validate building datasets against the schema to ensure data quality.
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path so 'src' is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.loader import (
    ConfigurableDataLoader,
    load_schema,
    DatasetValidator
)

# Configure logger to remove file name and line numbers
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    colorize=True,
    level="INFO"  # Only show INFO and above (no DEBUG)
)


def main():
    logger.info("=" * 80)
    logger.info("🔍 DATASET VALIDATION DEMO")
    logger.info("=" * 80)
    logger.info("")
    
    # 1. Load the schema
    logger.info("📋 Step 1: Loading Discover Denver Schema")
    logger.info("-" * 80)
    schema = load_schema()
    logger.success(f"✅ Schema loaded: {len(schema.fields)} fields")
    logger.info("")
    
    # 2. Load datasets
    logger.info("📂 Step 2: Loading Datasets")
    logger.info("-" * 80)
    
    # Temporarily disable detailed logging from loader
    logger.disable("src.loader")
    
    loader = ConfigurableDataLoader('config/data.json')
    all_data = loader.load_all_datasets()
    
    # Re-enable logging
    logger.enable("src.loader")
    
    # Extract DataFrames from NeighborhoodData objects
    # New structure: attributes are now dicts with {'value': ..., 'type': ..., 'required': ..., 'options': ...}
    # We need to extract just the values for validation
    datasets = {}
    for name, neighborhood in all_data.items():
        if neighborhood.buildings:
            # Extract attributes from each building
            import pandas as pd
            attributes_list = []
            for building_id, building_data in neighborhood.buildings.items():
                if 'attributes' in building_data and building_data['attributes']:
                    # Extract values from the nested structure
                    attrs = {}
                    for field_name, field_data in building_data['attributes'].items():
                        # Each field is now a dict with 'value', 'type', 'required', 'options'
                        if isinstance(field_data, dict) and 'value' in field_data:
                            attrs[field_name] = field_data['value']
                        else:
                            # Fallback for any fields that aren't in new format
                            attrs[field_name] = field_data
                    
                    # Add the building_id
                    attrs['id'] = building_id
                    attributes_list.append(attrs)
            
            if attributes_list:
                datasets[name] = pd.DataFrame(attributes_list)
    
    total_buildings = sum(len(df) for df in datasets.values())
    logger.success(f"✅ Loaded {len(datasets)} datasets with {total_buildings} total buildings")
    logger.info("")
    
    # 3. Create validator
    logger.info("🔧 Step 3: Creating Validator")
    logger.info("-" * 80)
    validator = DatasetValidator(schema, survey_level=2)  # Survey Level 2 = Basic Survey
    logger.success(f"✅ Validator created with {len(validator.required_fields)} required fields")
    logger.info("")
    
    # 4. Validate all datasets
    logger.info("🔍 Step 4: Validating All Datasets")
    logger.info("-" * 80)
    reports = validator.validate_dataset_dict(datasets)
    logger.info("")
    
    # 5. Show detailed report for each dataset
    logger.info("=" * 80)
    logger.info("📊 DETAILED VALIDATION REPORTS")
    logger.info("=" * 80)
    logger.info("")
    
    # Only show first 3 datasets in detail to reduce noise
    datasets_shown = 0
    max_datasets_to_show = 3
    
    for dataset_name, report in reports.items():
        if datasets_shown < max_datasets_to_show:
            report.print_summary()
            
            # Show sample errors for datasets with issues
            if report.invalid_records > 0:
                logger.info("")
                logger.info(f"📋 Sample Errors from {dataset_name}:")
                
                # Show errors from first invalid record only
                error_count = 0
                for result in report.record_results:
                    if not result.is_valid and error_count < 1:
                        logger.info(f"\n   Record: {result.record_id}")
                        for error in result.errors[:3]:  # Show first 3 errors per record
                            if error.error_type == 'missing_required':
                                logger.info(f"      ❌ Missing: {error.field_name}")
                            elif error.error_type == 'empty_required':
                                logger.info(f"      ⚠️  Empty: {error.field_name}")
                            elif error.error_type == 'invalid_option':
                                logger.info(f"      🔴 Invalid: {error.field_name} = '{error.current_value}'")
                        error_count += 1
                
                logger.info("")
            
            logger.info("")
            datasets_shown += 1
    
    if len(reports) > max_datasets_to_show:
        logger.info(f"... and {len(reports) - max_datasets_to_show} more datasets (omitted for brevity)")
        logger.info("")
    
    # 6. Global statistics using presenter
    from src.loader.dataset_validator import ValidationReportPresenter
    ValidationReportPresenter.print_global_summary(reports)
    
    logger.success("✅ Validation complete!")
    logger.info("=" * 80)
    
    # 7. Return reports for further analysis
    return reports


if __name__ == "__main__":
    reports = main()
