# data3 Drop — Data Review & Cross-Check

**Date:** June 25, 2026 (updated June 26, 2026)
**Scope:** 9 neighborhoods, 9 Excel definition files + ~44k photos in `data3/`.
**Goal:** verify the definition files comply with our internal schema and match
the photos, ahead of integrating data3 into training (data + data2 + data3).

> **June 26 update — both open questions resolved by the data owner.**
> 1. **`DDS.` is not a third ID space.** It was a *transitional* prefix that
>    lives in the `smithsonianNumber` column for records that had no `5DV`
>    number. Every record now also carries a `DIS` number in the `id` column —
>    **use `id` (DIS) as the primary key everywhere.** Confirmed in
>    `Whittier-Final-All.xlsx`: all 1,599 rows have a `DIS` `id`, with
>    `smithsonianNumber` = `DDS` (1,363) or `5DV` (236). The `DDS`-named Whittier
>    photos therefore join via `smithsonianNumber` — **no gap.**
> 2. **Format A is replaced by a schema-mapped export.** The owner sent
>    `TEST_HIST_DISCOVERDENVERSRVYS_P.xls` — the ArcGIS/City schema (8,699 rows,
>    filter by `REGIONNAME`) covering all four Format-A neighborhoods
>    (VV 3,543 · Elyria Swansea 1,536 · CPW 861 · Jefferson Park 555 = 6,495
>    rows). It is *much* cleaner than the raw "All Data Query" dump but **not**
>    identical to Final-All, so it needs a thin normalization step (below), not a
>    full vocabulary translation.
>
> Net effect: **all 9 neighborhoods now have schema-aligned definitions** and a
> working photo join. See the Integration Plan at the end.

## Headline

- **5 of 9 neighborhoods are ready** ("Final-All" format) — same layout as our
  existing `data2` CLEAN.txt, **100% schema-compliant** on every label field
  checked, and **~100% of photos match a definition**.
- **4 of 9 neighborhoods** are now covered by the **ArcGIS/City schema export**
  (`TEST_HIST_…xls`) instead of the raw "All Data Query" dump. Labels are
  schema-named and largely clean; a thin normalization layer is still needed.
- **Building-ID schemes resolved:** use `id` (`DIS.`) as the primary key; keep
  `smithsonianNumber` (`5DV.`/`DDS.`) only for photo matching. `DDS.` is a
  retired transitional prefix, not a separate registry.
- **One systematic data-quality issue:** every "Final-All" `id` is wrapped in
  smart quotes (`“DIS.17785"`) and must be cleaned.

## The two file formats

| Format | Neighborhoods | Columns | Vocabulary | Status |
|---|---|---|---|---|
| **B — "Final-All"** | Five Points, Skyland, Valverde, Villa Park, Whittier | 77–78 | **Internal schema** (Building Category, Roof Type, Wall Features, …) | ✅ Ready |
| **A — "All Data Query"** | City Park West, Elyria Swansea, Jefferson Park, Virginia Village | ~118 | **Raw survey DB** (ArchitecturalStyle, BuildingType, PrimaryRoofMaterial, Window1Desc…) | ⚠️ Needs mapping |

Format B matches our `data2/*/CLEAN.txt` layout exactly (`id` = DIS, then
`smithsonianNumber`, then schema-named label columns). Format A is the upstream
database dump that Format B is *derived from* — column names and the option
vocabulary differ from our schema.

## Schema compliance (Format B)

Every checked single-label field validated **0 out-of-schema values** against
`schema/Discover Denver Schema.txt`:

