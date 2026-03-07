"""
Field Coverage Report

Analyzes which fields are present/missing across all datasets.
Shows detailed statistics for each field in the schema.
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
import pandas as pd


def main():
    logger.info("=" * 80)
    logger.info("📊 FIELD COVERAGE ANALYSIS")
    logger.info("=" * 80)
    logger.info("")
    
    # 1. Load schema
    logger.info("📋 Loading Schema...")
    schema = load_schema()
    logger.info(f"✅ Loaded {len(schema.fields)} fields")
    logger.info("")
    
    # 2. Load all datasets
    logger.info("📂 Loading Datasets...")
    loader = ConfigurableDataLoader('config/data.json')
    all_data = loader.load_all_datasets()
    
    # Convert to DataFrames
    datasets = {}
    for name, neighborhood in all_data.items():
        if neighborhood.buildings:
            datasets[name] = pd.DataFrame.from_dict(neighborhood.buildings, orient='index')
    
    total_buildings = sum(len(df) for df in datasets.values())
    logger.info(f"✅ Loaded {len(datasets)} datasets with {total_buildings} buildings")
    logger.info("")
    
    # 3. Combine all records
    logger.info("🔗 Combining all records...")
    all_records = pd.concat(datasets.values(), ignore_index=True)
    logger.info(f"✅ Combined dataset: {len(all_records)} records, {len(all_records.columns)} columns")
    logger.info("")
    
    # 4. Analyze field coverage
    logger.info("=" * 80)
    logger.info("📊 FIELD COVERAGE REPORT")
    logger.info("=" * 80)
    logger.info("")
    
    # Get all fields from schema
    schema_fields = {field.name: field for field in schema.fields}
    
    # Track statistics
    field_stats = []
    
    for field_name, field_def in sorted(schema_fields.items()):
        # Check if field exists in data
        if field_name in all_records.columns:
            present_count = all_records[field_name].notna().sum()
            missing_count = total_buildings - present_count
            empty_count = all_records[field_name].isna().sum()
            coverage_pct = (present_count / total_buildings) * 100
            
            field_stats.append({
                'field': field_name,
                'type': field_def.field_type,
                'required': field_def.required,
                'present': present_count,
                'missing': missing_count,
                'coverage': coverage_pct,
                'in_data': True
            })
        else:
            # Field not in data at all
            field_stats.append({
                'field': field_name,
                'type': field_def.field_type,
                'required': field_def.required,
                'present': 0,
                'missing': total_buildings,
                'coverage': 0.0,
                'in_data': False
            })
    
    # Convert to DataFrame for easy analysis
    stats_df = pd.DataFrame(field_stats)
    
    # 5. Required Fields Analysis
    logger.info("🔴 REQUIRED FIELDS (Survey Level 2)")
    logger.info("-" * 80)
    required_fields = stats_df[stats_df['required'] == True].sort_values('coverage')
    
    logger.info(f"Total required fields: {len(required_fields)}")
    logger.info("")
    
    for _, row in required_fields.iterrows():
        status = "✅" if row['coverage'] == 100 else "❌"
        in_data_marker = "📋" if row['in_data'] else "🚫"
        logger.info(f"{status} {in_data_marker} {row['field']:<35} | "
                   f"Present: {row['present']:>3}/{total_buildings} ({row['coverage']:>5.1f}%) | "
                   f"Missing: {row['missing']:>3} | "
                   f"Type: {row['type']}")
    
    logger.info("")
    logger.info("Legend: ✅=100% coverage, ❌=incomplete, 📋=in data, 🚫=not in data")
    logger.info("")
    
    # 6. Optional Fields Analysis
    logger.info("=" * 80)
    logger.info("📘 OPTIONAL FIELDS")
    logger.info("-" * 80)
    optional_fields = stats_df[stats_df['required'] == False].sort_values('coverage', ascending=False)
    
    logger.info(f"Total optional fields: {len(optional_fields)}")
    logger.info("")
    
    for _, row in optional_fields.iterrows():
        status = "✅" if row['coverage'] == 100 else "📊" if row['coverage'] > 0 else "⚪"
        in_data_marker = "📋" if row['in_data'] else "🚫"
        logger.info(f"{status} {in_data_marker} {row['field']:<35} | "
                   f"Present: {row['present']:>3}/{total_buildings} ({row['coverage']:>5.1f}%) | "
                   f"Missing: {row['missing']:>3} | "
                   f"Type: {row['type']}")
    
    logger.info("")
    logger.info("Legend: ✅=100% coverage, 📊=partial, ⚪=0%, 📋=in data, 🚫=not in data")
    logger.info("")
    
    # 7. Summary Statistics
    logger.info("=" * 80)
    logger.info("📈 SUMMARY STATISTICS")
    logger.info("=" * 80)
    logger.info("")
    
    # Fields by coverage
    full_coverage = len(stats_df[stats_df['coverage'] == 100])
    partial_coverage = len(stats_df[(stats_df['coverage'] > 0) & (stats_df['coverage'] < 100)])
    no_coverage = len(stats_df[stats_df['coverage'] == 0])
    
    logger.info(f"📊 Coverage Distribution:")
    logger.info(f"   • 100% coverage: {full_coverage} fields")
    logger.info(f"   • Partial coverage: {partial_coverage} fields")
    logger.info(f"   • 0% coverage: {no_coverage} fields")
    logger.info("")
    
    # Required vs optional
    req_full = len(stats_df[(stats_df['required'] == True) & (stats_df['coverage'] == 100)])
    req_total = len(stats_df[stats_df['required'] == True])
    opt_full = len(stats_df[(stats_df['required'] == False) & (stats_df['coverage'] == 100)])
    opt_total = len(stats_df[stats_df['required'] == False])
    
    logger.info(f"🔴 Required Fields:")
    logger.info(f"   • Complete: {req_full}/{req_total} ({req_full/req_total*100:.1f}%)")
    logger.info(f"   • Incomplete: {req_total - req_full}/{req_total}")
    logger.info("")
    
    logger.info(f"📘 Optional Fields:")
    logger.info(f"   • Complete: {opt_full}/{opt_total} ({opt_full/opt_total*100:.1f}%)")
    logger.info(f"   • Incomplete: {opt_total - opt_full}/{opt_total}")
    logger.info("")
    
    # Fields not in data at all
    not_in_data = stats_df[~stats_df['in_data']]
    logger.info(f"🚫 Fields Not Present in Data: {len(not_in_data)}")
    if len(not_in_data) > 0:
        logger.info(f"   Fields completely missing from CSV files:")
        for _, row in not_in_data.iterrows():
            req_marker = "🔴" if row['required'] else "📘"
            logger.info(f"      {req_marker} {row['field']} ({row['type']})")
    logger.info("")
    
    # Fields in data but not in schema
    data_fields = set(all_records.columns)
    schema_field_names = set(schema_fields.keys())
    extra_fields = data_fields - schema_field_names
    
    if extra_fields:
        logger.info(f"⚠️  Fields in Data but NOT in Schema: {len(extra_fields)}")
        for field in sorted(extra_fields):
            non_null = all_records[field].notna().sum()
            logger.info(f"      • {field} (present in {non_null}/{total_buildings} records)")
        logger.info("")
    
    # 8. Top Missing Required Fields
    logger.info("=" * 80)
    logger.info("🎯 TOP 10 MISSING REQUIRED FIELDS")
    logger.info("=" * 80)
    logger.info("")
    
    top_missing_required = required_fields.nlargest(10, 'missing')
    for i, (_, row) in enumerate(top_missing_required.iterrows(), 1):
        logger.info(f"{i:2d}. {row['field']:<35} Missing: {row['missing']:>3}/{total_buildings} records ({100-row['coverage']:.1f}%)")
    
    logger.info("")
    logger.info("=" * 80)
    logger.success("✅ Field coverage analysis complete!")
    logger.info("=" * 80)
    
    return stats_df


if __name__ == "__main__":
    stats_df = main()
