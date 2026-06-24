# Phase 3 Label Audit

This audit ranks candidate Phase 3 fields using only image-bearing data2 buildings.
Counts are deduplicated by building_id, so multiple photos of one building count once.

## Basic Survey Check

All nine requested Phase 3 fields are included in Basic Survey at the top level. Multipart fields have partial Basic Survey coverage because some subfields are Full Survey only.

| Field | Basic Survey status |
|---|---|
| `wall_features` | Yes: field is Basic + Full Survey. |
| `landscape_features` | Yes: field is Major Alterations + Basic + Full Survey. |
| `window` | Partial: Window, Window Type, and Window Features are Basic + Full; Window Location and Window Material are Full-only. |
| `entrance` | Partial: Entrance, Entrance Type, and Entrance Location are Basic + Full; Entrance Features and Door Type are Full-only. |
| `associated_buildings` | Partial: Associated Building/Object Type and Notes are Basic + Full; Location is Full-only. |
| `building_category` | Yes: field is Major Alterations + Basic + Full Survey. |
| `current_use` | Yes: field is Less than 30 years + Major Alterations + Basic + Full Survey. |
| `roof_materials` | Yes: field is Basic + Full Survey. |
| `original_use` | Yes: field is Less than 30 years + Major Alterations + Basic + Full Survey. |

## Phase 3 Training Plan

### Core fields

- `wall_features` (rank 1, score 97.0)
- `landscape_features` (rank 2, score 79.75)
- `window` (rank 3, score 74.75)

### Visual expansion fields

- `entrance` (rank 4, score 73.75)
- `associated_buildings` (rank 5, score 72.55)

### Imbalance expansion fields

- `building_category` (rank 6, score 71.94)
- `current_use` (rank 7, score 64.31)
- `roof_materials` (rank 8, score 57.56)
- `original_use` (rank 9, score 53.9)

Training should start with the full nine-field Phase 3 scope, but report metrics in two tracks: visually direct tasks and imbalanced/use tasks. The incoming larger data drop should be used to raise minority-class counts before deciding whether any imbalance field needs grouping.

The exact Step 2 parsing, grouping, and encoding rules are defined in [docs/PHASE3_LABEL_DEFINITIONS.md](PHASE3_LABEL_DEFINITIONS.md), with a machine-readable contract in [config/phase3_label_definitions.json](../config/phase3_label_definitions.json).

## Ranked Fields

| Rank | Field | Score | Coverage | Usable labels >=100 | Group labels 30-99 | Avg labels | Top label share | Recommendation |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | `wall_features` | 97.00 | 94.65% | 21 | 1 | 2.77 | 39.40% | phase3_core |
| 2 | `landscape_features` | 79.75 | 98.72% | 17 | 2 | 3.68 | 83.23% | phase3_core |
| 3 | `window` | 74.75 | 99.13% | 34 | 9 | 6.86 | 72.29% | phase3_core |
| 4 | `entrance` | 73.75 | 99.82% | 22 | 9 | 4.63 | 89.58% | phase3_visual_expansion |
| 5 | `associated_buildings` | 72.55 | 65.79% | 9 | 3 | 1.90 | 69.07% | phase3_visual_expansion |
| 6 | `building_category` | 71.94 | 100.00% | 2 | 1 | 1.00 | 94.74% | phase3_imbalance_expansion |
| 7 | `current_use` | 64.31 | 100.00% | 2 | 7 | 1.00 | 81.81% | phase3_imbalance_expansion |
| 8 | `roof_materials` | 57.56 | 99.97% | 2 | 3 | 1.01 | 88.43% | phase3_imbalance_expansion |
| 9 | `original_use` | 53.90 | 100.00% | 3 | 4 | 1.00 | 84.16% | phase3_imbalance_expansion |
| 10 | `roof_features` | 40.34 | 4.68% | 0 | 8 | 2.06 | 28.14% | phase4_later |
| 11 | `building_plan` | 32.72 | 5.13% | 1 | 1 | 1.00 | 60.93% | phase4_later |
| 12 | `additional_cladding` | 24.67 | 2.35% | 0 | 0 | 1.06 | 16.67% | phase4_later |

