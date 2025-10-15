# Hybrid Solution: Configuration-Driven Data Loading

## Proposed Solution: JSON Metadata File

### Concept
Instead of reorganizing files OR implementing complex dual-structure detection, use a **JSON configuration file** that explicitly maps each dataset to its CSV and image locations.

### Example Configuration File: `data_structure.json`

```json
{
  "version": "1.0",
  "datasets": [
    {
      "name": "Cole-Bungalows",
      "neighborhood": "Cole",
      "style": "Bungalows",
      "csv_file": "data/Bungalows/Cole Data - CLEAN.txt",
      "images_dir": "data/Bungalows/Bungalows - Photos"
    },
    {
      "name": "Cole-MinimalTraditional",
      "neighborhood": "Cole",
      "style": "Minimal Traditional",
      "csv_file": "data/Minimal Traditional/Cole - CLEAN.txt",
      "images_dir": "data/Minimal Traditional/Minimal Traditional - Photos"
    },
    {
      "name": "Cole",
      "neighborhood": "Cole",
      "style": "Mixed",
      "csv_file": "data2/Cole/Cole - CLEAN.txt",
      "images_dir": "data2/Cole"
    },
    {
      "name": "Regis-Bungalows",
      "neighborhood": "Regis",
      "style": "Bungalows",
      "csv_file": "data/Bungalows/Regis - CLEAN.txt",
      "images_dir": "data/Bungalows/Bungalows - Photos"
    },
    {
      "name": "Regis",
      "neighborhood": "Regis",
      "style": "Mixed",
      "csv_file": "data2/Regis/Regis - CLEAN.txt",
      "images_dir": "data2/Regis"
    }
  ]
}
```

### Alternative: Simpler Structure

```json
{
  "version": "1.0",
  "base_path": ".",
  "datasets": {
    "Cole-Bungalows": {
      "csv": "data/Bungalows/Cole Data - CLEAN.txt",
      "images": "data/Bungalows/Bungalows - Photos",
      "metadata": {
        "neighborhood": "Cole",
        "style": "Bungalows"
      }
    },
    "Cole-MinimalTraditional": {
      "csv": "data/Minimal Traditional/Cole - CLEAN.txt",
      "images": "data/Minimal Traditional/Minimal Traditional - Photos",
      "metadata": {
        "neighborhood": "Cole",
        "style": "Minimal Traditional"
      }
    },
    "Cole": {
      "csv": "data2/Cole/Cole - CLEAN.txt",
      "images": "data2/Cole",
      "metadata": {
        "neighborhood": "Cole",
        "style": "Mixed"
      }
    }
  }
}
```

### Auto-Generation Script

```json
{
  "version": "1.0",
  "auto_generated": true,
  "generation_date": "2025-10-13T10:30:00Z",
  "base_path": ".",
  
  "structure_templates": {
    "style_based": {
      "pattern": "data/{style}/{neighborhood}*CLEAN.txt",
      "images": "data/{style}/{style} - Photos"
    },
    "neighborhood_based": {
      "pattern": "data2/{neighborhood}/{neighborhood}*CLEAN.txt",
      "images": "data2/{neighborhood}"
    }
  },
  
  "datasets": [
    "... auto-discovered datasets ..."
  ]
}
```

## Comparison of Solutions

### Solution 1: Migrate data/ to data2/ Structure
**Approach:** Reorganize files to single structure

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Simplicity** | ⭐⭐⭐⭐⭐ | Single loading path, no complexity |
| **Flexibility** | ⭐⭐ | Lose style-based organization |
| **Code Changes** | ⭐⭐⭐⭐⭐ | None needed (already works) |
| **Data Preservation** | ⭐⭐⭐ | Must merge CSVs, reorganize files |
| **Reversibility** | ⭐⭐⭐ | Can restore from backup |
| **Maintenance** | ⭐⭐⭐⭐⭐ | Very low - single structure |

**Pros:**
- ✅ Simplest code (no changes)
- ✅ Single source of truth
- ✅ Easy to understand

**Cons:**
- ❌ Permanent restructuring required
- ❌ Lose style-based folder organization
- ❌ Must merge multiple CSVs
- ❌ Can't easily separate by style

---