| Field | Five Points | Skyland | Valverde | Villa Park | Whittier |
|---|---|---|---|---|---|
| Architectural Style | 930 | 1182 | 1118 | 1927 | 1504 |
| Building Form | 930 | 1182 | 1118 | 1927 | 1504 |
| Roof Type | 887 | 1167 | 1090 | 1883 | 1464 |
| Stories | 1343 | 1258 | 1162 | 2010 | 1585 |
| Building Category | 930 | 1182 | 1118 | 1927 | 1504 |
| Original / Current Use | 1343 | 1258 | 1162 | 2010 | 1585 |
| Primary Cladding | 930 | 1182 | 1118 | 1927 | 1504 |
| **Out-of-schema values** | **0** | **0** | **0** | **0** | **0** |

(Numbers are filled-cell counts per field; blanks are expected for vacant lots /
under-30-year buildings, which are intentionally unlabeled.)

Format A was **not** schema-validated because its columns are not schema fields —
that is precisely the work the mapping step must do.

## Photo ↔ definition match

Matching photos to definitions by building ID (any of the three schemes):

| Neighborhood | Format | Rows | Photos | Photo-buildings | Matched to a def | Orphan photo-buildings |
|---|---|---|---|---|---|---|
| City Park West | A | 862 | 2,905 | 810 | 809 | 1 |
| Elyria Swansea | A | 1,536 | 4,545 | 1,439 | 1,439 | 0 |
| Jefferson Park | A | 532 | 1,787 | 506 | 483 | 23 |
| Virginia Village | A | 3,545 | 10,614 | 3,185 | 3,185 | 0 |
| Five Points | B | 1,543 | 3,937 | 1,316 | 1,316 | 0 |
| Skyland | B | 1,265 | 4,374 | 1,256 | 1,256 | 0 |
| Valverde | B | 1,227 | 3,983 | 1,152 | 1,152 | 0 |
| Villa Park | B | 2,055 | 6,504 | 2,008 | 2,008 | 0 |
| Whittier | B | 1,599 | 5,293 | 1,592 | 1,591 | 1 |
| **Total** | | **13,164** | **~44k** | **~13.3k** | **~13.2k** | **~48** |

Orphan photos (a photo building with no matching definition row) are negligible
(~48 across the whole drop, mostly Jefferson Park). Not every definition row has
photos — that gap is expected (vacant lots, un-photographed parcels) and those
rows simply won't produce training images.

### Building-ID schemes found in photos
- **`5DV.`** (Smithsonian) — City Park West, Elyria Swansea, Jefferson Park,
  Virginia Village, Skyland, part of Whittier.
- **`DIS.`** — Five Points, Valverde, Villa Park, part of Skyland/Whittier.
- **`DDS.`** — most of Whittier (4,277 photos).

Our `ImageIndex` keys on the leading ID token, so it can match all three as long
as the definition's `id` **or** `smithsonianNumber` carries the matching value —
which the cross-check confirms it does.

## Issues to resolve before integration

1. **Format A → use the ArcGIS export** (`TEST_HIST_…xls`) for the 4
   neighborhoods. *Resolved source-wise;* still needs a thin normalization
   (column rename + value canonicalization — see plan). The one genuinely lossy
   item is roof type: the export keeps generic `Gable` (not `Front`/`Cross`
   Gable). We either accept the coarser label or raise it with the City.
2. **Smart-quoted IDs (all Format B).** Strip `“ ” "` from `id` before use
   (the loader already strips quotes — confirm it covers smart quotes).
3. **`DIS.\d+` assertion.** `build_phase1_label_mapping.py` hard-asserts
   `building_id` matches `DIS.\d+`. The 4 ArcGIS neighborhoods carry `5DV` ids
   (mostly), so the assertion must be **parameterized** to accept `DIS|5DV|DDS`.
4. **Excel, not TSV.** `data3` ships `.xlsx`/`.xls`; the pipeline consumes
   `… - CLEAN.txt` (TSV). Each file needs an export step.
5. **ID column anomaly (minor).** ~156 ArcGIS rows carry a `DISVCT…` value in
   the ID column — inspect and normalize during conversion.

## Bottom line

