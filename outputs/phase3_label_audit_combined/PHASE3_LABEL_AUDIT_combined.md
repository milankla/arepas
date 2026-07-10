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

- `wall_features` (rank 1, score 96.46)
- `landscape_features` (rank 2, score 84.75)
- `window` (rank 3, score 74.75)

### Visual expansion fields

- `entrance` (rank 5, score 73.75)
- `associated_buildings` (rank 8, score 65.75)

### Imbalance expansion fields

- `roof_materials` (rank 4, score 74.75)
- `building_category` (rank 6, score 71.94)
- `current_use` (rank 7, score 67.75)
- `original_use` (rank 11, score 57.75)

Training should start with the full nine-field Phase 3 scope, but report metrics in two tracks: visually direct tasks and imbalanced/use tasks. The incoming larger data drop should be used to raise minority-class counts before deciding whether any imbalance field needs grouping.

## Ranked Fields

| Rank | Field | Score | Coverage | Usable labels >=100 | Group labels 30-99 | Avg labels | Top label share | Recommendation |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | `wall_features` | 96.46 | 68.11% | 24 | 6 | 2.43 | 34.07% | phase3_core |
| 2 | `landscape_features` | 84.75 | 98.10% | 25 | 1 | 3.56 | 72.46% | phase3_core |
| 3 | `window` | 74.75 | 71.72% | 39 | 7 | 6.37 | 71.36% | phase3_core |
| 4 | `roof_materials` | 74.75 | 95.48% | 5 | 3 | 1.03 | 64.94% | phase3_imbalance_expansion |
| 5 | `entrance` | 73.75 | 74.42% | 28 | 13 | 4.59 | 88.31% | phase3_visual_expansion |
| 6 | `building_category` | 71.94 | 72.47% | 2 | 1 | 1.00 | 91.98% | phase3_imbalance_expansion |
| 7 | `current_use` | 67.75 | 100.00% | 8 | 2 | 1.00 | 80.08% | phase3_imbalance_expansion |
| 8 | `associated_buildings` | 65.75 | 42.02% | 11 | 4 | 1.89 | 65.13% | phase3_visual_expansion |
| 9 | `roof_features` | 65.73 | 13.05% | 13 | 19 | 1.77 | 22.67% | phase4_later |
| 10 | `additional_cladding` | 62.09 | 17.81% | 9 | 12 | 1.53 | 35.48% | phase4_later |
| 11 | `original_use` | 57.75 | 100.00% | 6 | 6 | 1.00 | 82.29% | phase3_imbalance_expansion |
| 12 | `building_plan` | 31.49 | 4.34% | 2 | 1 | 1.00 | 61.47% | phase4_later |

## Top Labels By Field

### `wall_features`

Strong facade-detail candidate; likely complementary to cladding, style, and form.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Foundation - Concrete | 4007 | 23.20% |
| Foundation - Not Visible | 3211 | 18.59% |
| Brick - Patterned | 3161 | 18.30% |
| Belt Course | 3066 | 17.75% |
| Brick - Polychromatic | 2282 | 13.21% |
| Gable Vents | 1653 | 9.57% |
| Brick - Corbeled | 1536 | 8.89% |
| Shingles in Gable - Decorative | 1258 | 7.28% |
| Shutters | 998 | 5.78% |
| Masonry Bay | 977 | 5.66% |

### `landscape_features`

Context task; useful for setting, category, and broader site interpretation.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Walkway - Concrete | 12276 | 71.09% |
| Fence - Rear | 10430 | 60.40% |
| Fence - Left Side | 5832 | 33.77% |
| Fence - Right Side | 5794 | 33.55% |
| Driveway - Solid | 5503 | 31.87% |
| Fence - Front | 3807 | 22.05% |
| Wall - Retaining | 3040 | 17.60% |
| Denver Roll | 2226 | 12.89% |
| Walkway - Stone | 1405 | 8.14% |
| Stone Public Sidewalk | 1333 | 7.72% |

### `window`

Promising but visually smaller/noisier than entrance; needs grouping.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Window Type: Double/Single Hung | 8838 | 51.18% |
| Window Type: Fixed | 8251 | 47.78% |
| Window Type: Sliding | 6858 | 39.71% |
| Window Features: None | 6535 | 37.84% |
| Window Features: Rowlock Sill | 4680 | 27.10% |
| Window Features: Paired Windows | 4150 | 24.03% |
| Window Features: Stone Sill | 3819 | 22.11% |
| Window Features: Tripartite Window | 3246 | 18.80% |
| Window Features: Divided Lights | 3084 | 17.86% |
| Window Features: Arch | 2989 | 17.31% |

### `roof_materials`

Often dominated by asphalt/unknown and hard to verify from street-level photos.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Shingles - Asphalt | 10708 | 62.01% |
| Shingles | 3893 | 22.54% |
| Unknown Roof Material | 1692 | 9.80% |
| Asphalt Shingles | 273 | 1.58% |
| Metal | 140 | 0.81% |
| Terra Cotta Tile | 95 | 0.55% |
| Membrane | 75 | 0.43% |
| Shingles - Concrete | 47 | 0.27% |
| Gravel | 14 | 0.08% |
| Other Roof Material | 12 | 0.07% |