### Solution 2: Dual Structure Support (Auto-Detection)
**Approach:** Code detects and handles both structures

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Simplicity** | ⭐⭐ | Complex detection logic |
| **Flexibility** | ⭐⭐⭐⭐ | Works with both structures |
| **Code Changes** | ⭐⭐ | Significant refactoring needed |
| **Data Preservation** | ⭐⭐⭐⭐⭐ | Keep everything as-is |
| **Reversibility** | ⭐⭐⭐⭐⭐ | No file changes |
| **Maintenance** | ⭐⭐ | Higher complexity, more edge cases |

**Pros:**
- ✅ No file reorganization
- ✅ Handles both structures
- ✅ Backwards compatible

**Cons:**
- ❌ Complex detection logic
- ❌ More code to maintain
- ❌ Potential edge cases
- ❌ Still can't mix structures easily

---

### Solution 3: JSON Configuration File (Hybrid) 🌟
**Approach:** Explicit configuration defines all mappings

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Simplicity** | ⭐⭐⭐⭐ | Clean, declarative approach |
| **Flexibility** | ⭐⭐⭐⭐⭐ | Maximum flexibility, any structure |
| **Code Changes** | ⭐⭐⭐ | Moderate refactoring |
| **Data Preservation** | ⭐⭐⭐⭐⭐ | Keep everything as-is |
| **Reversibility** | ⭐⭐⭐⭐⭐ | Just edit JSON |
| **Maintenance** | ⭐⭐⭐⭐ | Clear config, easy debugging |

**Pros:**
- ✅ No file reorganization needed
- ✅ Works with ANY directory structure
- ✅ Can mix data/ and data2/ freely
- ✅ Explicit and self-documenting
- ✅ Easy to add new datasets
- ✅ Can preserve style metadata
- ✅ Version controlled configuration
- ✅ Can generate automatically
- ✅ Easy to debug (just look at JSON)

**Cons:**
- ❌ Requires maintaining JSON file
- ❌ Additional configuration step
- ❌ Manual updates when structure changes

---

## Detailed Hybrid Solution Design

### 1. Configuration Schema

```python
from dataclasses import dataclass
from typing import Optional, Dict, List
from pathlib import Path
import json

@dataclass
class DatasetConfig:
    """Configuration for a single dataset."""
    name: str
    csv_file: str
    images_dir: str
    neighborhood: Optional[str] = None
    style: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None
    
    def validate(self, base_path: Path) -> bool:
        """Validate that paths exist."""
        csv_path = base_path / self.csv_file
        img_path = base_path / self.images_dir
        return csv_path.exists() and img_path.exists()

@dataclass
class DataStructureConfig:
    """Top-level configuration."""
    version: str
    base_path: str
    datasets: List[DatasetConfig]
    
    @classmethod
    def from_json(cls, json_path: str) -> 'DataStructureConfig':
        """Load configuration from JSON file."""
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        datasets = [
            DatasetConfig(**ds) for ds in data.get('datasets', [])
        ]
        
        return cls(
            version=data.get('version', '1.0'),
            base_path=data.get('base_path', '.'),
            datasets=datasets
        )
    
    def get_dataset(self, name: str) -> Optional[DatasetConfig]:
        """Get dataset by name."""
        for ds in self.datasets:
            if ds.name == name:
                return ds
        return None
    
    def get_datasets_by_neighborhood(self, neighborhood: str) -> List[DatasetConfig]:
        """Get all datasets for a neighborhood."""
        return [ds for ds in self.datasets if ds.neighborhood == neighborhood]
```

### 2. Updated Loader

