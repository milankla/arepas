# Data Cleanup & Label Normalization

**Scope:** Phase 1 + Phase 2 multi-task training on the combined Denver dataset
(`data/` + `data2/` + `data3/` → `outputs/combined/image_label_mapping_phase1.csv`,
17,269 buildings / 60,841 image rows / 20 datasets).

**Where it happens:** All label cleanup is applied **at load time** inside
[src/loader/architectural_dataset.py](../src/loader/architectural_dataset.py).
The CSV manifests are **never mutated** — every transform is a pure
string→string function registered in `PRE_ENCODE_TRANSFORMS` (single-label) or
`MULTILABEL_ATOM_TRANSFORMS` (multi-label), applied before the `LabelEncoder` /
`MultiLabelBinarizer` is fit. This keeps the raw survey data auditable and makes
the label policy reproducible and reversible.

**Guiding rule:** every trained category should have **≥ 50 buildings**. Classes
below that floor are folded into an "Other"-style bucket or merged into the
nearest meaningful class, because a ~15% test split otherwise leaves too few
examples to learn or evaluate reliably.

> ⚠️ **Known exceptions (left in by owner decision):**
> `architectural_style → Mission` (46 buildings) and
> `building_form → Gas Station` (26 buildings) are below the 50-building floor
> but intentionally **kept** as their own classes.

---

## Summary table

| Field | Phase | Type | Raw → Final | Cleanup theme |
|---|---|---|---|---|
| `roof_type` | 1 | single-label | ~19 multi-bit → **11** | Flatten compound roofs; drop rare types |
| `building_form` | **2** | single-label | 63 → **27** | Merge typos; group Gas Station; fold rare → Other |
| `stories` | 1 | single-label | mixed notation → **5** | Normalize notation; coarsen tall buildings |
| `architectural_style` | **2** | single-label | 37 → **16** | Keep viable classes; rest → Other Style; **mask compounds** |
| `primary_cladding` | 1 | single-label | 18 → **8** | Coarsen material variants into groups |
| `setting` | 1 | multi-label | 12 raw atomics → **6** | Canonicalize surveyor typos/phrasing |
| `chimney_present` | 1 | single-label (gated) | 2 classes | Survey-level masking (false-negative fix) |

> **Phase 2 tasks** are `architectural_style` (§4) and `building_form` (§2),
> trained on top of the warm-started Phase 1 backbone; the rest are Phase 1.

---

## 1. `roof_type` — flatten compound roofs, drop rare types

**High level:** Surveyors could tag multiple roof types per building, turning
this into a noisy 19-bit multi-label problem (~13% Jaccard). We collapse it to a
clean single-label problem: any building with more than one roof type becomes
the single class **`Compound`**, and rare single types fold into **`Other`**.

**Technical:**
- `normalize_roof_type_label()`: if the value contains `"; "` (multi-select) or
  equals `"Compound Roof"` → `"Compound"`.
- `RARE_ROOF_TYPES` (< 50 buildings) → `"Other"`:
  `Shed` (40), `Mansard` (34), `Barrel Roof` (25), `Pyramidal` (21),
  `Gable` (11), `Unknown Roof Type` (6), `Monitor` (2) — ~148 buildings total.
- **Result:** 11 classes (`Compound`, `Cross Gable`, `Cross Hip-on-Gable`,
  `Dutch Hipped`, `Flat`, `Front Gable`, `Gambrel`, `Hip-on-Gable`, `Hipped`,
  `Other`, `Side Gable`). Min class `Dutch Hipped` = 92. Converts a
  multi-label/BCE task into a single-label/CrossEntropy task.

## 2. `building_form` (Phase 2) — merge duplicates, group Gas Station, fold rare → Other

**High level:** The raw field had 63 classes polluted by spelling/casing typos,
several "Gas Station - *" subtypes, and a long tail of rare forms. We merge
duplicates to a canonical spelling, group all gas-station subtypes into one
`Gas Station` family, then fold anything below the 50-building floor into
`Other`.

**Technical:**
- `BUILDING_FORM_CANON`: typo/casing merges, e.g.
  `"Apartment Block"` / `"Apartment-Block"` → `"Apartment - Block"`,
  `"Central Block With Projecting Bays"` / `"...Projecting Bay"` /
  `"Central Block ith Projecting Bay"` → `"Central Block with Projecting Bays"`,
  `"Hipped Roof Box"` → `"Hipped-Roof Box"`, `"Split-Level"` → `"Split Level"`,
  `"Comercial - Other"` → `"Commercial - Other"`.