The 5 "Final-All" neighborhoods (~7,689 buildings) are clean, schema-compliant,
and photo-matched — they can be integrated with a thin conversion step. The 4
"All Data Query" neighborhoods (~6,475 buildings) have good photos but need a
vocabulary-mapping step (or re-export in Final-All format) before their labels
can be trusted. A concrete integration plan follows separately.

## Phase 3 Label Audit — combined data (July 9, 2026)

Run of `scripts/phase3_label_audit.py` against
`outputs/combined/image_label_mapping_phase1.csv` (**17,269 buildings**, deduped
by `building_id`), now that data + data2 + data3 are integrated. Full output:
`outputs/phase3_label_audit_combined/`. This supersedes the 759-building data2
audit that drove the original forward plan — the volume constraint is resolved.

### Field ranking & frequencies

Atomic bins = number of atomic labels with ≥300 / 100–299 / <30 positive
buildings.

| Rank | Field | Coverage | Buildings | Atomics | ≥300 | 100–299 | <30 | Recommendation |
|---|---|---|---|---|---|---|---|---|
| 1 | `wall_features` | 68.1% | 11,762 | 49 | 18 | 6 | 19 | **phase3_core** |
| 2 | `landscape_features` | 98.1% | 16,941 | 60 | 20 | 5 | 34 | **phase3_core** |
| 3 | `window` | 71.7% | 12,385 | 56 | 31 | 8 | 10 | **phase3_core** |
| 4 | `roof_materials` | 95.5% | 16,488 | 14 | 3 | 2 | 6 | imbalance_expansion |
| 5 | `entrance` | 74.4% | 12,852 | 142 | 20 | 8 | 101 | visual_expansion |
| 6 | `building_category` | 72.5% | 12,514 | 4 | 2 | 0 | 1 | imbalance_expansion |
| 7 | `current_use` | 100% | 17,269 | 42 | 3 | 5 | 32 | imbalance_expansion |
| 8 | `associated_buildings` | 42.0% | 7,256 | 24 | 6 | 5 | 9 | visual_expansion |
| 9 | `roof_features` | 13.1% | 2,254 | 71 | 1 | 12 | 39 | phase4_later |
| 10 | `additional_cladding` | 17.8% | 3,075 | 59 | 5 | 4 | 38 | phase4_later |
| 11 | `original_use` | 100% | 17,269 | 37 | 3 | 3 | 25 | imbalance_expansion |
| 12 | `building_plan` | 4.3% | 750 | 8 | 1 | 1 | 5 | phase4_later |

### Top atomics per training-scope field (positive buildings / % of 17,269)

**`wall_features`** — Foundation-Concrete 4,007 (23.2%) · Foundation-Not Visible
3,211 (18.6%) · Brick-Patterned 3,161 (18.3%) · Belt Course 3,066 (17.8%) ·
Brick-Polychromatic 2,282 (13.2%) · Gable Vents 1,653 (9.6%).

**`landscape_features`** — Walkway-Concrete 12,276 (71.1%) · Fence-Rear 10,430
(60.4%) · Fence-Left 5,832 (33.8%) · Fence-Right 5,794 (33.5%) · Driveway-Solid
5,503 (31.9%) · Fence-Front 3,807 (22.1%).

**`window`** — Double/Single Hung 8,838 (51.2%) · Fixed 8,251 (47.8%) · Sliding
6,858 (39.7%) · Features:None 6,535 (37.8%) · Rowlock Sill 4,680 (27.1%) · Paired
4,150 (24.0%).

**`entrance`** — Location:Front Facade 11,349 (65.7%) · Type:Porch 8,552 (49.5%)
· Projecting 6,963 (40.3%) · Partial Width 5,456 (31.6%) · Stoop 3,389 (19.6%) ·
Full Width 3,101 (18.0%). *(142 atomics, but 101 are <30 support — the
`PHASE3_MIN_POSITIVE_COUNT=100` gate prunes these from the loss.)*