```python
class ConfigurableDataLoader:
    """
    Data loader that uses JSON configuration to locate CSVs and images.
    """
    
    def __init__(self, config_path: str = "data_structure.json"):
        self.config = DataStructureConfig.from_json(config_path)
        self.base_path = Path(self.config.base_path)
        
        # Validate configuration
        invalid = []
        for dataset in self.config.datasets:
            if not dataset.validate(self.base_path):
                invalid.append(dataset.name)
        
        if invalid:
            logger.warning(f"Invalid datasets: {invalid}")
    
    def load_dataset(self, dataset_name: str) -> Dict:
        """Load a specific dataset by name."""
        dataset_config = self.config.get_dataset(dataset_name)
        
        if not dataset_config:
            raise ValueError(f"Dataset '{dataset_name}' not found in configuration")
        
        # Use existing DataLoader with configured paths
        csv_path = self.base_path / dataset_config.csv_file
        images_dir = self.base_path / dataset_config.images_dir
        
        loader = DataLoader(
            images_dir=str(images_dir),
            attributes_file=str(csv_path)
        )
        
        # Load data
        images_result = loader.load_images()
        attrs_result = loader.load_attributes()
        mapping_result = loader.map_images_to_attributes()
        
        return {
            'name': dataset_config.name,
            'neighborhood': dataset_config.neighborhood,
            'style': dataset_config.style,
            'metadata': dataset_config.metadata,
            'images': images_result,
            'attributes': attrs_result,
            'mapping': mapping_result
        }
    
    def load_all_datasets(self) -> List[Dict]:
        """Load all configured datasets."""
        results = []
        for dataset_config in self.config.datasets:
            try:
                result = self.load_dataset(dataset_config.name)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to load {dataset_config.name}: {e}")
        
        return results
    
    def load_neighborhood(self, neighborhood: str, 
                          merge: bool = True) -> Dict:
        """
        Load all datasets for a neighborhood.
        
        Args:
            neighborhood: Neighborhood name
            merge: If True, merge all style datasets for this neighborhood
        """
        datasets_configs = self.config.get_datasets_by_neighborhood(neighborhood)
        
        if not datasets_configs:
            raise ValueError(f"No datasets found for neighborhood '{neighborhood}'")
        
        datasets = [self.load_dataset(ds.name) for ds in datasets_configs]
        
        if merge:
            # Merge multiple style datasets into one
            return self._merge_datasets(datasets, neighborhood)
        else:
            return datasets
    
    def _merge_datasets(self, datasets: List[Dict], neighborhood: str) -> Dict:
        """Merge multiple datasets for the same neighborhood."""
        # Combine all DataFrames
        all_dfs = [ds['attributes'].data for ds in datasets]
        merged_df = pd.concat(all_dfs, ignore_index=True)
        
        # Remove duplicates based on 'id'
        if 'id' in merged_df.columns:
            merged_df = merged_df.drop_duplicates(subset=['id'], keep='first')
        
        # Combine images (already PIL objects)
        all_images = []
        for ds in datasets:
            all_images.extend(ds['images'].data)
        
        return {
            'name': neighborhood,
            'neighborhood': neighborhood,
            'style': 'Mixed',
            'attributes': merged_df,
            'images': all_images,
            'datasets_merged': len(datasets)
        }
```

### 3. Auto-Generation Script

```python
def generate_config_from_structure(root_path: str = ".") -> Dict:
    """
    Automatically discover datasets and generate configuration.
    """
    root = Path(root_path)
    datasets = []
    
    # Scan for style-based structure (data/)
    data_dir = root / "data"
    if data_dir.exists():
        for style_folder in data_dir.iterdir():
            if not style_folder.is_dir():
                continue
            if style_folder.name.endswith(" - Photos"):
                continue
            
            style_name = style_folder.name
            photos_folder = style_folder / f"{style_name} - Photos"
            
            # Find all CSVs in this style folder
            for csv_file in style_folder.glob("*CLEAN.txt"):
                # Extract neighborhood name
                neighborhood = csv_file.stem.replace(" Data - CLEAN", "").replace(" - CLEAN", "")
                
                dataset = {
                    "name": f"{neighborhood}-{style_name}",
                    "csv_file": str(csv_file.relative_to(root)),
                    "images_dir": str(photos_folder.relative_to(root)) if photos_folder.exists() else str(style_folder.relative_to(root)),
                    "neighborhood": neighborhood,
                    "style": style_name
                }
                datasets.append(dataset)
    
    # Scan for neighborhood-based structure (data2/)
    data2_dir = root / "data2"
    if data2_dir.exists():
        for neighborhood_folder in data2_dir.iterdir():
            if not neighborhood_folder.is_dir():
                continue
            
            neighborhood = neighborhood_folder.name
            csv_file = neighborhood_folder / f"{neighborhood} - CLEAN.txt"
            
            if csv_file.exists():
                dataset = {
                    "name": neighborhood,
                    "csv_file": str(csv_file.relative_to(root)),
                    "images_dir": str(neighborhood_folder.relative_to(root)),
                    "neighborhood": neighborhood,
                    "style": "Mixed"
                }
                datasets.append(dataset)
    
    config = {
        "version": "1.0",
        "base_path": ".",
        "generated": True,
        "generation_date": datetime.now().isoformat(),
        "datasets": datasets
    }
    
    return config

def create_config_file(output_path: str = "data_structure.json"):
    """Generate and save configuration file."""
    config = generate_config_from_structure()
    
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Generated configuration: {output_path}")
    print(f"   Found {len(config['datasets'])} datasets")
    
    return config
```

