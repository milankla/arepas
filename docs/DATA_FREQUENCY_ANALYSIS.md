# Data Frequency Analysis

Frequency counts are computed **per building** (not per image). All percentages are out of total buildings in the dataset.  
Multi-label fields (e.g. `setting`) count each tag independently, so percentages can exceed 100%.

> **⚠ Updated May 13, 2026:** Phase 1 `data2` counts were recomputed from the corrected `data2/image_label_mapping_phase1.csv` (7,135 buildings) after the building ID truncation bug fix. The prior document used the broken 759-building sample.

---

## Overview

| | `data` | `data2` |
|---|---|---|
| **Total buildings** | 197 | 7,135 |
| **Total images** | 701 | 26,160 |
| **Avg images / building** | 3.56 | 3.67 |
| **Neighborhoods** | 10 | 6 |
| **Source styles** | Bungalow, Minimal Traditional | Mixed (residential + commercial) |

---

## Neighborhoods

### `data` — 197 buildings

| Neighborhood | Buildings | % |
|---|---|---|
| Sunnyside | 69 | 35.0% |
| Skyland | 40 | 20.3% |
| Clayton | 18 | 9.1% |
| Regis | 16 | 8.1% |
| South City Park | 15 | 7.6% |
| Villa Park | 13 | 6.6% |
| Westwood | 11 | 5.6% |
| Cole | 8 | 4.1% |
| Barnum | 4 | 2.0% |
| Valverde | 3 | 1.5% |

### `data2` — 7,135 buildings

| Neighborhood | Buildings | % |
|---|---|---|
| Sunnyside | 2,843 | 39.8% |
| Regis | 1,367 | 19.2% |
| Cole | 1,137 | 15.9% |
| Skyland | 1,122 | 15.7% |
| South City Park | 444 | 6.2% |
| Streetcar Commercial | 222 | 3.1% |

---

## Attribute Frequency Tables

### `architectural_style`

Phase 1 task. 6 classes in `data`, 37 classes in `data2`.

| Style | `data` (197) | % | `data2` (7,135) | % |
|---|---|---|---|---|
| No Clear Architectural Style | 101 | 51.3% | 3,565 | 50.0% |
| Craftsman | 69 | 35.0% | 1,361 | 19.1% |
| Ranch | 18 | 9.1% | 745 | 10.4% |
| Victorian Cottage | — | — | 369 | 5.2% |
| Edwardian | — | — | 323 | 4.5% |
| English Norman Cottage | 5 | 2.5% | 196 | 2.7% |
| Modern Movement | — | — | 138 | 1.9% |
| Classical Revival | 2 | 1.0% | 81 | 1.1% |
| Mixed Style | 2 | 1.0% | 65 | 0.9% |
| Queen Anne | — | — | 62 | 0.9% |
| Dutch Colonial Revival | — | — | 51 | 0.7% |
| Contemporary | — | — | 34 | 0.5% |
| Mission | — | — | 29 | 0.4% |
| Italianate | — | — | 24 | 0.3% |
| Tudor Revival | — | — | 16 | 0.2% |
| Mediterranean Revival | — | — | 10 | 0.1% |
| Colonial Revival | — | — | 9 | 0.1% |
| Other Style | — | — | 7 | 0.1% |
| International Style | — | — | 5 | 0.1% |
| Pueblo Revival | — | — | 5 | 0.1% |
| Art Deco | — | — | 5 | 0.1% |
| Rustic | — | — | 4 | 0.1% |
| Moderne | — | — | 4 | 0.1% |
| Swiss Chalet | — | — | 4 | 0.1% |
| *(13 classes with 1–3 buildings)* | — | — | 22 | 0.3% |

> **Note:** "No Clear Architectural Style" is the majority class (~50–51%) in both datasets. With 7,135 buildings the picture has improved significantly: Victorian Cottage (369), Edwardian (323), English Norman Cottage (196) are now viable as standalone classes. Classes with <10 buildings should still be grouped into "Other Style" or dropped.

---

### `building_form`

Phase 2 task. 2 classes in `data` (by design — only two styles were surveyed), 32 classes in `data2`.

#### `data` (197 buildings)

| Form | Count | % |
|---|---|---|
| Minimal Traditional | 120 | 60.9% |
| Bungalow | 77 | 39.1% |

#### `data2` (7,135 buildings)