**`roof_materials`** — Shingles-Asphalt 10,708 (62.0%) · Shingles 3,893 (22.5%) ·
Unknown 1,692 (9.8%); everything else <300 (Metal 140, Terra Cotta 95, …) — a
natural Asphalt / Shingles / Other coarsening.

**`building_category`** — Residential 11,511 (66.7%) · Commercial 932 (5.4%) ·
Other 70 · Agricultural 1. Majority-class dominated (kept as a cheap auxiliary).

### Findings → training scope

- **Volume constraint resolved:** every core field now has thousands of
  labelled buildings (vs. 759 before). The old "data wall" no longer applies;
  most fields have 18–31 atomics with ≥300 support.
- **Precision, not recall, is still the lever** — hence the `pos_weight` clamp
  drop 10 → 3.5 planned for the run.
- **`PHASE3_MIN_POSITIVE_COUNT=100`** cleanly removes the long sparse tails
  (`entrance` 101 sparse, `landscape_features` 34, `wall_features` 19) from the
  loss without hand-maintained drop-lists.
- **Correction to the earlier plan:** `roof_features` is only **13.1% coverage**
  (2,254 buildings, 1 strong atomic) → `phase4_later`, **dropped** from the
  train scope (my initial scope had wrongly kept it).
- **Recommended Phase 3 train set (6 fields):** `wall_features`,
  `landscape_features`, `window`, `entrance`, `roof_materials`,
  `building_category`.
- **Dropped:** `roof_features`, `associated_buildings` (42% cov, angle-dependent),
  `current_use`, `original_use` (history/function, not appearance),
  `additional_cladding`, `building_plan`, `chimney_*` (all low-coverage or
  non-visual).

## Appendix A — Format A vs Format B in detail

The two formats are two *views of the same survey database* at different stages
of processing. Format A is the **raw export**; Format B is the **curated,
schema-conformed deliverable** derived from it. They differ in four ways:
structure, column naming, vocabulary, and granularity.

### Structure and column naming

| | **Format B — "Final-All"** | **Format A — "All Data Query"** |
|---|---|---|
| Files | `<Neighborhood>-Final-All.xlsx` (5) | `All Data Query_<Neighborhood>.xlsx` (4) |
| Sheet name | `<Neighborhood>_Final-All` | `CURRENT___Export_for_OAHP` |
| Column count | **77** | **118** |
| Column style | Human-readable **Title Case with spaces** (`Architectural Style`, `Roof Type`, `Primary Cladding`) — i.e. **our internal schema field names** | Raw DB **CamelCase** (`ArchitecturalStyle`, `RoofType`, `CladdingPrimary`) with table-prefixed keys |
| Section prefixes | none | columns are grouped by source table: `SURVEY_DATA_*`, `SURVEY_NOTES_*`, `SURVEY_PROPERTY_*`, `PROPERTY_GEOGRAPHY_*`, `PROPERTY_HISTORY_*`, `PROPERTY_EVALUATION_*` |
| Join keys present | `id` (DIS), `smithsonianNumber` (5DV) | `ResourceNumber` (5DV), `SURVEY_DATA_PIN` (numeric parcel ID); **no DIS id** |
| QC / workflow flags | none | `Under30Years`, `CompletelyAltered`, `SurveyComplete`, `DATA_QC`, `ENHANCED_FORM`, `NPI_QC`, `ENHANCED_FORM_DONE` |

Format B's columns map **1:1 onto our schema**, which is why it validated with
zero out-of-schema values. Format A carries ~40 extra columns (workflow flags,
per-table PIN/Address echoes, split entrance/window descriptors) that have no
schema home and must be dropped or folded during mapping.

### Vocabulary differences (the real work)

Even where a field exists in both, the **allowed values differ**. Examples drawn
from the actual data (Five Points = B, City Park West = A):