- Gas-station grouping: `"Gas Station - Oblong Box"`, `"- Other"`,
  `"- House with Canopy"`, `"- Cottage"` → `"Gas Station"`.
- `KEEP_BUILDING_FORMS` (≥ 50 buildings, plus the grouped Gas Station family)
  are kept; everything else → `"Other"`.
- **Result:** 63 → 27 classes. `Gas Station` (26) is intentionally retained
  despite being below the floor (owner decision).

## 3. `stories` — normalize notation, coarsen tall buildings

**High level:** Story counts arrived in inconsistent notation (`2.5` decimal vs
`2-1/2` fraction) and with a long thin tail of tall buildings. We standardize on
the fraction notation and collapse everything genuinely ≥ 3 stories into a single
`3+` bucket.

**Technical (`normalize_stories_label`):**
- `"1/2"` (4 buildings, below floor; a raised-basement/half storey) → `"1"`.
- `"2.5"` (decimal variant from data3) → `"2-1/2"`.
- `"3"`, `"3-1/2"`, `"4"`, `"5-9"`, `"10-19"`, `"20+"` → `"3+"`.
- Note: `"2+"` was previously **renamed** to `"2-1/2"` — it misleadingly implied
  "2 or more" but contained only 2.5-story buildings (plain `"2"` is separate).
- **Result:** 5 classes `['1', '1-1/2', '2', '2-1/2', '3+']`, all ≥ 50
  (min `3+` = 134). `2-1/2` (Foursquares etc.) is a real, common Denver category
  kept separate from the open-ended `3+` tall-building bucket.

## 4. `architectural_style` (Phase 2) — keep viable classes, mask compounds, rest → Other Style

**High level:** 37+ raw styles with a heavy long tail, plus a set of compound
"X; Y" survey entries where the surveyor recorded two styles at once. We keep
single styles with **≥ 50 buildings**, collapse the rest into `Other Style`, and
**mask the compounds out of the style head entirely** (they neither train nor
pollute `Other Style`) since every distinct combo is well below the floor.

**Technical (`normalize_arch_style_label`):**
- Compound values (any string containing `";"`) → the `IGNORE_LABEL` sentinel,
  which is excluded from the `LabelEncoder`'s classes and from `class_weights`,
  and emitted as `IGNORE_INDEX = -100` in `__getitem__`. The building is **not**
  dropped — it still supervises `building_form` and all Phase 1 tasks; only its
  style label is masked (same mechanism as `chimney_present`, see §7).
- `ARCH_STYLE_KEEP` (15 named styles) are retained; every other single value —
  including the pre-existing `"Other Style"` — → `"Other Style"`.
- `Italianate` (142) and `Colonial Revival` (66) were **promoted** into the keep
  list once the combined dataset pushed them past the 50-building floor.
- **Result:** 16 classes (15 kept + `Other Style`). **319 compound buildings**
  across 101 combos are masked. `Mission` (46 buildings) is intentionally
  retained despite being below the floor (owner decision).

## 5. `primary_cladding` — coarsen material variants into groups

**High level:** 18 highly granular cladding labels (e.g. multiple siding and
shingle sub-materials) with most below useful counts. We coarsen them into 8
material groups that are visually distinguishable from a facade photo.

**Technical (`CLADDING_COARSEN_MAP` / `normalize_cladding_label`):**
- `Stucco - Modern` + `Stucco - Historic` → `Stucco`
- `Siding - Horizontal/Vertical/Aluminum/Wood/Unknown` → `Siding - Other`
  (`Siding - Vinyl` kept separate — large enough)
- `Shingles - Asbestos/Plain/Asphalt` → `Shingles`
- `Concrete - Block/Modular-Precast` + `Stone - Faux/Smooth` → `Concrete / Stone`
- `Brick`, `Sheet Metal`, `Other Cladding` kept; any unseen value → `Other Cladding`.
- **Result:** 8 classes (`Brick`, `Concrete / Stone`, `Other Cladding`,
  `Sheet Metal`, `Shingles`, `Siding - Other`, `Siding - Vinyl`, `Stucco`).
  Min `Sheet Metal` = 62.

## 6. `setting` — canonicalize surveyor variants (multi-label)