| Form | Count | % |
|---|---|---|
| Bungalow | 1,542 | 21.6% |
| Minimal Traditional | 1,333 | 18.7% |
| Gable Front | 909 | 12.7% |
| Classic Cottage | 491 | 6.9% |
| Ranch | 405 | 5.7% |
| Central Block with Projecting Bays | 346 | 4.8% |
| Terrace Type | 312 | 4.4% |
| Duplex | 288 | 4.0% |
| Other | 240 | 3.4% |
| Apartment - Block | 154 | 2.2% |
| Foursquare | 145 | 2.0% |
| Hipped-Roof Box | 142 | 2.0% |
| Transitional Ranch | 131 | 1.8% |
| One-Part Commercial Block | 110 | 1.5% |
| Commercial/Industrial Block | 105 | 1.5% |
| Gabled Ell | 94 | 1.3% |
| Bi-Level | 93 | 1.3% |
| Commercial - Other | 43 | 0.6% |
| Apartment - Garden Court | 41 | 0.6% |
| Split Level | 34 | 0.5% |
| Two-Part Commercial Block | 28 | 0.4% |
| Central Passage Double-Pile | 28 | 0.4% |
| Hall and Parlor | 21 | 0.3% |
| Shotgun | 20 | 0.3% |
| Service Bay Business | 16 | 0.2% |
| House with Commercial Addition | 12 | 0.2% |
| Apartment - Complex | 9 | 0.1% |
| Strip Mall or Shopping Center | 9 | 0.1% |
| Apartment - Courtyard | 7 | 0.1% |
| Neo-Mansard | 6 | 0.1% |
| Cape Cod | 6 | 0.1% |
| I-House | 4 | 0.1% |
| *(7 classes with 1–3 buildings)* | 7 | 0.1% |

> **Note:** 39 classes in `data2`. With 7,135 buildings, the top 17 classes all have ≥94 buildings and can be trained standalone. Forms with <10 buildings (Gas Station variants, Quonset, Rowhouse, High-Rise, Apartment - Dingbat) should be merged into "Other" or dropped.

---

### `roof_type`

Phase 1 task. 19 classes in `data`, 40 classes in `data2` (raw). Multi-roof compounds recorded as semicolon-separated strings.

#### `data` (197 buildings)

| Roof Type | Count | % |
|---|---|---|
| Hipped | 75 | 38.1% |
| Cross Gable | 33 | 16.8% |
| Side Gable | 31 | 15.7% |
| Hip-on-Gable | 16 | 8.1% |
| Front Gable | 12 | 6.1% |
| Cross Hip-on-Gable | 8 | 4.1% |
| Hipped; Front Gable | 6 | 3.0% |
| Compound Roof; Hipped; Front Gable | 3 | 1.5% |
| Compound Roof; Cross Gable; Hipped | 2 | 1.0% |
| Front Gable; Hipped | 2 | 1.0% |
| *(10 rare compound types, 1 each)* | 9 | 4.6% |

#### `data2` (7,135 buildings)

| Roof Type | Count | % |
|---|---|---|
| Hipped | 2,067 | 29.0% |
| Front Gable | 1,257 | 17.6% |
| Cross Gable | 1,030 | 14.4% |
| Side Gable | 880 | 12.3% |
| Flat | 658 | 9.2% |
| Hip-on-Gable | 204 | 2.9% |
| Hipped; Front Gable | 180 | 2.5% |
| Cross Hip-on-Gable | 144 | 2.0% |
| Compound Roof | 126 | 1.8% |
| Front Gable; Hipped | 83 | 1.2% |
| Gambrel | 52 | 0.7% |
| Compound Roof; Front Gable; Hipped | 31 | 0.4% |
| Compound Roof; Hipped; Front Gable | 28 | 0.4% |
| Cross Gable; Hipped | 23 | 0.3% |
| Pyramidal | 19 | 0.3% |
| Mansard | 14 | 0.2% |
| Hipped; Pyramidal | 14 | 0.2% |
| Hipped; Cross Gable | 14 | 0.2% |
| Dutch Hipped | 12 | 0.2% |
| Front Gable; Shed | 12 | 0.2% |
| *(~80 rare compound types, 1–13 each)* | 282 | 3.9% |

> **Note:** `data` lacks Flat roofs entirely (residential only). `data2` Flat (9.2%) comes from commercial buildings. Top 5 simple types now have 658–2,067 buildings each — well-trained standalone. Gambrel (52) is newly viable. The long compound tail (~80 types) should be merged into a "Compound" bucket for all types with <20 buildings.

---

### `primary_cladding`

Phase 1 task. Raw values vs. 8-class coarsened scheme used in training.

#### Raw values — `data` (197 buildings)