**Architectural Style** — close, but the "no style" sentinel differs:
- B: `No Clear Architectural Style`, `Edwardian`, `Queen Anne`, `Classical Revival`, `Victorian Cottage`, `Modern Movement`, `Italianate`, `Moderne`
- A: `No Style`, `Classical Revival`, `Mission`, `Queen Anne`, `Victorian Cottage`, `Spanish Colonial Revival`, `Dutch Colonial Revival`
- ⇒ `No Style` → `No Clear Architectural Style`; confirm A's extra styles all exist in the schema option list.

**Roof Type** — B uses *specific gable* tokens and an explicit `Compound Roof`
marker; A uses *generic gable*:
- B: `Front Gable`, `Cross Gable`, `Hipped`, `Flat`, `Barrel Roof; Compound Roof; Flat`, `Compound Roof; Cross Gable; Hipped`
- A: `Gable`, `Hipped`, `Flat`, `Gambrel`, `Shed`, `Hipped; Flat`, `Gable; Hipped`
- ⇒ A's bare `Gable` has no direct B equivalent (B forces Front/Cross/Side); this is a **lossy** mapping that may need photo inspection or a default.

**Roof material** — one field in B, split in two in A, with explicit null tokens:
- B: single `Roof Materials` column; blanks where unknown
- A: `PrimaryRoofMaterial` + `DetailedRoofMaterial`; values include `Unknown Roof Material`, `N/A`, `Unknown-Not Visible`, `Other Roof Material`
- ⇒ collapse A's two columns; map its explicit unknown/N-A tokens to **blank**.

**Stories** — same intent, inconsistent formatting in A:
- B: `1`, `1-1/2`, `2`, `2-1/2`, `3`, `5-9`, `10-19` (consistent `-1/2`)
- A: mixes `1-1/2` **and** `1 1/2`, `2-1/2` **and** `2 1/2`, plus `N/A`
- ⇒ normalize whitespace/hyphen variants; map `N/A` → blank.

**Original Use** — A contains **three encodings of the same value** (a dash/space
defect):
- A: `Domestic – Single Dwelling` (en-dash), `Domestic –Single Dwelling` (en-dash, no space), `Domestic - Single Dwelling` (hyphen), plus `N/A`, `Unknown Original Use`
- ⇒ canonicalize dash + spacing to the single B form `Domestic – Single Dwelling`.

**Building Form (B) ≈ BuildingType (A)** — vocabularies largely agree
(`Foursquare`, `Gable Front`, `Ranch`, `Central Block with Projecting Bays`,
`Other`), so this field maps cleanly.

### Granularity differences

Format A keeps **fine-grained, multi-attribute descriptors** that Format B
collapses:

- **Windows:** A has `Window1Desc`, `Window2Desc`, `Window3Desc`, each a
  structured free-text string like
  `Type: Double/Single Hung; Material: Wood; Location: Front Facade; Features: Stone Sill; Features: Transom`.
  B collapses all of this into a single `Window` column.
- **Entrances:** A splits the entrance into ~16 columns
  (`MainEntranceType`, `MainEntranceDoorType`, `MainEntranceRoofAndEnclosure`, …
  plus a full `SecondEntrance*` set and `Storefront*` extras). B has a single
  `Entrance` column.
- **Chimneys / roof eaves:** A has `RoofNumberOfChimneys`,
  `RoofChimneyPlacement`, `RoofChimneyMaterial`, `RoofEaves`; B folds these into
  `Roof Features` / `Chimney`.

⇒ For training (Phase-1 fields) this granularity is mostly **discardable** — we
only need the schema label columns — but it explains the 77→118 column gap and
why a naïve column-rename is not enough.

### Summary of the transform Format A needs

1. Rename ~30 raw columns → schema field names.
2. Collapse split columns (roof material ×2, window ×3, entrance ×16) → single
   schema fields.
3. Translate value vocabularies (style sentinel, generic→specific gable, unknown
   tokens → blank).