### `entrance`

Promising if grouped around broad entrance type and location.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Entrance Location: Front Facade | 11349 | 65.72% |
| Entrance Type: Porch | 8552 | 49.52% |
| Entrance Type: Projecting | 6963 | 40.32% |
| Entrance Type: Partial Width | 5456 | 31.59% |
| Entrance Type: Stoop | 3389 | 19.62% |
| Entrance Type: Full Width | 3101 | 17.96% |
| Entrance Type: No Porch or Stoop | 2426 | 14.05% |
| Entrance Type: Flush Door | 2426 | 14.05% |
| Entrance Type: Low | 2134 | 12.36% |
| Entrance Location: Right Side | 1989 | 11.52% |

### `building_category`

Broad auxiliary classifier; useful if enough non-residential examples exist.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Residential | 11511 | 66.66% |
| Commercial | 932 | 5.40% |
| Other | 70 | 0.41% |
| Agricultural | 1 | 0.01% |

### `current_use`

Broad use categories may be visual; fine-grained use is context-heavy.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Domestic – Single Dwelling | 13829 | 80.08% |
| Domestic – Multiple Dwelling | 1888 | 10.93% |
| Commercial - Business/Professional | 301 | 1.74% |
| Commercial - Warehouse | 276 | 1.60% |
| Commercial - Retail Store | 197 | 1.14% |
| Commercial - Restaurant | 144 | 0.83% |
| Vacant Building | 131 | 0.76% |
| Commercial - Other | 128 | 0.74% |
| Religious Facility | 63 | 0.36% |
| Mixed Use | 62 | 0.36% |

### `associated_buildings`

Context/object task; depends strongly on image angle and full-view coverage.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Building/Object Type: Detached | 4726 | 27.37% |
| Building/Object Type: Garage | 4700 | 27.22% |
| Building/Object Type: Shed or Storage Building | 1266 | 7.33% |
| Building/Object Type: Garage – Attached | 810 | 4.69% |
| Building/Object Type: Carport | 409 | 2.37% |
| Building/Object Location: Behind Primary Building | 300 | 1.74% |
| Building/Object Type: Attached | 293 | 1.70% |
| Building/Object Type: Other Associated Building or Object | 221 | 1.28% |
| Building/Object Type: Unknown | 219 | 1.27% |
| Building/Object Type: Not Visible | 217 | 1.26% |

### `roof_features`

Conceptually useful, but many atomics are expected to be sparse.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Rafter Tails | 511 | 2.96% |
| Boxed Eaves | 250 | 1.45% |
| Skylight | 219 | 1.27% |
| Eaves - Boxed | 212 | 1.23% |
| Cornice - Decorative | 204 | 1.18% |
| Dormer - Hipped | 204 | 1.18% |
| Dormer - Gable | 189 | 1.09% |
| Bargeboard - Decorative | 185 | 1.07% |
| Brackets - Decorative | 183 | 1.06% |
| Purlins | 148 | 0.86% |

### `additional_cladding`

Secondary material task; likely sparse and better deferred unless counts surprise.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Foundation - Concrete | 1091 | 6.32% |
| Gable Vents | 1002 | 5.80% |
| Foundation - Not Visible | 454 | 2.63% |
| Belt Course | 334 | 1.93% |
| Brick - 2 or More Color | 319 | 1.85% |
| Brick - Patterned | 172 | 1.00% |
| Other Wall Details | 115 | 0.67% |
| Shingles in Gable - Decorative | 112 | 0.65% |
| Foundation - Stone | 106 | 0.61% |
| Masonry Bay | 88 | 0.51% |

### `original_use`

Historical field; weak image-only target despite high label coverage.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Domestic – Single Dwelling | 14210 | 82.29% |
| Domestic – Multiple Dwelling | 1668 | 9.66% |
| Commercial - Warehouse | 350 | 2.03% |
| Commercial - Retail Store | 257 | 1.49% |
| Commercial - Other | 180 | 1.04% |
| Commercial - Business/Professional | 142 | 0.82% |
| Industry/Processing | 78 | 0.45% |
| Unknown Original Use | 71 | 0.41% |
| Mixed Use | 53 | 0.31% |
| Religious Facility | 48 | 0.28% |

### `building_plan`

Usually needs aerial or multi-view information; front facade is often insufficient.

| Label | Positive buildings | Coverage |
|---|---:|---:|
| Rectangular Plan | 461 | 2.67% |
| Irregular Plan | 199 | 1.15% |
| L-Shaped Plan | 49 | 0.28% |
| Square Plan | 27 | 0.16% |
| U-Shaped Plan | 5 | 0.03% |
| T-Shaped Plan | 4 | 0.02% |
| Other Plan | 3 | 0.02% |
| H-Shaped Plan | 2 | 0.01% |

## Phase 4 / Later Fields

- `roof_features`: rank 9, score 65.73. Conceptually useful, but many atomics are expected to be sparse.
- `additional_cladding`: rank 10, score 62.09. Secondary material task; likely sparse and better deferred unless counts surprise.
- `building_plan`: rank 12, score 31.49. Usually needs aerial or multi-view information; front facade is often insufficient.