| Cladding | Count | % |
|---|---|---|
| Brick | 142 | 72.1% |
| Shingles - Asbestos | 16 | 8.1% |
| Stucco - Historic | 11 | 5.6% |
| Siding - Aluminum | 9 | 4.6% |
| Concrete - Block | 8 | 4.1% |
| Siding - Horizontal, Wood | 5 | 2.5% |
| Siding - Horizontal, Unknown Material | 2 | 1.0% |
| Shingles - Unknown | 2 | 1.0% |
| Stone - Rusticated | 1 | 0.5% |
| Shingles - Plain | 1 | 0.5% |

#### Raw values — `data2` (7,135 buildings)

| Cladding | Count | % |
|---|---|---|
| Brick | 4,976 | 69.7% |
| Siding - Vinyl | 544 | 7.6% |
| Stucco - Modern | 441 | 6.2% |
| Stucco - Historic | 386 | 5.4% |
| Siding - Horizontal, Unknown Material | 156 | 2.2% |
| Siding - Horizontal, Wood | 155 | 2.2% |
| Siding - Aluminum | 129 | 1.8% |
| Shingles - Asbestos | 95 | 1.3% |
| Concrete - Block | 58 | 0.8% |
| Stone - Faux | 36 | 0.5% |
| Siding - Vertical, Unknown Material | 33 | 0.5% |
| Sheet Metal | 28 | 0.4% |
| Shingles - Plain | 23 | 0.3% |
| Concrete - Modular/Precast | 14 | 0.2% |
| Other Cladding | 14 | 0.2% |
| Siding - Vertical, Wood | 15 | 0.2% |
| Stone - Rusticated | 8 | 0.1% |
| Siding - Board and Batten | 7 | 0.1% |
| Unknown Cladding | 6 | 0.1% |
| Shingles - Asphalt | 5 | 0.1% |
| *(5 rare types, 1–2 each)* | 5 | 0.1% |

#### Coarsened (8-class) — training scheme

The `CLADDING_COARSEN_MAP` in `src/loader/architectural_dataset.py` groups raw values into 8 classes:

| Coarse Class | `data` | % | `data2` | % |
|---|---|---|---|---|
| Brick | 142 | 72.1% | 4,976 | 69.7% |
| Stucco | 11 | 5.6% | 827 | 11.6% |
| Siding - Vinyl | 0 | 0.0% | 544 | 7.6% |
| Siding - Other | 16 | 8.1% | 488 | 6.8% |
| Shingles | 19 | 9.6% | 123 | 1.7% |
| Concrete / Stone | 8 | 4.1% | 109 | 1.5% |
| Sheet Metal | 0 | 0.0% | 28 | 0.4% |
| Other Cladding | 1 | 0.5% | 40 | 0.6% |

> **Key imbalance:** Brick accounts for ~70–72% of all buildings across both datasets. This remains the primary driver of poor cladding macro-F1. However, with 7,135 buildings, Stucco (827), Siding-Vinyl (544), and Siding-Other (488) all have enough examples for meaningful learning — weighted loss or oversampling should now significantly improve minority-class F1.

---

### `stories`

Phase 1 task. `data` is heavily 1-story (91.9%); `data2` is more varied.

| Stories | `data` (197) | % | `data2` (7,135) | % |
|---|---|---|---|---|
| 1 | 181 | 91.9% | 4,921 | 69.0% |
| 1-1/2 | 15 | 7.6% | 1,483 | 20.8% |
| 2 | 1 | 0.5% | 633 | 8.9% |
| 2-1/2 | — | — | 58 | 0.8% |
| 3 | — | — | 18 | 0.3% |
| 1/2 | — | — | 4 | 0.1% |
| 4 | — | — | 8 | 0.1% |
| 5–9 | — | — | 7 | 0.1% |
| 3-1/2 | — | — | 2 | 0.0% |
| 10–19 | — | — | 1 | 0.0% |

> **Note:** `data` is essentially a 2-class problem (1 vs. 1-1/2). `data2` includes taller commercial buildings up to 10–19 stories.

---

### `alteration_level`

Phase 1 task (secondary). `data` is almost entirely unaltered (99%). `data2` has a realistic distribution.

| Alteration Level | `data` (197) | % | `data2` (7,135) | % |
|---|---|---|---|---|
| 1 - Completely Altered | — | — | 5 | 0.1% |
| 2 - Major Alterations | — | — | 322 | 4.5% |
| 3 - Moderate Alterations | — | — | 2,270 | 31.8% |
| 4 - Minor Alterations | 2 | 1.0% | 4,127 | 57.8% |
| 5 - Not Altered | 195 | 99.0% | 411 | 5.8% |

