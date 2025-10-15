# Dual Data Structure Analysis

## Executive Summary

This document analyzes the structural differences between the `data/` and `data2/` folders to design a dual-support loading system. Currently, the loader only works with `data2`.

## Structural Comparison

### `data/` Structure - Style-Based Organization
```
data/
├── Bungalows/                          # Style folder (Level 1)
│   ├── Clayton Data - CLEAN.txt        # Neighborhood CSV
│   ├── Cole Data - CLEAN.txt
│   ├── Regis - CLEAN.txt
│   ├── Skyland - CLEAN.txt
│   ├── South City Park - CLEAN.txt
│   ├── Sunnyside - CLEAN.txt
│   ├── Villa Park - CLEAN.txt
│   ├── Westwood - CLEAN.txt
│   ├── Whittier - CLEAN.txt
│   └── Bungalows - Photos/            # Centralized photos folder
│       └── [image files]
│
└── Minimal Traditional/                # Style folder (Level 1)
    ├── Barnum - CLEAN.txt
    ├── Clayton - CLEAN.txt
    ├── Cole - CLEAN.txt
    ├── Regis - CLEAN.txt
    ├── Skyland - CLEAN.txt
    ├── South City Park - CLEAN.txt
    ├── Sunnyside - CLEAN.txt
    ├── Valverde - CLEAN.txt
    ├── Villa Park - CLEAN.txt
    ├── Westwood - CLEAN.txt
    └── Minimal Traditional - Photos/   # Centralized photos folder
        └── [image files]
```

**Key Characteristics:**
- **Hierarchy:** 3 levels (root → style → neighborhood CSVs + photos)
- **CSV Location:** Inside style folders
- **CSV Naming:** `{Neighborhood} Data - CLEAN.txt` (e.g., "Cole Data - CLEAN.txt")
- **Image Location:** Centralized in `{Style} - Photos/` subfolder
- **Organization:** Grouped by architectural style first, then neighborhood

### `data2/` Structure - Neighborhood-Based Organization
```
data2/
├── Cole/                               # Neighborhood folder (Level 1)
│   ├── Cole - CLEAN.txt                # CSV file
│   ├── 5DV.1011_3280_N_DOWNING_ST.tKLg0.jpg
│   ├── 5DV.1011_3280_N_DOWNING_ST.4i2OOT.jpg
│   └── [1000+ more image files]
│
├── Regis/                              # Neighborhood folder (Level 1)
│   ├── Regis - CLEAN.txt
│   └── [1000+ image files]
│
├── Skyland/
├── South City Park/
├── Streetcar Commercial/
└── Sunnyside/
```

**Key Characteristics:**
- **Hierarchy:** 2 levels (root → neighborhood folder)
- **CSV Location:** Directly in neighborhood folder
- **CSV Naming:** `{Neighborhood} - CLEAN.txt` (e.g., "Cole - CLEAN.txt")
- **Image Location:** Co-located with CSV in same directory
- **Organization:** Flat structure grouped by neighborhood only

## CSV Content Comparison

### Content Structure
Both CSV files have **identical column structures**:
- Tab-delimited format
- Same header columns (id, status, address, smithsonianNumber, etc.)
- Same data types and patterns

### Example Headers (Both Identical)
```
"id"    "status"    "address"    "attributesDefinitionId"    "surveyLevel"    
"surveyedAt"    "createdAt"    "updatedAt"    "yearBuilt"    
"smithsonianNumber"    "city"    "township"    "range"    "section"    
...
```

### Key CSV Fields for Image Matching
- `smithsonianNumber`: e.g., "5DV.4594" (used in image filenames)
- `id`: e.g., "DIS.3176" (building identifier)
- `address`: e.g., "3226 N RACE ST"

## Image Naming Pattern (Both Structures)

Images follow the same naming convention in both structures:
```
{smithsonian_number}_{address}.{hash}.{extension}

Examples:
5DV.4594_3226_N_RACE_ST.tKLg0.jpg
5DV.45154_3818_N_FRANKLIN_ST.pdDf9m.jpg
5DV.41609_4815_N_SHERIDAN_BLVD.RxsPXE.jpg
```

**Pattern Components:**
- Smithsonian number (e.g., "5DV.4594")
- Address with underscores (e.g., "3226_N_RACE_ST")
- Random hash (e.g., "tKLg0")
- Extension (typically ".jpg")

## Detection Strategy

### How to Automatically Detect Structure Type

```python
def detect_structure_type(root_path: Path) -> str:
    """
    Detect whether we're dealing with data/ or data2/ structure.
    
    Returns: 'style-based' or 'neighborhood-based'
    """
    subdirs = [d for d in root_path.iterdir() if d.is_dir()]
    
    # Check for style folders with " - Photos" pattern
    photo_folders = [d for d in subdirs if d.name.endswith(" - Photos")]
    
    if photo_folders:
        return 'style-based'  # data/ structure
    
    # Check for CSV files directly in subdirectories
    for subdir in subdirs:
        csv_files = list(subdir.glob("*CLEAN.txt"))
        if csv_files:
            # Check if images are co-located
            images = list(subdir.glob("*.jpg"))
            if images:
                return 'neighborhood-based'  # data2/ structure
    
    raise ValueError("Could not determine structure type")
```

