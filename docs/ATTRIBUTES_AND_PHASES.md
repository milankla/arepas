### Arepas Attribute and Phase Overview

Arepas predicts architectural attributes from building photographs and survey data. The attributes are grouped into phases according to how visually observable they are, how reliable the labels are, and how much context the model needs.

This document is a high-level reference for planning, review, and communication. It describes what each attribute means, where it fits in the roadmap, and how Arepas treats it conceptually.

#### Phase Summary

| Phase | Focus | Status | Treatment |
|---|---|---|---|
| Phase 1 | Direct visual features | Active | Core facade and site-context attributes that can usually be inferred from photos. |
| Phase 2 | Architectural classification | Active | Higher-level identity tasks such as style and form. These depend on patterns learned from Phase 1. |
| Phase 3 | Fine-grained details | Candidate | Detailed features that need stronger labels, more data, or more careful grouping. |
| Phase 4 | Alterations and integrity | Experimental | Difficult judgment tasks that often require expert knowledge or historical comparison. |
| Not modeled | Notes, metadata, evaluation fields | Preserved only | Useful for filtering, research, or review, but not direct computer-vision targets today. |

#### Phase 1: Direct Visual Features

Phase 1 contains the most visually direct attributes. These are the foundation of the system because they describe the building's visible structure, materials, and immediate setting.

| Attribute | What it captures | Current treatment | Notes |
|---|---|---|---|
| Stories | Number of visible storeys. | Active. | Treated as a visual facade task. Rare taller-building values are grouped so the model learns practical height categories rather than sparse one-off labels. |
| Roof type | Main roof geometry, such as hipped, front gable, side gable, flat, or compound. | Active. | The survey allows multiple roof types. Arepas currently simplifies compound roof combinations into a single compound category for more stable learning. |
| Primary cladding | Dominant exterior wall material. | Active. | Similar materials are grouped into broader material families. Brick is very common, so this task needs imbalance-aware treatment. |
| Setting | How the building sits on its lot and relates to the street or neighboring buildings. | Active. | This is a context task. Full images are often more useful than tight crops because sidewalks, corners, setbacks, and adjacent structures matter. |
| Chimney presence | Whether a chimney is visible or documented. | Active as a simple yes/no task. | This is heavily imbalanced because most buildings do not have a documented chimney. Chimney details are not treated as reliable fine-grained targets yet. |

#### Phase 2: Architectural Classification

Phase 2 covers higher-level architectural identity. These attributes are more interpretive than Phase 1 features, but they are central to the project.

| Attribute | What it captures | Current treatment | Notes |
|---|---|---|---|
| Architectural style | The applied architectural style or stylistic family. | Active. | This is one of the primary goals of Arepas. Rare styles are grouped so the model focuses on categories with enough examples to learn. |
| Building form | The building's underlying physical form or massing. | Active. | Closely related to architectural style. Arepas treats this as a companion task rather than an entirely independent concept. |
| Building category | Broad category such as residential, commercial, agricultural, or other. | Candidate. | Available in the survey schema and useful for future work, but not a primary active target yet. It may be useful as a broad context or routing attribute. |

#### Phase 3: Fine-Grained Details

Phase 3 attributes are often visible, but they are harder because they can be small, sparse, partially occluded, or inconsistently labeled. These are best introduced after the core model is stable.

| Attribute | What it captures | Current treatment | Notes |
|---|---|---|---|
| Wall features | Details such as belt courses, patterned brick, gable vents, shutters, masonry bays, and foundation visibility. | Strong Phase 3 candidate. | This is one of the most promising next groups because several wall features occur often enough to learn. |
| Window features | Window type, configuration, and visible details. | Candidate. | Needs careful parsing and grouping. Some window characteristics are visible, but fine material or location details may need closer views. |
| Entrance features | Porch, stoop, storefront, portico, door, and entrance-related details. | Candidate. | Likely learnable for broad entrance types. Fine details should be grouped or deferred. |
| Landscape features | Fences, walkways, driveways, retaining walls, parking lots, and related site features. | Candidate context task. | More about the property setting than the building itself. Full images are preferred. |
| Associated buildings and objects | Garages, sheds, carports, carriage houses, loading docks, and related secondary structures. | Candidate context/detection task. | Requires wider views and may benefit from object detection or multi-view review. |
| Roof materials | Visible roof material, such as asphalt shingles, metal, tile, or unknown. | Deferred. | Often dominated by one common class and can be hard to see clearly from street-level photos. |
| Roof features | Dormers, eaves, brackets, rafter tails, parapets, and other roof details. | Deferred. | Many individual features are rare, so this should wait for more data or broader grouping. |
| Additional cladding | Secondary exterior materials beyond the primary cladding. | Deferred. | Too sparse for a strong standalone target today. Better handled later as part of wall/material detail analysis. |
| Building plan | Footprint or plan shape. | Usually deferred. | A front facade photo rarely shows enough information. This may need aerial imagery or multiple views. |
| Current use | Present-day use of the building. | Candidate only at broad groupings. | Broad residential/commercial/vacant categories may be feasible. Fine-grained use categories often require signage or outside context. |
| Original use | Historical or original use of the building. | Deferred/hybrid. | Often not directly visible from a current photo. Better suited to a combined visual plus historical-data approach. |
| Chimney materials and features | Chimney material and decorative details. | Deferred. | Too few positive examples for reliable fine-grained prediction at present. |