> **Note:** `data` was sourced from "Basic Survey" records which are pre-filtered for well-preserved examples — explaining the near-100% "Not Altered" distribution. `data2` reflects the full survey spectrum. The model trained on `data` would not generalize alteration detection at all.

---

### `setting`

Phase 1 task. Multi-label field; each building can have multiple tags.

| Setting Tag | `data` (197) | % | `data2` (7,135) | % |
|---|---|---|---|---|
| Set Back from Sidewalk | 197 | 100.0% | 6,737 | 94.4% |
| Corner | 36 | 18.3% | 1,315 | 18.4% |
| Flush at Sidewalk | — | — | 217 | 3.0% |
| Set at Back of Lot | — | — | 168 | 2.4% |
| Attached on 1 Side | — | — | 59 | 0.8% |
| Attached on 2 Sides | — | — | 26 | 0.4% |

> **Note:** `data` has only 2 setting tags (100% Set Back, 18% Corner). `data2` includes "Flush at Sidewalk" and attached-building categories absent from `data` — these are characteristic of the Streetcar Commercial neighborhood.

---

### `chimney_present`

Phase 1 task. Binary label derived from chimney documentation in survey records.

| Chimney | `data` (197) | % | `data2` (7,135) | % |
|---|---|---|---|---|
| No | 186 | 94.4% | 6,914 | 96.9% |
| Yes | 11 | 5.6% | 221 | 3.1% |

> **Note:** Still heavily imbalanced, but "Yes" grows from 18 to 221 buildings in the corrected dataset — enough for focal loss or weighted BCE to make a meaningful attempt. Label quality remains the likely ceiling: chimneys are documented only when explicitly noted in survey text.

---

## Summary: Class Imbalance by Task

| Task | Phase | `data` majority class | `data2` majority class | Concern |
|---|---|---|---|---|
| `architectural_style` | 1 | No Clear Style (51%) | No Clear Style (50%) | 37 classes; top 11 viable standalone (≥29 bldgs) |
| `building_form` | 2 | Minimal Traditional (61%) | Bungalow (22%) | 39 classes; top 17 viable standalone (≥94 bldgs) |
| `roof_type` | 1 | Hipped (38%) | Hipped (29%) | Compound tail; merge types with <20 into "Compound" |
| `primary_cladding` | 1 | Brick (72%) | Brick (70%) | Brick dominates; minority classes now large enough for weighted loss |
| `stories` | 1 | 1 story (92%) | 1 story (69%) | data is near-trivial (2 classes); data2 has 10 |
| `alteration_level` | 1 | 5-Not Altered (99%) | 4-Minor Alt. (58%) | data useless for alteration; data2 viable |
| `setting` | 1 | Set Back (100%) | Set Back (94%) | data has only 2 tags; data2 has 6 |
| `chimney_present` | 1 | No (94%) | No (97%) | Yes class: 221 bldgs — feasible with focal loss |

---

## Notes on Dataset Differences

- **`data`** contains only Bungalows and Minimal Traditionals from residential neighborhoods. All buildings are "Basic Survey" quality, nearly unaltered. It is a clean but narrow slice.
- **`data2`** is the primary training dataset — 7,135 buildings across residential + commercial neighborhoods, covering the full alteration spectrum and architectural variety.
- **Overlap:** Sunnyside, Regis, Cole, Skyland, and South City Park appear in both. The same building IDs may appear if neighborhoods were resurveyed — deduplicate if ever merging.
- **Cladding imbalance** (Brick ~68–72%) is a fundamental data property, not a preprocessing artifact. It will persist regardless of coarsening strategy.
- **`building_form` and `architectural_style`** in `data2` have many classes with <5 buildings — Phase 2 training will require grouping or exclusion of rare classes before fine-tuning.

---

## Phase 2 Attributes

> **⚠ Important: Raw counts vs. training CSV**
>
> Phase 2 and 3 counts are computed from the raw `CLEAN.txt` survey files — **not** from `data2/image_label_mapping_phase1.csv`. The raw files contain every building ever surveyed in each neighborhood, whether or not it has associated photos.
>
> | | `data` | `data2` |
> |---|---|---|
> | Buildings in raw CLEAN.txt files | 196 | **8,208** |
> | Buildings in training CSV (with images) | 197 | **7,135** |
> | Coverage ratio | ~100% | **~87%** |
>
> All percentages in the Phase 2/3 tables use the raw building count (196 / 8,208) as the denominator. To estimate how many positive examples would actually be available during training, multiply any percentage by 7,135 (for `data2`) or 197 (for `data`). For example, `wall_features` Foundation-Not Visible at 32.5% in the raw data implies roughly **2,319 buildings** in the training CSV — solidly learnable. But `roof_features` Eaves-Boxed at 1.1% implies only **~79 training buildings** — still not learnable.
>
> Additionally, Phase 2/3 fields are **not currently extracted** into the training CSV. Any task listed here would require updating the data pipeline before training.

