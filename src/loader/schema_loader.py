"""
Schema loader for Discover Denver architectural survey data.

This module loads and validates schema definitions that describe the expected
structure and fields for architectural survey datasets.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class FieldOption:
    """Represents a single option for a field."""
    name: str
    conditions: Optional[Dict[str, List[str]]] = None  # "if" conditions
    
    @classmethod
    def from_dict(cls, data: Any) -> 'FieldOption':
        """Create FieldOption from dictionary or string."""
        if isinstance(data, str):
            return cls(name=data, conditions=None)
        elif isinstance(data, dict):
            return cls(
                name=data.get('name', ''),
                conditions=data.get('if')
            )
        else:
            raise ValueError(f"Invalid option format: {data}")


@dataclass
class MultipartSubfield:
    """Represents a subfield within a multipart field."""
    name: str
    field_type: str  # 'single', 'multi', 'text', 'longtext'
    options: List[FieldOption] = field(default_factory=list)
    required: bool = False
    survey_level: List[int] = field(default_factory=list)
    hint: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MultipartSubfield':
        """Create MultipartSubfield from dictionary."""
        options_data = data.get('options', [])
        options = [FieldOption.from_dict(opt) for opt in options_data] if options_data else []
        
        return cls(
            name=data['name'],
            field_type=data['type'],
            options=options,
            required=data.get('required', False),
            survey_level=data.get('surveyLevel', []),
            hint=data.get('hint')
        )


@dataclass
class SchemaField:
    """Represents a field definition in the schema."""
    name: str
    field_type: str  # 'single', 'multi', 'text', 'longtext', 'multipart'
    section: int
    required: bool
    survey_level: List[int]
    hint: Optional[str] = None
    options: List[FieldOption] = field(default_factory=list)
    question: Optional[str] = None  # For multipart fields
    statement: Optional[str] = None  # For multipart fields
    subfields: List[MultipartSubfield] = field(default_factory=list)  # For multipart fields
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SchemaField':
        """Create SchemaField from dictionary."""
        # Handle options
        options_data = data.get('options', [])
        options = [FieldOption.from_dict(opt) for opt in options_data] if options_data else []
        
        # Handle multipart subfields
        subfields = []
        if data.get('type') == 'multipart' and 'fields' in data:
            subfields = [MultipartSubfield.from_dict(sf) for sf in data['fields']]
        
        return cls(
            name=data['name'],
            field_type=data['type'],
            section=data['section'],
            required=data['required'],
            survey_level=data.get('surveyLevel', []),
            hint=data.get('hint'),
            options=options,
            question=data.get('question'),
            statement=data.get('statement'),
            subfields=subfields
        )
    
    def get_all_option_names(self) -> Set[str]:
        """Get all possible option names for this field."""
        return {opt.name for opt in self.options}
    
    def is_valid_option(self, value: str) -> bool:
        """Check if a value is a valid option for this field."""
        return value in self.get_all_option_names()


@dataclass
class SchemaSection:
    """Represents a section in the schema."""
    section_id: int
    name: str
    hint: Optional[str]
    admin_only: bool
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SchemaSection':
        """Create SchemaSection from dictionary."""
        return cls(
            section_id=data['id'],
            name=data['name'],
            hint=data.get('hint'),
            admin_only=data.get('admin_only', False)
        )


@dataclass
class SurveyLevel:
    """Represents a survey level definition."""
    level_id: int
    name: str
    description: Optional[str]
    skip_survey: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SurveyLevel':
        """Create SurveyLevel from dictionary."""
        return cls(
            level_id=data['id'],
            name=data['name'],
            description=data.get('description'),
            skip_survey=data.get('skip_survey', False)
        )


@dataclass
class DiscoverDenverSchema:
    """Complete schema for Discover Denver architectural survey."""
    fields: List[SchemaField]
    sections: List[SchemaSection]
    survey_levels: List[SurveyLevel]
    _field_map: Dict[str, SchemaField] = field(default_factory=dict, init=False, repr=False)
    
    def __post_init__(self):
        """Build lookup maps after initialization."""
        self._field_map = {f.name: f for f in self.fields}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DiscoverDenverSchema':
        """Create schema from dictionary."""
        fields = [SchemaField.from_dict(f) for f in data.get('fields', [])]
        sections = [SchemaSection.from_dict(s) for s in data.get('sections', [])]
        survey_levels = [SurveyLevel.from_dict(sl) for sl in data.get('surveyLevels', [])]
        
        return cls(
            fields=fields,
            sections=sections,
            survey_levels=survey_levels
        )
    
    def get_field(self, field_name: str) -> Optional[SchemaField]:
        """Get a field by name."""
        return self._field_map.get(field_name)
    
    def get_field_names(self) -> Set[str]:
        """Get all field names in the schema."""
        return set(self._field_map.keys())
    
    def get_required_fields(self, survey_level: Optional[int] = None) -> List[SchemaField]:
        """
        Get all required fields, optionally filtered by survey level.
        
        Args:
            survey_level: Filter fields by survey level (0-4)
        
        Returns:
            List of required SchemaField objects
        """
        required = [f for f in self.fields if f.required]
        
        if survey_level is not None:
            required = [f for f in required if survey_level in f.survey_level]
        
        return required
    
    def get_fields_by_section(self, section_id: int) -> List[SchemaField]:
        """Get all fields in a specific section."""
        return [f for f in self.fields if f.section == section_id]
    
    def get_section(self, section_id: int) -> Optional[SchemaSection]:
        """Get a section by ID."""
        for section in self.sections:
            if section.section_id == section_id:
                return section
        return None
    
    def get_survey_level(self, level_id: int) -> Optional[SurveyLevel]:
        """Get a survey level by ID."""
        for level in self.survey_levels:
            if level.level_id == level_id:
                return level
        return None
    
    def print_summary(self) -> None:
        """Print a summary of the schema."""
        logger.info("\n" + "=" * 60)
        logger.info("DISCOVER DENVER SCHEMA SUMMARY")
        logger.info("=" * 60)
        
        logger.info(f"\n📊 Total Fields: {len(self.fields)}")
        logger.info(f"   - Required: {len([f for f in self.fields if f.required])}")
        logger.info(f"   - Optional: {len([f for f in self.fields if not f.required])}")
        
        # Count by type
        type_counts = {}
        for field in self.fields:
            type_counts[field.field_type] = type_counts.get(field.field_type, 0) + 1
        
        logger.info(f"\n📋 Fields by Type:")
        for field_type, count in sorted(type_counts.items()):
            logger.info(f"   - {field_type}: {count}")
        
        logger.info(f"\n📂 Sections: {len(self.sections)}")
        for section in self.sections:
            field_count = len(self.get_fields_by_section(section.section_id))
            logger.info(f"   - {section.name} ({section.section_id}): {field_count} fields")
        
        logger.info(f"\n🎯 Survey Levels: {len(self.survey_levels)}")
        for level in self.survey_levels:
            logger.info(f"   - {level.name} ({level.level_id})")
        
        logger.info("=" * 60 + "\n")


class SchemaLoader:
    """Loader for Discover Denver schema files."""
    
    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize schema loader.
        
        Args:
            schema_path: Path to schema JSON file. If None, uses default location.
        """
        if schema_path is None:
            schema_path = "schema/Discover Denver Schema.txt"
        
        self.schema_path = Path(schema_path)
        self.schema: Optional[DiscoverDenverSchema] = None
    
    def load_schema(self) -> DiscoverDenverSchema:
        """
        Load schema from JSON file.
        
        Returns:
            DiscoverDenverSchema object
        
        Raises:
            FileNotFoundError: If schema file doesn't exist
            json.JSONDecodeError: If schema file is not valid JSON
        """
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")
        
        logger.info(f"Loading schema from: {self.schema_path}")
        
        try:
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)
            
            self.schema = DiscoverDenverSchema.from_dict(schema_data)
            
            logger.success(f"✅ Schema loaded successfully: {len(self.schema.fields)} fields")
            
            return self.schema
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse schema JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load schema: {e}")
            raise
    
    def get_schema(self) -> DiscoverDenverSchema:
        """
        Get loaded schema, loading it if necessary.
        
        Returns:
            DiscoverDenverSchema object
        """
        if self.schema is None:
            self.load_schema()
        return self.schema


# Convenience function
def load_schema(schema_path: Optional[str] = None) -> DiscoverDenverSchema:
    """
    Load Discover Denver schema from file.
    
    Args:
        schema_path: Path to schema JSON file
    
    Returns:
        DiscoverDenverSchema object
    """
    loader = SchemaLoader(schema_path)
    return loader.load_schema()


# Main execution when run as script
if __name__ == "__main__":
    import sys
    
    # Configure logging for direct execution
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    
    # Determine which schema to load
    schema_path = None
    if len(sys.argv) > 1:
        schema_path = sys.argv[1]
    
    logger.info("🔍 Loading Discover Denver Schema...")
    
    try:
        # Load schema
        schema = load_schema(schema_path)
        
        # Print summary
        schema.print_summary()
        
        # Show some example fields
        logger.info("📋 Example Fields:")
        logger.info("")
        
        for field in schema.fields[:5]:
            logger.info(f"  • {field.name}")
            logger.info(f"    Type: {field.field_type}")
            logger.info(f"    Required: {field.required}")
            if field.options:
                logger.info(f"    Options: {len(field.options)} available")
            logger.info("")
        
        logger.success("✅ Schema loading completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to load schema: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