## Top Labels By Field

### `wall_features`

Strong facade-detail candidate; likely complementary to cladding, style, and form.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Foundation - Not Visible | 2661 | 37.30% |
| Foundation - Concrete | 2132 | 29.88% |
| Brick - Patterned | 2087 | 29.25% |
| Belt Course | 1808 | 25.34% |
| Brick - Polychromatic | 1749 | 24.51% |
| Gable Vents | 1431 | 20.06% |
| Brick - Corbeled | 1106 | 15.50% |
| Shingles in Gable - Decorative | 696 | 9.75% |
| Half-Timbering | 684 | 9.59% |
| Shutters | 565 | 7.92% |

### `landscape_features`

Context task; useful for setting, category, and broader site interpretation.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Walkway - Concrete | 5863 | 82.17% |
| Fence - Rear | 5383 | 75.44% |
| Fence - Left Side | 2365 | 33.15% |
| Fence - Right Side | 2353 | 32.98% |
| Driveway - Solid | 1861 | 26.08% |
| Wall - Retaining | 1731 | 24.26% |
| Fence - Front | 1718 | 24.08% |
| Denver Roll | 1632 | 22.87% |
| Built-In Planters | 853 | 11.96% |
| Walkway - Stone | 494 | 6.92% |

### `window`

Promising but visually smaller/noisier than entrance; needs grouping.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Window Type: Double/Single Hung | 5113 | 71.66% |
| Window Type: Fixed | 5014 | 70.27% |
| Window Type: Sliding | 4004 | 56.12% |
| Window Features: Rowlock Sill | 3506 | 49.14% |
| Window Features: None | 3306 | 46.33% |
| Window Features: Paired Windows | 2689 | 37.69% |
| Window Features: Tripartite Window | 2295 | 32.17% |
| Window Features: Divided Lights | 2255 | 31.60% |
| Window Features: Stone Sill | 2156 | 30.22% |
| Window Features: All | 1832 | 25.68% |

### `entrance`

Promising if grouped around broad entrance type and location.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Entrance Location: Front Facade | 6380 | 89.42% |
| Entrance Type: Porch | 5159 | 72.31% |
| Entrance Type: Projecting | 4218 | 59.12% |
| Entrance Type: Partial Width | 3202 | 44.88% |
| Entrance Type: Stoop | 1965 | 27.54% |
| Entrance Type: Full Width | 1965 | 27.54% |
| Entrance Type: Low | 1226 | 17.18% |
| Entrance Type: Flush Door | 1133 | 15.88% |
| Entrance Type: No Porch or Stoop | 1133 | 15.88% |
| Entrance Location: Right Side | 1099 | 15.40% |

### `associated_buildings`

Context/object task; depends strongly on image angle and full-view coverage.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Building/Object Type: Detached | 3242 | 45.44% |
| Building/Object Type: Garage | 3236 | 45.35% |
| Building/Object Type: Shed or Storage Building | 761 | 10.67% |
| Building/Object Type: Garage – Attached | 552 | 7.74% |
| Building/Object Type: Carport | 219 | 3.07% |
| Building/Object Location: Behind Primary Building | 159 | 2.23% |
| Building/Object Type: Attached | 152 | 2.13% |
| Building/Object Type: Accessory Dwelling Unit (ADU) | 146 | 2.05% |
| Building/Object Type: Other Associated Building or Object | 139 | 1.95% |
| Building/Object Type: Unknown | 92 | 1.29% |

### `building_category`

Broad auxiliary classifier; useful if enough non-residential examples exist.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Residential | 6760 | 94.74% |
| Commercial | 343 | 4.81% |
| Other | 31 | 0.43% |
| Agricultural | 1 | 0.01% |

### `current_use`