---

### `building_category`

Phase 2 task. `data` is 100% Residential (filtered by design). `data2` shows the full spectrum.

| Category | `data` (196) | % | `data2` (8,208) | % |
|---|---|---|---|---|
| Residential | 196 | 100.0% | 7,026 | 85.6% |
| Commercial | — | — | 366 | 4.5% |
| Other | — | — | 34 | 0.4% |
| Agricultural | — | — | 2 | 0.0% |
| *(no category recorded)* | — | — | 780 | 9.5% |

> **Note:** ~9.5% of `data2` raw records have no Building Category recorded. In the training CSV (759 buildings with images), `building_category` is not extracted — it would need to be added to the CSV pipeline before training.

---

### `building_plan`

Phase 2 candidate. Highly sparse — only filled for full-survey buildings.

| Plan | `data` (196) | % | `data2` (8,208) | % |
|---|---|---|---|---|
| Rectangular Plan | 6 | 3.1% | 223 | 2.7% |
| Irregular Plan | 4 | 2.0% | 99 | 1.2% |
| L-Shaped Plan | 1 | 0.5% | 26 | 0.3% |
| Square Plan | 1 | 0.5% | 9 | 0.1% |
| T-Shaped Plan | — | — | 3 | 0.0% |
| U-Shaped Plan | — | — | 3 | 0.0% |
| Other Plan | — | — | 2 | 0.0% |
| H-Shaped Plan | — | — | 1 | 0.0% |
| *(not recorded)* | 184 | 93.9% | 7,842 | 95.5% |

> **Note:** Building Plan is filled for only ~4–6% of records. Not viable as a training target without major data collection.

---

### `original_use` / `current_use`

Phase 2 candidate (use type classification). `data` is overwhelmingly single-family residential.

#### Original Use — top classes

| Use | `data` (196) | % | `data2` (8,208) | % |
|---|---|---|---|---|
| Domestic – Single Dwelling | 193 | 98.5% | 6,544 | 79.7% |
| Domestic – Multiple Dwelling | 3 | 1.5% | 1,005 | 12.2% |
| Commercial - Retail Store | — | — | 137 | 1.7% |
| Commercial - Other | — | — | 73 | 0.9% |
| Commercial - Warehouse | — | — | 68 | 0.8% |
| Unknown Original Use | — | — | 46 | 0.6% |
| Commercial - Business/Professional | — | — | 37 | 0.5% |
| Commercial - Restaurant | — | — | 29 | 0.4% |
| Religious Facility | — | — | 26 | 0.3% |
| Mixed Use | — | — | 19 | 0.2% |
| *(19 further rare classes)* | — | — | ~130 | ~1.6% |

#### Current Use — top classes

| Use | `data` (196) | % | `data2` (8,208) | % |
|---|---|---|---|---|
| Domestic – Single Dwelling | 190 | 96.9% | 6,362 | 77.5% |
| Domestic – Multiple Dwelling | 5 | 2.6% | 1,146 | 14.0% |
| Commercial - Retail Store | — | — | 108 | 1.3% |
| Commercial - Business/Professional | — | — | 78 | 1.0% |
| Commercial - Restaurant | — | — | 78 | 1.0% |
| Vacant Building | — | — | 37 | 0.5% |
| Commercial - Warehouse | — | — | 55 | 0.7% |
| Religious Facility | — | — | 32 | 0.4% |
| Mixed Use | — | — | 25 | 0.3% |
| *(22 further rare classes)* | — | — | ~66 | ~0.8% |

> **Note:** Use type classification is viable in `data2` for the broad Residential vs. Commercial split, but fine-grained commercial subtypes (restaurant, retail, etc.) are all <2% and would need grouping.

---

### `landscape_features` (multi-label)

Phase 2 candidate. Recorded for nearly all buildings. Tags per building vary from 0 to 8+.