**High level:** `setting` is a multi-label field (building's relation to adjacent
lots/street) with 6 canonical schema options. Surveyor typos/casing/phrasing
created variant spellings that the `MultiLabelBinarizer` silently dropped,
losing ~12 buildings' worth of tags. We map each variant to its canonical schema
atomic.

**Technical (`SETTING_ATOM_CANON` via `MULTILABEL_ATOM_TRANSFORMS`, applied
per-atomic in `parse_multilabel_value`):**
- `"Set Back From Sidewalk"` (casing) + `"et Back from Sidewalk"` (leading-char
  typo) → `"Set Back from Sidewalk"`
- `"Flush with Sidewalk"` → `"Flush at Sidewalk"`
- `"Attached 1 Side"` → `"Attached on 1 Side"`
- `"Attached 2 Sides"` → `"Attached on 2 Sides"`
- `"Set Back at Alley"` (33) is **intentionally not mapped** — it is not one of
  the 6 schema options and is semantically distinct from `Set at Back of Lot`,
  so it stays dropped rather than guessed.
- **Result:** 6 trained atomics (`Attached on 1 Side`, `Attached on 2 Sides`,
  `Corner`, `Flush at Sidewalk`, `Set at Back of Lot`, `Set Back from Sidewalk`),
  all ≥ 50 (min `Attached on 2 Sides` = 62).

## 7. `chimney_present` — survey-level masking (false-negative fix)

**High level:** The `Chimney` schema field is `surveyLevel: [3]` + `required:
false` — it is collected **only at "Full Survey"**. `chimney_present` was derived
as `"Yes" if Chimney column non-empty else "No"`, so a `"No"` from a Basic Survey
actually means *"not assessed"*, not *"no chimney"*. This poisoned the label with
false negatives (Full Survey: 42.9% Yes vs Basic Survey: 0.3% Yes).

**Technical (per-task masking, not a value rewrite):**
- A `survey_level` column is carried through all manifests
  (`build_phase1_label_mapping.py` emits it; `convert_data3_format_a.py` injects
  `"Full Survey"` for intensive ArcGIS records; `combine_manifests.py` passes it
  through a strict column-equality check).
- In `__getitem__`, for `col in SURVEY_GATED_COLS` (`chimney_present`), when
  `survey_level != "Full Survey"` the label is set to the PyTorch sentinel
  `IGNORE_INDEX = -100`.
- `FocalLoss` and `CrossEntropyLoss` skip `-100` targets; `compute_metrics()`
  excludes them from accuracy/F1; `class_weights` are computed on the
  Full-Survey subset only (chimney weights `[No 0.90, Yes 1.12]`).
- **Result:** chimney is supervised only on the 5,457 Full-Survey buildings
  (No 3,118 / Yes 2,339, ~43% Yes) instead of being washed out by ~11,800
  unassessed "No" labels.

---

## Verification

After the transforms, `make_splits("outputs/combined/image_label_mapping_phase1.csv")`
fits encoders cleanly:

```
architectural_style: 16   building_form: 27   roof_type: 11
primary_cladding: 8       stories: 5          setting: 6 (multi)
chimney_present: 2
Split — train 12,088 buildings / 42,615 images,
        val 2,590 / 9,113, test 2,591 / 9,113
```

All trained categories meet the ≥ 50-building floor except the two
owner-approved exceptions (`Mission` 46, `Gas Station` 26).

---

## Field frequencies (complete combined dataset)

Building-level counts **after** normalization, across all 17,269 buildings in
`outputs/combined/image_label_mapping_phase1.csv`. Single-label percentages are
over labeled buildings; `setting` is multi-label (a building may carry several
atomics, so percentages do not sum to 100%); `chimney_present` is computed over
the 5,457 Full-Survey buildings only (the rest are masked — see §7).

### `architectural_style` — 16 classes (Phase 2; supervised = 16,950 of 17,269; 319 compounds masked)

| Class | Count | % |
|---|---:|---:|
| No Clear Architectural Style | 8,905 | 51.6% |
| Ranch | 2,868 | 16.6% |
| Craftsman | 1,688 | 9.8% |
| Victorian Cottage | 763 | 4.4% |
| Edwardian | 485 | 2.8% |
| Queen Anne | 447 | 2.6% |
| Contemporary | 344 | 2.0% |
| Modern Movement | 264 | 1.5% |
| Other Style | 264 | 1.5% |
| English Norman Cottage | 234 | 1.4% |
| Classical Revival | 179 | 1.0% |
| Mixed Style | 149 | 0.9% |
| Italianate | 142 | 0.8% |
| Dutch Colonial Revival | 106 | 0.6% |
| Colonial Revival | 66 | 0.4% |
| Mission ⚠️ | 46 | 0.3% |