Broad use categories may be visual; fine-grained use is context-heavy.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Domestic – Single Dwelling | 5837 | 81.81% |
| Domestic – Multiple Dwelling | 818 | 11.46% |
| Commercial - Retail Store | 98 | 1.37% |
| Commercial - Business/Professional | 67 | 0.94% |
| Commercial - Restaurant | 61 | 0.85% |
| Commercial - Warehouse | 54 | 0.76% |
| Commercial - Other | 36 | 0.50% |
| Vacant Building | 33 | 0.46% |
| Religious Facility | 30 | 0.42% |
| Mixed Use | 14 | 0.20% |

### `roof_materials`

Often dominated by asphalt/unknown and hard to verify from street-level photos.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Shingles - Asphalt | 6308 | 88.41% |
| Unknown Roof Material | 714 | 10.01% |
| Terra Cotta Tile | 59 | 0.83% |
| Metal | 49 | 0.69% |
| Shingles - Concrete | 36 | 0.50% |
| Membrane | 12 | 0.17% |
| Other Roof Material | 9 | 0.13% |
| Shingles - Wood | 7 | 0.10% |
| Shingles - Slate | 4 | 0.06% |
| Gravel | 2 | 0.03% |

### `original_use`

Historical field; weak image-only target despite high label coverage.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Domestic – Single Dwelling | 6005 | 84.16% |
| Domestic – Multiple Dwelling | 696 | 9.75% |
| Commercial - Retail Store | 125 | 1.75% |
| Commercial - Warehouse | 65 | 0.91% |
| Commercial - Other | 62 | 0.87% |
| Unknown Original Use | 37 | 0.52% |
| Commercial - Business/Professional | 30 | 0.42% |
| Religious Facility | 21 | 0.29% |
| Commercial - Restaurant | 18 | 0.25% |
| Mixed Use | 11 | 0.15% |

### `roof_features`

Conceptually useful, but many atomics are expected to be sparse.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Eaves - Boxed | 94 | 1.32% |
| Rafter Tails | 54 | 0.76% |
| Parapet - Flat | 48 | 0.67% |
| Parapet - Stepped | 47 | 0.66% |
| Eaves - Open | 45 | 0.63% |
| Cornice - Decorative | 43 | 0.60% |
| Dormer - Gable | 34 | 0.48% |
| Purlins | 31 | 0.43% |
| Dormer - Hipped | 26 | 0.36% |
| Dormer - Wall | 24 | 0.34% |

### `building_plan`

Usually needs aerial or multi-view information; front facade is often insufficient.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Rectangular Plan | 223 | 3.13% |
| Irregular Plan | 99 | 1.39% |
| L-Shaped Plan | 26 | 0.36% |
| Square Plan | 9 | 0.13% |
| T-Shaped Plan | 3 | 0.04% |
| U-Shaped Plan | 3 | 0.04% |
| Other Plan | 2 | 0.03% |
| H-Shaped Plan | 1 | 0.01% |

### `additional_cladding`

Secondary material task; likely sparse and better deferred unless counts surprise.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Stucco - Historic | 28 | 0.39% |
| Shingles - Decorative | 23 | 0.32% |
| Brick | 22 | 0.31% |
| Stucco - Modern | 15 | 0.21% |
| Shingles - Plain | 13 | 0.18% |
| Concrete - Block | 13 | 0.18% |
| Stone - Faux | 10 | 0.14% |
| Siding - Horizontal, Wood | 7 | 0.10% |
| Other Cladding | 6 | 0.08% |
| Siding - Vertical, Wood | 5 | 0.07% |

## Phase 4 / Later Fields

- `roof_features`: rank 10, score 40.34. Conceptually useful, but many atomics are expected to be sparse.
- `building_plan`: rank 11, score 32.72. Usually needs aerial or multi-view information; front facade is often insufficient.
- `additional_cladding`: rank 12, score 24.67. Secondary material task; likely sparse and better deferred unless counts surprise.