| Feature | `data` (196) | % | `data2` (8,208) | % |
|---|---|---|---|---|
| Walkway - Concrete | 183 | 93.4% | 6,078 | 74.0% |
| Fence - Rear | 146 | 74.5% | 5,575 | 67.9% |
| Fence - Left Side | 54 | 27.6% | 2,476 | 30.2% |
| Fence - Right Side | 56 | 28.6% | 2,475 | 30.2% |
| Driveway - Solid | 52 | 26.5% | 1,919 | 23.4% |
| Wall - Retaining | 31 | 15.8% | 1,810 | 22.1% |
| Fence - Front | 30 | 15.3% | 1,805 | 22.0% |
| Denver Roll | 57 | 29.1% | 1,671 | 20.4% |
| Built-In Planters | 21 | 10.7% | 881 | 10.7% |
| Walkway - Stone | 5 | 2.6% | 513 | 6.2% |
| Parking Lot | — | — | 370 | 4.5% |
| Stone Public Sidewalk | 2 | 1.0% | 308 | 3.8% |
| Fence - Ornamental | 4 | 2.0% | 260 | 3.2% |
| Driveway - Ribbon | 11 | 5.6% | 201 | 2.4% |
| Driveway - Unpaved | 7 | 3.6% | 194 | 2.4% |
| Walkway - Brick | 2 | 1.0% | 168 | 2.0% |
| Fence - Historic | 5 | 2.6% | 102 | 1.2% |
| Wall - Perimeter | — | — | 77 | 0.9% |
| *(4 further rare tags)* | — | — | ~82 | ~1.0% |

> **Note:** Landscape features describe site context, not the building itself. Correlation with architectural attributes may be weak — Parking Lot (4.5%) is a strong commercial indicator.

---

## Phase 3 Attributes

---

### `roof_materials` (multi-label)

Phase 3 task. Extremely dominated by Shingles - Asphalt in both datasets.

| Material | `data` (196) | % | `data2` (8,208) | % |
|---|---|---|---|---|
| Shingles - Asphalt | 193 | 98.5% | 6,323 | 77.0% |
| Unknown Roof Material | — | — | 716 | 8.7% |
| Terra Cotta Tile | — | — | 59 | 0.7% |
| Metal | — | — | 49 | 0.6% |
| Shingles - Concrete | 2 | 1.0% | 36 | 0.4% |
| Membrane | — | — | 12 | 0.1% |
| Other Roof Material | — | — | 9 | 0.1% |
| Shingles - Wood | 1 | 0.5% | 7 | 0.1% |
| Shingles - Slate | — | — | 4 | 0.0% |
| Gravel | — | — | 2 | 0.0% |

> **Note:** `data` is 98.5% Shingles - Asphalt — completely degenerate for classification. `data2` has "Unknown Roof Material" (8.7%) which correlates with flat commercial roofs. Not learnable without significantly more data.

---

### `roof_features` (multi-label)

Phase 3 task. Very sparse across both datasets — most buildings have no roof features recorded.

| Feature | `data` (196) | % | `data2` (8,208) | % |
|---|---|---|---|---|
| Eaves - Boxed | 4 | 2.0% | 94 | 1.1% |
| Rafter Tails | 6 | 3.1% | 54 | 0.7% |
| Parapet - Flat | — | — | 48 | 0.6% |
| Parapet - Stepped | — | — | 47 | 0.6% |
| Eaves - Open | 7 | 3.6% | 45 | 0.5% |
| Cornice - Decorative | — | — | 43 | 0.5% |
| Dormer - Gable | — | — | 34 | 0.4% |
| Purlins | 4 | 2.0% | 31 | 0.4% |
| Dormer - Hipped | — | — | 26 | 0.3% |
| Dormer - Wall | 1 | 0.5% | 24 | 0.3% |
| Eaves - None | 1 | 0.5% | 24 | 0.3% |
| Eaves - Flared | — | — | 23 | 0.3% |
| Parapet - Shaped | 1 | 0.5% | 22 | 0.3% |
| Brackets - Decorative | 1 | 0.5% | 21 | 0.3% |
| Bargeboard - Decorative | — | — | 21 | 0.3% |
| Dentils | — | — | 19 | 0.2% |
| Dormer - Shed | 1 | 0.5% | 19 | 0.2% |
| *(15 further rare tags)* | — | — | ~70 | ~0.9% |

> **Note:** Maximum frequency in `data2` is 1.1% (94 buildings) for Eaves - Boxed. Almost no feature exceeds 1%. Not learnable from images alone at current data scale. This task requires at minimum 10× more data.

---

### `wall_features` (multi-label)

Phase 3 task. Best-populated of the Phase 3 tasks. Several features exceed 20% in both datasets.