4. Canonicalize encoding defects (Original Use dashes, Stories spacing).
5. Drop ~40 workflow/QC/echo columns.
6. Derive a `building_id` from `ResourceNumber` (5DV) since no DIS id exists.

Because step 3 is partly **lossy** (e.g. bare `Gable`), obtaining "Final-All"
re-exports for these four neighborhoods remains the lower-risk option.

## Appendix B — The three building-ID schemes

Denver historic-survey records carry more than one identifier, and `data3`
photos are named with **whichever ID was current when the photo was filed**.
Three prefixes appear:

| Prefix | Name / origin | Where it lives in the definitions | Example photo filename |
|---|---|---|---|
| **`5DV.`** | **Smithsonian trinomial** — the Colorado state site number. `5` = Colorado, `DV` = Denver County, the digits = sequential site number. | Format B `smithsonianNumber`; Format A `ResourceNumber` | `5DV.1011_3280_N_DOWNING_ST.0001.jpg` (underscore) · `5DV.1040-HIGH_ST_N_2143.001.JPG` (dash) |
| **`DIS.`** | **Discover Denver survey ID** — the project's own primary key. | Format B `id` (the smart-quoted column) | `DIS.16911_1000_E_18TH_AVE.0002.jpg` |
| **`DDS.`** | A **second Discover Denver ID series** (observed only in the photo names, predominantly Whittier — 4,277 photos). Appears to be an earlier/parallel DIS series; not present as a column in the definitions we have. | *(not a definition column)* | `DDS.1226_1521_E_23RD_AVE.0001.jpg` |

### Why three, and why it matters

- A single building can legitimately have **both** a `5DV` (state) and a `DIS`
  (project) number — these are different registries, not duplicates.
- **Format A** rows expose only `5DV` (`ResourceNumber`) + a numeric PIN — **no
  `DIS`** — so Format A photos must be joined on `5DV`.
- **Format B** rows expose `DIS` (`id`) + `5DV` (`smithsonianNumber`), so Format
  B photos can join on either.
- **Whittier mixes all three** in its photo folder (`DDS` 4,277, `5DV` 784,
  `DIS` 232). The `DDS` photos have **no matching ID column** in the definition
  file, so they can only be reached if a `DDS→DIS/5DV` crosswalk exists or the
  photos are re-keyed.

### Filename anatomy

```
5DV.1011_3280_N_DOWNING_ST.0001.jpg
└──┬──┘ └────────┬───────┘ └─┬─┘ └┬┘
  ID    address (underscores) seq  ext
```

Two delimiter conventions occur: `<ID>_<ADDRESS>.<seq>.jpg` (underscore) and
`<ID>-<ADDRESS>_<num>.<seq>.JPG` (dash). Our `ImageIndex` already tokenizes on
the leading ID (splitting on `_` and `.`), so it indexes `5DV.1011`, `DIS.16911`
and `DDS.1226` as keys — meaning a join succeeds whenever the definition row
carries the matching prefix in `id` **or** `smithsonianNumber`.

### Integration consequence

- 5 Format-B neighborhoods + the `5DV`/`DIS` photos: **join works today** on
  `id` (DIS), with `smithsonianNumber` (`5DV`/`DDS`) as the photo fallback.
- 4 ArcGIS neighborhoods: **join on `5DV`** (`DISCOVERDENVERID` /
  `SMITHSONIANNUMBER`), which matches their `5DV`-named photos.
- **Whittier `DDS` photos: resolved** — every Whittier record has a `DIS` `id`,
  and `DDS` lives in `smithsonianNumber`, so the `DDS`-named photos attach via
  the `smithsonianNumber` fallback. No crosswalk needed.

---

## Integration Plan — all 9 neighborhoods

**Goal:** produce `data3/image_label_mapping_phase1.csv` in the **exact same
form** as `data2/image_label_mapping_phase1.csv` (one row per building × image,
same 30 columns), and have the next training run consume **data + data2 +
data3**.

