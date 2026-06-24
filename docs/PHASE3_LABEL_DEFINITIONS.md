# Phase 3 Label Definitions

This document is the Step 2 contract for Phase 3 training labels. It defines how the nine locked Phase 3 fields should be parsed, grouped, and encoded before the loader/model wiring in Step 3.

The companion machine-readable contract is [config/phase3_label_definitions.json](../config/phase3_label_definitions.json).

## Scope

Locked Phase 3 fields:

- `wall_features`
- `landscape_features`
- `window`
- `entrance`
- `associated_buildings`
- `building_category`
- `current_use`
- `roof_materials`
- `original_use`

Counts are building-level counts from image-bearing `data2` records, deduplicated by `building_id`.

## Global Rules

- Use the image-bearing mapping CSV as the training source: `data2/image_label_mapping_phase1.csv`.
- Count buildings, not images, when deciding whether labels are trainable.
- Preserve Discover Denver schema option names exactly; do not split labels on hyphens.
- For multipart fields, use Basic Survey subfields only for Phase 3 v1.
- Treat `>=100` positive buildings as initially trainable.
- Treat `30-99` positive buildings as probation labels to revisit after the incoming data drop.
- Treat `<30` positive buildings as deferred unless they are grouped into a broader class.
- Use class weighting or positive-label weighting for all Phase 3 tasks.
- Start Phase 3 from the paired-v2 Phase 2 checkpoint, not from a fresh backbone.
- Use differential learning rates rather than frozen old heads; Phase 1/2 runs showed frozen heads drift out of alignment when the shared backbone keeps moving.

## Phase 1/2 Training Lessons For Phase 3

Phase 3 should inherit the paired-v2 lesson rather than treating every new head the same. The best Phase 2 run used EfficientNet-B5 with paired full images plus 456px crops, `task_gated_residual` fusion, `crop_prior`, `lr=5e-5`, `backbone_lr_scale=0.1`, batch size 6, gradient accumulation 4, cosine scheduling, and no frozen heads. It became the best overall checkpoint, mainly because full-image context helped `architectural_style` and `building_form`.

The tradeoff was detail preservation. `stories` and `roof_type` still underperformed the best crop/full baselines, while full-image context remained important for `setting`. Phase 3 routing therefore starts from crop features, adds full-image residuals selectively, and keeps total new-task loss modest so the nine new heads do not dominate the Phase 1/2 heads.

Recommended paired-view priors for Phase 3:

| Field | Initial view route | Gate prior | Residual scale | Rationale |
|---|---|---:|---:|---|
| `stories` | crop bypass / crop-preserved | 0.01 | 0.25 | Phase 2 paired-v2 diluted this geometry signal. |
| `roof_type` | strongly crop-heavy | 0.03 | 0.50 | Crop runs helped roof shape; preserve crop detail before adding context. |
| `primary_cladding` | mixed, crop-preserved | 0.20 | 0.75 | Texture needs crop detail, but tight crops previously hurt scale/context. |
| `setting` | full-heavy | 0.65 | 1.00 | Full-image baseline remained strongest for site/context. |
| `architectural_style`, `building_form` | paired/context moderate | 0.25 | 1.00 | These were the main paired-v2 winners. |
| `wall_features` | crop-heavy paired | 0.08 | 0.60 | Facade atomics depend on small visual details. |
| `window` | crop-heavy paired | 0.08 | 0.60 | Window type/features are local facade details. |
| `entrance` | crop-heavy with some context | 0.12 | 0.75 | Entrance type is local; entrance location benefits from context. |
| `roof_materials` | crop-heavy with some context | 0.12 | 0.75 | Material labels are fragile and should not be fully context-routed. |
| `landscape_features` | full-heavy | 0.60 | 1.00 | Landscape labels often sit outside the tight building crop. |
| `associated_buildings` | full-heavy | 0.60 | 1.00 | Garages, sheds, and carports often require broader scene context. |
| `building_category` | full-heavy | 0.60 | 1.00 | Category depends on massing, storefront/site cues, and context. |
| `current_use` | full-heavy, low loss | 0.60 | 1.00 | Use is indirect and needs site/signage/context cues. |
| `original_use` | full-heavy, lowest loss | 0.60 | 1.00 | Historical use is the least direct image-only target in Phase 3. |