| Feature | `data` (196) | % | `data2` (8,208) | % |
|---|---|---|---|---|
| Brick - Polychromatic | 84 | 42.9% | 1,754 | 21.4% |
| Foundation - Concrete | 82 | 41.8% | 2,138 | 26.0% |
| Brick - Patterned | 80 | 40.8% | 2,092 | 25.5% |
| Foundation - Not Visible | 47 | 24.0% | 2,668 | 32.5% |
| Belt Course | 45 | 23.0% | 1,810 | 22.1% |
| Half-Timbering | 43 | 21.9% | 686 | 8.4% |
| Gable Vents | 34 | 17.3% | 1,432 | 17.4% |
| Brick - Corbeled | 22 | 11.2% | 1,107 | 13.5% |
| Awnings | 21 | 10.7% | 503 | 6.1% |
| Shutters | 18 | 9.2% | 565 | 6.9% |
| Masonry Bay | 12 | 6.1% | 559 | 6.8% |
| Foundation - Brick | 8 | 4.1% | 538 | 6.6% |
| Shingles in Gable - Decorative | 4 | 2.0% | 697 | 8.5% |
| Shingles in Gable - Plain | 9 | 4.6% | 353 | 4.3% |
| Rowlock Course | 7 | 3.6% | 154 | 1.9% |
| Quoins | 6 | 3.1% | 220 | 2.7% |
| Engaged Columns | — | — | 454 | 5.5% |
| Other Wall Details | 4 | 2.0% | 168 | 2.0% |
| Attached Sign | — | — | 151 | 1.8% |
| Balcony | — | — | 117 | 1.4% |
| Engaged Piers | — | — | 97 | 1.2% |
| Foundation - Stone | — | — | 351 | 4.3% |
| *(9 further rare tags)* | 3 | ~1.5% | ~85 | ~1.0% |

> **Note:** Wall features are the most learnable Phase 3 task. Foundation-Not Visible (32.5%), Foundation-Concrete (26%), Brick-Patterned (25.5%), Belt Course (22.1%) all have reasonable sample sizes in `data2`. However, the raw counts above include all surveyed buildings — actual training set (759 buildings) would have proportionally fewer positive examples.

---

### `additional_cladding` (multi-label)

Phase 3 candidate. Extremely sparse — most buildings have a single primary cladding only.

| Additional Cladding | `data` (196) | % | `data2` (8,208) | % |
|---|---|---|---|---|
| Stucco - Historic | 4 | 2.0% | 28 | 0.3% |
| Shingles - Decorative | — | — | 23 | 0.3% |
| Brick | 1 | 0.5% | 22 | 0.3% |
| Stucco - Modern | 1 | 0.5% | 15 | 0.2% |
| Shingles - Plain | — | — | 13 | 0.2% |
| Concrete - Block | — | — | 13 | 0.2% |
| Stone - Faux | — | — | 10 | 0.1% |
| *(18 further rare tags, all ≤0.1%)* | — | — | — | — |

> **Note:** Additional cladding is present in <5% of buildings. Not viable as a training target.

---

### Alteration Sub-Fields (multi-label)

Phase 3 tasks. Only relevant for `data2` — `data` has essentially no alterations recorded.

#### `alterations_additions`

| Addition Type | `data` (196) | % | `data2` (8,208) | % |
|---|---|---|---|---|
| Addition - Rear | 5 | 2.6% | 2,375 | 28.9% |
| Addition - Right Side | 1 | 0.5% | 312 | 3.8% |
| Addition - Left Side | — | — | 296 | 3.6% |
| Addition Appears Historic | 5 | 2.6% | 262 | 3.2% |
| Addition - Upper Story | — | — | 210 | 2.6% |
| Addition - Front Facade | — | — | 112 | 1.4% |
| Access Ramp Added | 3 | 1.5% | 58 | 0.7% |
| Exterior Staircase Added | — | — | 47 | 0.6% |
| Addition - Other | — | — | 35 | 0.4% |

#### `alterations_entrances`

| Alteration | `data` (196) | % | `data2` (8,208) | % |
|---|---|---|---|---|
| Entrance - Altered | — | — | 2,079 | 25.3% |
| Entrance Alterations Appear Historic | — | — | 449 | 5.5% |
| Entrance - Enclosed | — | — | 416 | 5.1% |
| Entrance - Added | — | — | 296 | 3.6% |
| Doorway - Moved or Added | — | — | 117 | 1.4% |
| Entrance - Removed | — | — | 83 | 1.0% |
| Transom Filled In | — | — | 79 | 1.0% |
| Storefront - Altered | — | — | 61 | 0.7% |
| Doorway - Filled In | — | — | 44 | 0.5% |

#### `alterations_roof`