### Target end-state

Each neighborhood becomes a `data3/<Neighborhood>/<Neighborhood> - CLEAN.txt`
(TSV) with the columns the loader expects — `id`, `smithsonianNumber`,
`address`, then the Title-Case schema label columns — exactly like
`data2/*/CLEAN.txt`. Then the **existing** `build_phase1_label_mapping.py`
pipeline does the rest (photo join + per-image manifest), so the output CSV is
guaranteed to match the data2 format.

```
data3/<Neighborhood>/<Neighborhood> - CLEAN.txt   ← we generate (9 files)
config/data3.json                                  ← we generate (lists all 9)
        │  python scripts/build_phase1_label_mapping.py --config config/data3.json
        ▼
data3/image_label_mapping_phase1.csv               ← same 30 columns as data2
```

### Step 1 — Format B → CLEAN.txt (5 neighborhoods, easy)

Convert `Five Points`, `Skyland`, `Valverde`, `Villa Park`, `Whittier` xlsx →
TSV. The columns already match the schema; the only transforms are:
- strip smart quotes from `id`,
- keep `id` / `smithsonianNumber` / `address` + the schema label columns.

### Step 2 — ArcGIS export → CLEAN.txt (4 neighborhoods)

From `TEST_HIST_DISCOVERDENVERSRVYS_P.xls`, filter `REGIONNAME` ∈
{`CPW`, `VV`, `ELYRIA SWANSEA`, `JEFFERSON PARK`} and emit one CLEAN.txt per
neighborhood, applying the normalization layer:
- **Rename** `UPPERCASE_UNDERSCORE` columns → Title-Case schema names
  (`ARCHITECTURAL_STYLE` → `Architectural Style`, …).
- **Multi-value delimiter:** convert comma-joined values → `; ` (semicolon),
  matching Final-All / schema convention.
- **Value canonicalization:** `No Style` → `No Clear Architectural Style`;
  `Modern Movements` → `Modern Movement`; `Stucco-Historic` → `Stucco - Historic`;
  collapse stray double-spaces; normalize Stories (`2 1/2` → `2-1/2`).
- **IDs:** `id` = `DISCOVERDENVERID`, `smithsonianNumber` = `SMITHSONIANNUMBER`;
  inspect/clean the ~156 `DISVCT…` ID rows.
- **Roof type:** leave generic `Gable` as-is (flagged; lossy) unless the City
  re-exports.

### Step 3 — config + build

- Add `config/data3.json` listing all 9 neighborhoods (mirrors
  `config/data2.json`).
- **Relax the ID assertion** in `build_phase1_label_mapping.py` from `DIS\.\d+`
  to `(DIS|5DV|DDS)\.\d+` (parameterized) so the ArcGIS neighborhoods pass.
- Run `python scripts/build_phase1_label_mapping.py --config config/data3.json`
  → `data3/image_label_mapping_phase1.csv`.
- Verify row counts + `ImageIndex` join coverage per neighborhood (spot-check
  Whittier `DDS`).

### Step 4 — train on data + data2 + data3

Point the next training run at all three manifests (combine the three
`image_label_mapping_phase1.csv` files, or list all three datasets in the
training config). Confirm the merged class distribution before kicking off a
full run.

### Change budget / sequencing

This touches more than 3 files, so per our workflow rules it will be split into
small, reviewable tasks:
1. Format B converter + `config/data3.json` (5 neighborhoods).
2. ArcGIS normalizer (4 neighborhoods).
3. `build_phase1_label_mapping.py` ID-assertion relax + build + verify.
4. Training-config wiring for data + data2 + data3.

**Open decision:** accept generic `Gable` roof type for the 4 ArcGIS
neighborhoods, or request a `Front`/`Cross`/`Side` Gable re-export from the City.