Recommended Phase 3 loss weights:

| Field | Initial loss weight | Reason |
|---|---:|---|
| `wall_features` | 0.050 | Strong visual detail target; keep below Phase 1/2 primary heads. |
| `window` | 0.045 | Many local labels, but noisy/multipart. |
| `entrance` | 0.035 | Visual but mixed detail/location semantics. |
| `landscape_features` | 0.030 | Full-context target with moderate label noise. |
| `associated_buildings` | 0.025 | Context target; object may be absent or partially visible. |
| `building_category` | 0.025 | Imbalanced but broad; focal loss handles class skew. |
| `roof_materials` | 0.025 | Fragile material signal; use per-label positive weights. |
| `current_use` | 0.020 | Indirect image-only target. |
| `original_use` | 0.015 | Most indirect Phase 3 target; treat as exploratory. |

Use `BCEWithLogitsLoss(pos_weight=...)` for multi-label fields and focal CE with capped class weights for grouped single-label fields. Do not use single-label class weights directly for multi-label heads.

## Target Types

| Field | Target type | Loss family | Initial target count |
|---|---|---|---:|
| `wall_features` | multi-label | BCE with per-label `pos_weight` | 21 |
| `landscape_features` | multi-label | BCE with per-label `pos_weight` | 17 |
| `window` | multi-label multipart | BCE with per-label `pos_weight` | 25 |
| `entrance` | multi-label multipart | BCE with per-label `pos_weight` | 14 |
| `associated_buildings` | multi-label multipart | BCE with per-label `pos_weight` | 6 |
| `building_category` | single-label grouped | focal CE with capped class weights | 3 |
| `current_use` | single-label grouped | focal CE with capped class weights | 5 |
| `roof_materials` | multi-label grouped | BCE with per-label `pos_weight` | 6 |
| `original_use` | single-label grouped | focal CE with capped class weights | 5 |

## Field Rules

### `wall_features`

Use semicolon-separated multi-label parsing.

Initial train labels:

`Foundation - Not Visible`, `Foundation - Concrete`, `Brick - Patterned`, `Belt Course`, `Brick - Polychromatic`, `Gable Vents`, `Brick - Corbeled`, `Shingles in Gable - Decorative`, `Half-Timbering`, `Shutters`, `Masonry Bay`, `Foundation - Brick`, `Awnings`, `Engaged Columns`, `Shingles in Gable - Plain`, `Foundation - Stone`, `Quoins`, `Other Wall Details`, `Rowlock Course`, `Attached Sign`, `Balcony`.

Probation label: `Engaged Piers`.

Do not create a synthetic other class for Phase 3 v1. Low-count wall atomics stay out of the loss and remain visible in audits.

### `landscape_features`

Use semicolon-separated multi-label parsing.

Initial train labels:

`Walkway - Concrete`, `Fence - Rear`, `Fence - Left Side`, `Fence - Right Side`, `Driveway - Solid`, `Wall - Retaining`, `Fence - Front`, `Denver Roll`, `Built-In Planters`, `Walkway - Stone`, `Parking Lot`, `Stone Public Sidewalk`, `Fence - Ornamental`, `Driveway - Ribbon`, `Driveway - Unpaved`, `Walkway - Brick`, `Fence - Historic`.

Probation labels: `Wall - Perimeter`, `Walkway - Other Material`.

### `window`

Use schema-aware multipart parsing. Include only Basic Survey subfields:

- `Window Type`
- `Window Features`

Exclude Full-only subfields for Phase 3 v1:

- `Window Location`
- `Window Material`

Initial train labels include the high-count `Window Type:*` and `Window Features:*` schema options listed in [config/phase3_label_definitions.json](../config/phase3_label_definitions.json). The key implementation rule is to match schema options exactly, so labels like `Divided Lights - All` remain intact.

Probation label: `Window Features: Slot Window`.

### `entrance`