| Alteration | `data` (196) | % | `data2` (8,208) | % |
|---|---|---|---|---|
| Dormer - Added | — | — | 296 | 3.6% |
| Chimney - Removed | — | — | 199 | 2.4% |
| Chimney - Altered | — | — | 79 | 1.0% |
| Dormer - Altered | — | — | 70 | 0.9% |
| Chimney - Added | — | — | 43 | 0.5% |

#### `alterations_cladding`

| Alteration | `data` (196) | % | `data2` (8,208) | % |
|---|---|---|---|---|
| Cladding - All Replaced | 1 | 0.5% | 1,712 | 20.9% |
| Brick/Stone Painted | 4 | 2.0% | 1,519 | 18.5% |
| Cladding - Some Replaced | — | — | 882 | 10.7% |
| Cladding Alterations Appear Historic | 4 | 2.0% | 353 | 4.3% |

#### `alterations_windows`

| Alteration | `data` (196) | % | `data2` (8,208) | % |
|---|---|---|---|---|
| Windows Replaced - All | 0 | 0.0% | 4,233 | 51.6% |
| Windows Replaced - Some | 6 | 3.1% | 2,368 | 28.8% |
| Window Openings - Altered | — | — | 752 | 9.2% |
| Window Openings - Filled In | — | — | 362 | 4.4% |
| Windows Boarded Up | 2 | 1.0% | 215 | 2.6% |
| Replacement Windows Appear Historic | — | — | 69 | 0.8% |

> **Note:** Alteration sub-fields are the richest Phase 3 signal in `data2`. Windows Replaced - All (51.6%) and Cladding - All Replaced (20.9%) are the strongest signals and highly correlated with the Phase 1 `alteration_level` labels. These tags are only populated for full-survey buildings; the training CSV subset of 759 buildings will have proportionally similar rates.

---

### `integrity_rating`

Phase 3 candidate (equivalent to `alteration_level` from Phase 1 — same scale, different column).

| Rating | `data` (196) | % | `data2` raw (8,208) | % |
|---|---|---|---|---|
| 1 - Completely Altered | — | — | 55 | 0.7% |
| 2 - Major Alterations | — | — | 544 | 6.6% |
| 3 - Moderate Alterations | — | — | 2,296 | 28.0% |
| 4 - Minor Alterations | — | — | 4,101 | 50.0% |
| 5 - Not Altered | 196 | 100.0% | 411 | 5.0% |
| *(not recorded)* | — | — | 801 | 9.8% |

> **Note:** `integrity_rating` and `alteration_level` (Phase 1) are the same 5-point scale. They should be nearly identical for any given building — use `alteration_level` from the CSV, which is already extracted.

---

## Phase 2/3 Summary: Learnability Assessment

| Task | Phase | Best dataset | Max class % | Viable? | Blocker |
|---|---|---|---|---|---|
| `building_category` | 2 | `data2` | Residential 86% | Partial | Not in training CSV; needs extraction |
| `building_plan` | 2 | Either | Rectangular 3% | No | 95% missing |
| `original_use` / `current_use` | 2 | `data2` | SingleDwelling 78% | Partial | 29 classes, severe long tail |
| `landscape_features` | 2 | Both | Walkway-Concrete 74% | Yes (some tags) | Strong signal for a few tags; most tags too rare |
| `roof_materials` | 3 | `data2` | Shingles-Asphalt 77% | No | 99% one class in `data`; not learnable |
| `roof_features` | 3 | `data2` | Eaves-Boxed 1.1% | No | Max 94 positives across 8k buildings |
| `wall_features` | 3 | Both | Foundation-NotVisible 33% | Yes (top 8 tags) | Top 8 tags have reasonable coverage |
| `additional_cladding` | 3 | Either | Stucco-Historic 0.3% | No | <5% of buildings |
| `alterations_additions` | 3 | `data2` | Addition-Rear 29% | Yes | Only populated in `data2`; not in training CSV |
| `alterations_entrances` | 3 | `data2` | Entrance-Altered 25% | Yes | Only populated in `data2`; not in training CSV |
| `alterations_cladding` | 3 | `data2` | Cladding-All-Replaced 21% | Yes | Only populated in `data2`; not in training CSV |
| `alterations_windows` | 3 | `data2` | Windows-Replaced-All 52% | Yes | Only populated in `data2`; not in training CSV |
| `alterations_roof` | 3 | `data2` | Dormer-Added 3.6% | Marginal | Low frequency |
| `integrity_rating` | 3 | `data2` | Minor-Alterations 50% | Redundant | Same as `alteration_level` in Phase 1 |