## Migration Plan: Implementing Hybrid Solution

### Phase 1: Generate Initial Configuration (Day 1)
1. Create `scripts/generate_config.py` with auto-discovery
2. Run script to generate `data_structure.json`
3. Manually review and validate JSON
4. Add to version control

### Phase 2: Implement Config-Based Loader (Day 1-2)
1. Create `src/loader/config_schema.py` with dataclasses
2. Create `src/loader/configurable_loader.py` with ConfigurableDataLoader
3. Update existing loader to use config when available
4. Maintain backwards compatibility

### Phase 3: Testing (Day 2)
1. Test loading from data/ (style-based)
2. Test loading from data2/ (neighborhood-based)
3. Test merged neighborhood loading
4. Test configuration validation

### Phase 4: Documentation (Day 3)
1. Document JSON schema
2. Create usage examples
3. Update README
4. Document migration from old loader

### Phase 5: Rollout (Day 3)
1. Update main scripts to use ConfigurableDataLoader
2. Keep old loader for backwards compatibility
3. Add deprecation warnings to old loader

## Usage Examples

### Example 1: Load Specific Dataset
```python
loader = ConfigurableDataLoader("data_structure.json")

# Load specific style/neighborhood combination
cole_bungalows = loader.load_dataset("Cole-Bungalows")
print(f"Loaded {len(cole_bungalows['attributes'].data)} buildings")
```

### Example 2: Load All Data for Neighborhood
```python
# Load and merge all styles for Cole
cole_all = loader.load_neighborhood("Cole", merge=True)
print(f"Cole total buildings: {len(cole_all['attributes'])}")
print(f"Merged from {cole_all['datasets_merged']} datasets")
```

### Example 3: Load Everything
```python
all_data = loader.load_all_datasets()
print(f"Loaded {len(all_data)} datasets")
```

### Example 4: Custom Configuration
```json
{
  "version": "1.0",
  "base_path": "/path/to/project",
  "datasets": [
    {
      "name": "SpecialSet",
      "csv_file": "custom/location/data.txt",
      "images_dir": "custom/images",
      "metadata": {
        "custom_field": "custom_value"
      }
    }
  ]
}
```

## Advantages of Hybrid Solution

### 1. **Maximum Flexibility**
- Works with ANY directory structure
- Can mix data/ and data2/ freely
- Easy to add external datasets

### 2. **No Data Migration**
- Keep files exactly where they are
- No risk of data loss
- No merge conflicts

### 3. **Explicit and Clear**
- Configuration is self-documenting
- Easy to see what's being loaded
- Version controlled

### 4. **Style Preservation**
- Maintain style-based organization in data/
- Can load by style or merged
- Don't lose architectural metadata

### 5. **Easy Debugging**
- Just check JSON if something fails
- Clear error messages
- Can validate configuration independently

### 6. **Incremental Adoption**
- Generate initial config automatically
- Manually refine as needed
- Keep old loader for backwards compatibility

## Comparison Summary

| Feature | Migration | Auto-Detect | JSON Config 🌟 |
|---------|-----------|-------------|----------------|
| Code Simplicity | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| Flexibility | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Data Preservation | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Maintainability | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| Debugging | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Future-Proof | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## Recommendation: JSON Configuration 🎯

**The hybrid JSON configuration solution is the best choice because:**

1. ✅ **No destructive changes** - keep your data as-is
2. ✅ **Maximum flexibility** - works with any structure
3. ✅ **Self-documenting** - clear what's loaded from where
4. ✅ **Easy to extend** - just add entries to JSON
5. ✅ **Preserve metadata** - keep style/neighborhood info
6. ✅ **Version controlled** - JSON in git shows changes
7. ✅ **Auto-generation** - can create initial config automatically
8. ✅ **Gradual migration** - can use for new data while keeping old structure

## Implementation Timeline

- **Day 1 Morning:** Generate config script + schema
- **Day 1 Afternoon:** Implement ConfigurableDataLoader
- **Day 2 Morning:** Testing and validation
- **Day 2 Afternoon:** Documentation
- **Day 3:** Integration and rollout

**Total effort:** ~2-3 days for complete implementation

Would you like me to start implementing this solution?