### Detection Criteria

| Feature | data/ (Style-Based) | data2/ (Neighborhood-Based) |
|---------|---------------------|----------------------------|
| Top-level folders | Style names (Bungalows, Minimal Traditional) | Neighborhood names (Cole, Regis) |
| Contains " - Photos" folders | ✅ Yes | ❌ No |
| CSV naming | `{Neighborhood} Data - CLEAN.txt` | `{Neighborhood} - CLEAN.txt` |
| Images co-located with CSV | ❌ No | ✅ Yes |
| Directory depth | 3 levels | 2 levels |

## Implementation Plan

### Phase 1: Structure Detection
1. Create `structure_detector.py` module
2. Implement automatic structure type detection
3. Add validation for each structure type

### Phase 2: Path Resolution Abstraction
1. Create `PathResolver` base class
2. Implement `StyleBasedPathResolver` for data/
3. Implement `NeighborhoodBasedPathResolver` for data2/
4. Each resolver handles:
   - CSV file location
   - Image directory location
   - File naming patterns

### Phase 3: Unified Loader Interface
1. Update `NeighborhoodDataLoader` to accept structure type
2. Use appropriate path resolver based on detection
3. Handle both structures transparently

### Phase 4: Testing
1. Test with data/ structure
2. Test with data2/ structure
3. Test structure auto-detection
4. Verify image-to-attribute mapping works for both

## Code Architecture

### Proposed Class Hierarchy

```
DataStructure (ABC)
├── load_neighborhoods() -> List[str]
├── get_csv_path(neighborhood: str) -> Path
├── get_images_dir(neighborhood: str) -> Path
└── get_csv_naming_pattern() -> str

StyleBasedStructure(DataStructure)
├── Handles data/ structure
├── Returns style/neighborhood paths
└── Resolves to centralized Photos folder

NeighborhoodBasedStructure(DataStructure)
├── Handles data2/ structure
├── Returns neighborhood paths
└── Resolves to neighborhood folder for images
```

### Integration with Existing Code

The `NeighborhoodDataLoader` will be updated to:
```python
class NeighborhoodDataLoader:
    def __init__(self, root_dir: str, structure: Optional[DataStructure] = None):
        self.root_dir = Path(root_dir)
        
        # Auto-detect if not provided
        if structure is None:
            structure_type = detect_structure_type(self.root_dir)
            if structure_type == 'style-based':
                self.structure = StyleBasedStructure(self.root_dir)
            else:
                self.structure = NeighborhoodBasedStructure(self.root_dir)
        else:
            self.structure = structure
    
    def load_neighborhood(self, neighborhood: str):
        csv_path = self.structure.get_csv_path(neighborhood)
        images_dir = self.structure.get_images_dir(neighborhood)
        # ... rest of loading logic
```

## Edge Cases and Considerations

### 1. Mixed Structures
**Issue:** What if user has both data/ and data2/ in workspace?
**Solution:** Always require explicit root directory specification

### 2. CSV Naming Variations
**Issue:** "Cole Data - CLEAN.txt" vs "Cole - CLEAN.txt"
**Solution:** Use fuzzy matching or pattern detection for CSV discovery

### 3. Missing Photos Folders
**Issue:** What if "Style - Photos" folder doesn't exist in data/?
**Solution:** Graceful fallback with clear error message

### 4. Image Resolution Performance
**Issue:** Searching centralized Photos folder might be slower
**Solution:** Build image index once, cache lookups

### 5. Neighborhood Name Extraction
**Issue:** Extracting "Cole" from "Cole Data - CLEAN.txt"
**Solution:** Strip " Data - CLEAN.txt" suffix using regex

## Testing Strategy

### Unit Tests
- Test structure detection with mock directories
- Test path resolution for each structure type
- Test CSV name pattern matching

### Integration Tests
- Load actual data from data/ folder
- Load actual data from data2/ folder
- Verify identical output format

### Performance Tests
- Compare loading times between structures
- Measure image index building time
- Optimize if necessary

## Migration Path

### For Users with data/ structure:
1. System auto-detects style-based structure
2. Loader uses StyleBasedStructure resolver
3. No code changes required by user

### For Users with data2/ structure:
1. System auto-detects neighborhood-based structure
2. Loader uses NeighborhoodBasedStructure resolver
3. Continues to work exactly as before (backwards compatible)

### For Users with custom structures:
1. Implement custom `DataStructure` subclass
2. Pass to loader explicitly
3. System adapts to custom logic

## Next Steps

1. ✅ Complete this analysis document
2. 📋 Review and approve architecture design
3. 📋 Implement `structure_detector.py`
4. 📋 Create `DataStructure` abstraction classes
5. 📋 Update `NeighborhoodDataLoader` with dual support
6. 📋 Write comprehensive tests
7. 📋 Update documentation and README
8. 📋 Validate with real data from both structures

## Conclusion

The two structures differ primarily in their organizational hierarchy:
- **data/**: Style-first organization with centralized images
- **data2/**: Neighborhood-first organization with co-located images

Both structures contain identical CSV content and image naming patterns, making a unified loading interface feasible. The key is implementing proper path resolution based on automatic structure detection.

The proposed abstraction layer will allow seamless support for both structures while maintaining backwards compatibility with existing data2/ workflows.