#### Phase 4: Alterations and Integrity

Phase 4 attributes are important but difficult. They ask not just what is visible, but whether what is visible is original, replaced, altered, or historically compatible. That often requires expertise or comparison against a likely original condition.

| Attribute | What it captures | Current treatment | Notes |
|---|---|---|---|
| Alteration level | Overall degree of alteration, from not altered to completely altered. | Deferred. | Useful, but visually ambiguous. Should be revisited with broader classes or expert-reviewed examples. |
| Additions | Added wings, upper stories, rear additions, ramps, or other physical additions. | Candidate Phase 4 task. | Some additions are visible, but rear or side additions may be missed from a single front image. |
| Entrance alterations | Altered, enclosed, moved, removed, or added entrances. | Candidate Phase 4 task. | Potentially useful for storefronts, porches, and enclosed entries. Needs expert validation. |
| Roof alterations | Added or altered dormers, chimneys, and roof changes. | Deferred. | Many categories are sparse and may overlap with normal roof-feature variation. |
| Cladding alterations | Replaced siding, painted masonry, or other cladding changes. | Candidate Phase 4 task. | Some signals are visible, but distinguishing alteration from original material can be difficult. |
| Window alterations | Replaced, boarded, filled, or altered windows. | Candidate Phase 4 task. | High-value target, but originality is hard to judge from imagery alone without architectural context. |

#### Not Modeled as Visual Targets

Some fields are useful to keep, analyze, or review, but they are not direct prediction targets for the current image model.

| Field group | Treatment |
|---|---|
| General architectural notes | Preserved for review or possible future text analysis. |
| Historical notes and background | Useful context, but not visual labels. |
| Eligibility and evaluation fields | Expert judgment fields, not direct image-classification targets. |
| Survey level | Used to understand what information should be available for a record. Not a target. |
| Neighborhood and dataset metadata | Useful for analysis, splits, and bias checks. Not a model output. |

#### How Arepas Treats Attributes

##### Stable Active Attributes

Attributes in Phases 1 and 2 are the current production focus. They are trained because they have enough visual signal and enough label coverage to support meaningful evaluation.

##### Grouped Attributes

Some survey categories are too detailed or too sparse in their raw form. Arepas groups them into broader classes when that improves learnability and reliability. Examples include high-storey categories, rare architectural styles, cladding variants, and compound roof combinations.

##### Multi-Label Attributes

Some attributes naturally allow more than one answer. Setting is the clearest active example. Future multi-label groups, such as wall features or alteration subfields, should only include labels with enough examples to evaluate fairly.

##### Context-Sensitive Attributes

Not every task benefits from the same crop. Facade crops help with stories, cladding, and roof geometry. Full images help with setting, landscape features, associated buildings, and broader use or category clues. Paired full-image plus crop inputs are the preferred direction when a task needs both detail and context.

##### Expert-Judgment Attributes

Alteration and integrity fields require caution. They may be documented in the survey, but the model may not be able to infer them reliably from a single present-day exterior photo. These should be treated as research tasks unless supported by expert validation, historical comparison, or coarser labels.

#### Basic Survey Coverage

Most records are Basic Survey records, and Basic Survey captures much of what Arepas needs for the active phases.

| Attribute group | Basic Survey coverage | Implication |
|---|---|---|
| Phase 1 visual attributes | Mostly covered | Stories, roof type, primary cladding, and setting are available. |
| Chimney details | Not fully covered | Chimney is more limited and should be treated carefully. |
| Phase 2 classification | Covered | Architectural style, building form, and building category are available. |
| Phase 3 candidates | Partly covered | Several detail fields are present, but they need grouping and quality checks. |
| Alterations | Covered | Labels exist, but visual learnability remains difficult. |

#### Recommended Roadmap

1. Continue improving Phase 1 and Phase 2 with better image views, especially paired full-image plus crop training.
2. Treat building category as the next broad classification candidate after class balance is reviewed.
3. Promote wall features as the strongest Phase 3 detail candidate.
4. Treat landscape features as a context task that should use full-image information.
5. Defer sparse detail tasks such as roof features, roof materials, additional cladding, and chimney subdetails until more data or broader grouping is available.
6. Revisit alteration tasks only with coarser labels, expert review, or historical/contextual support.