> _319 compound "X; Y" buildings (1.8%) are masked out of the style head (see
> §4) — excluded from the supervised denominator above; they still train on
> `building_form` and all Phase 1 tasks._

### `building_form` — 27 classes (Phase 2; labeled = 17,269)

| Class | Count | % |
|---|---:|---:|
| Minimal Traditional | 2,868 | 16.6% |
| Ranch | 2,720 | 15.8% |
| Bungalow | 2,117 | 12.3% |
| Gable Front | 2,028 | 11.7% |
| Central Block with Projecting Bays | 872 | 5.0% |
| Classic Cottage | 807 | 4.7% |
| Terrace Type | 770 | 4.5% |
| Transitional Ranch | 736 | 4.3% |
| Other | 719 | 4.2% |
| Duplex | 684 | 4.0% |
| Commercial/Industrial Block | 563 | 3.3% |
| Foursquare | 441 | 2.6% |
| Hipped-Roof Box | 270 | 1.6% |
| Apartment - Block | 254 | 1.5% |
| One-Part Commercial Block | 244 | 1.4% |
| Bi-Level | 216 | 1.3% |
| Gabled Ell | 190 | 1.1% |
| Split Level | 159 | 0.9% |
| Service Bay Business | 99 | 0.6% |
| Two-Part Commercial Block | 91 | 0.5% |
| Commercial - Other | 85 | 0.5% |
| Central Passage Double-Pile | 71 | 0.4% |
| Hall and Parlor | 71 | 0.4% |
| Apartment - Garden Court | 62 | 0.4% |
| Shotgun | 54 | 0.3% |
| Apartment - Complex | 52 | 0.3% |
| Gas Station ⚠️ | 26 | 0.2% |

### `roof_type` — 11 classes (labeled = 17,269)

| Class | Count | % |
|---|---:|---:|
| Hipped | 4,633 | 26.8% |
| Front Gable | 2,761 | 16.0% |
| Compound | 2,407 | 13.9% |
| Cross Gable | 2,386 | 13.8% |
| Side Gable | 2,374 | 13.7% |
| Flat | 1,910 | 11.1% |
| Hip-on-Gable | 271 | 1.6% |
| Cross Hip-on-Gable | 178 | 1.0% |
| Other | 148 | 0.9% |
| Gambrel | 109 | 0.6% |
| Dutch Hipped | 92 | 0.5% |

### `primary_cladding` — 8 classes (labeled = 17,269)

| Class | Count | % |
|---|---:|---:|
| Brick | 8,928 | 51.7% |
| Other Cladding | 2,307 | 13.4% |
| Siding - Vinyl | 1,805 | 10.5% |
| Siding - Other | 1,683 | 9.7% |
| Stucco | 1,585 | 9.2% |
| Shingles | 564 | 3.3% |
| Concrete / Stone | 335 | 1.9% |
| Sheet Metal | 62 | 0.4% |

### `stories` — 5 classes (labeled = 17,269)

| Class | Count | % |
|---|---:|---:|
| 1 | 11,963 | 69.3% |
| 1-1/2 | 3,010 | 17.4% |
| 2 | 1,739 | 10.1% |
| 2-1/2 | 423 | 2.4% |
| 3+ | 134 | 0.8% |

### `setting` — multi-label, 6 trained atomics (of 17,269 buildings)

| Atomic | Count | % |
|---|---:|---:|
| Set Back from Sidewalk | 16,272 | 94.2% |
| Corner | 3,186 | 18.4% |
| Flush at Sidewalk | 672 | 3.9% |
| Set at Back of Lot | 271 | 1.6% |
| Attached on 1 Side | 174 | 1.0% |
| Attached on 2 Sides | 62 | 0.4% |
| _Set Back at Alley (not a schema option — dropped)_ | 33 | 0.2% |

### `chimney_present` — 2 classes (Full-Survey only, denom = 5,457)

| Class | Count | % |
|---|---:|---:|
| No | 3,118 | 57.1% |
| Yes | 2,339 | 42.9% |

> ⚠️ = retained despite being below the ≥ 50-building floor (owner decision).
