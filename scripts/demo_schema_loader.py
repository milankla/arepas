"""
Demo script for Discover Denver Schema Loader.

This script demonstrates:
1. Loading the schema
2. Inspecting schema structure
3. Querying field definitions
4. Accessing field options
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.loader import load_schema, SchemaLoader
from loguru import logger

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
)


def main():
    """Run schema loader demo."""
    logger.info("🎯 Discover Denver Schema Loader Demo")
    logger.info("=" * 60)
    
    # 1. Load schema
    logger.info("\n📋 1. Loading Schema")
    logger.info("-" * 60)
    
    schema = load_schema()
    schema.print_summary()
    
    # 2. Query specific fields
    logger.info("\n🔍 2. Querying Specific Fields")
    logger.info("-" * 60)
    
    # Check Building Form field
    building_form = schema.get_field("Building Form")
    if building_form:
        logger.info(f"\n📊 Field: {building_form.name}")
        logger.info(f"   Type: {building_form.field_type}")
        logger.info(f"   Required: {building_form.required}")
        logger.info(f"   Section: {building_form.section}")
        logger.info(f"   Total options: {len(building_form.options)}")
        logger.info(f"\n   Sample options:")
        for opt in list(building_form.options)[:10]:
            logger.info(f"     • {opt.name}")
    
    # Check Architectural Style field
    arch_style = schema.get_field("Architectural Style")
    if arch_style:
        logger.info(f"\n📊 Field: {arch_style.name}")
        logger.info(f"   Type: {arch_style.field_type}")
        logger.info(f"   Required: {arch_style.required}")
        logger.info(f"   Total options: {len(arch_style.options)}")
        logger.info(f"\n   All style options:")
        for opt in sorted(arch_style.options, key=lambda x: x.name):
            logger.info(f"     • {opt.name}")
    
    # 3. Get required fields
    logger.info("\n📝 3. Required Fields Analysis")
    logger.info("-" * 60)
    
    required_fields = schema.get_required_fields()
    logger.info(f"\nTotal required fields: {len(required_fields)}")
    logger.info("\nRequired field names:")
    for field in required_fields:
        logger.info(f"  • {field.name} ({field.field_type})")
    
    # 4. Explore multipart fields
    logger.info("\n🔗 4. Multipart Fields (Complex Fields)")
    logger.info("-" * 60)
    
    multipart_fields = [f for f in schema.fields if f.field_type == 'multipart']
    logger.info(f"\nTotal multipart fields: {len(multipart_fields)}")
    
    for field in multipart_fields:
        logger.info(f"\n📊 {field.name}:")
        logger.info(f"   Question: {field.question}")
        logger.info(f"   Subfields: {len(field.subfields)}")
        for subfield in field.subfields:
            logger.info(f"     • {subfield.name} ({subfield.field_type})")
            if subfield.options:
                logger.info(f"       Options: {len(subfield.options)}")
    
    # 5. Explore sections
    logger.info("\n📂 5. Schema Sections")
    logger.info("-" * 60)
    
    for section in schema.sections:
        fields_in_section = schema.get_fields_by_section(section.section_id)
        logger.info(f"\n{section.name} (ID: {section.section_id})")
        logger.info(f"  Admin only: {section.admin_only}")
        logger.info(f"  Fields: {len(fields_in_section)}")
        if fields_in_section:
            for field in fields_in_section[:3]:  # Show first 3
                logger.info(f"    • {field.name}")
            if len(fields_in_section) > 3:
                logger.info(f"    ... and {len(fields_in_section) - 3} more")
    
    # 6. Survey levels
    logger.info("\n🎯 6. Survey Levels")
    logger.info("-" * 60)
    
    for level in schema.survey_levels:
        logger.info(f"\nLevel {level.level_id}: {level.name}")
        if level.description:
            logger.info(f"  Description: {level.description}")
        logger.info(f"  Skip survey: {level.skip_survey}")
        
        # Count fields for this level
        fields_for_level = [f for f in schema.fields if level.level_id in f.survey_level]
        logger.info(f"  Applicable fields: {len(fields_for_level)}")
    
    logger.info("\n" + "=" * 60)
    logger.success("✅ Schema exploration completed!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