Use schema-aware multipart parsing. Include only Basic Survey subfields:

- `Entrance Type`
- `Entrance Location`

Exclude Full-only subfields for Phase 3 v1:

- `Entrance Features`
- `Door Type`

Preserve full entrance schema options. For example, `Porch - Partial Width - Projecting` is one class, not three classes.

Probation labels: `Entrance Location: Corner`, `Entrance Type: Porch - Full Width - Recessed`, `Entrance Type: Porch - Wrap Around - Projecting`.

### `associated_buildings`

Use schema-aware multipart parsing. Include only:

- `Building/Object Type`

Exclude from Phase 3 v1 targets:

- `Building/Object Location`, because it is Full Survey only.
- `Building/Object Notes`, because it is long text and not a stable class label.

Initial train labels:

`Garage - Detached`, `Shed or Storage Building`, `Garage - Attached`, `Carport - Attached`, `Accessory Dwelling Unit (ADU)`, `Other Associated Building or Object`.

Probation labels: `Unknown - Not Visible`, `Carport - Detached`.

### `building_category`

Use single-label grouped classification.

Classes:

- `Residential`
- `Commercial`
- `Other / Agricultural`

Mapping:

- `Residential` -> `Residential`
- `Commercial` -> `Commercial`
- `Other`, `Agricultural` -> `Other / Agricultural`

This is intentionally imbalanced. Use focal loss plus capped balanced class weights and evaluate macro F1, not only accuracy.

### `current_use`

Use single-label grouped classification.

Classes:

- `Domestic - Single Dwelling`
- `Domestic - Multiple Dwelling`
- `Commercial`
- `Civic / Institutional`
- `Other / Mixed / Vacant`

Commercial subtypes collapse into `Commercial`. Education, government, health care, religious, recreation/culture, and social/meeting uses collapse into `Civic / Institutional`. Mixed, vacant, domestic-other, agriculture, defense, industry, transportation, and unknown/other values collapse into `Other / Mixed / Vacant`.

### `roof_materials`

Use semicolon-separated multi-label parsing with a rare-material group.

Classes:

- `Shingles - Asphalt`
- `Unknown Roof Material`
- `Terra Cotta Tile`
- `Metal`
- `Shingles - Concrete`
- `Rare Roof Material`

Rare group members:

- `Membrane`
- `Other Roof Material`
- `Shingles - Wood`
- `Shingles - Slate`
- `Gravel`

This is a deliberately imbalanced target. Use per-label `pos_weight`, and report per-label precision/recall or macro F1 alongside Jaccard.

### `original_use`

Use single-label grouped classification.

Classes:

- `Domestic - Single Dwelling`
- `Domestic - Multiple Dwelling`
- `Commercial`
- `Civic / Institutional`
- `Other / Mixed / Unknown`

Use the same broad grouping family as `current_use`, but keep the final catch-all named `Other / Mixed / Unknown` because `Vacant Building` is not an original-use schema option.

## Step 3 Implementation Notes

- Add schema-aware multipart parsing helpers before activating `window`, `entrance`, or `associated_buildings`.
- Add fixed atomics for multi-label Phase 3 fields so class order is stable across training/evaluation/inference.
- Add pre-encode transforms for grouped single-label fields.
- Add multi-label positive weights; Phase 3 uses per-task `BCEWithLogitsLoss(pos_weight=...)`.
- Add or update `TaskConfig` entries so the loss knows which Phase 3 tasks are multi-label and which use focal loss.
- Use `task_gated_residual` paired fusion with `crop_prior`, differential LR, and no frozen Phase 1/2 heads.
- Run a smoke test before full Phase 3 training to verify label tensor shapes and loss dispatch.

## Test Cases

- Multipart parser preserves hyphenated schema options exactly.
- Basic Survey filtering excludes Full-only subfields for `window`, `entrance`, and `associated_buildings`.
- Label counts are deduplicated by `building_id`.
- Grouped single-label transforms produce only the configured classes.
- Multi-label encoders use the same class order in train, validation, test, evaluation, and inference.
- Rare labels below threshold do not silently appear as untrained model heads.
