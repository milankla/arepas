# Best Validation Accuracy By Field And Phase

Generated June 8, 2026 from saved `outputs/data2/**/training_history.json` files. The capped Phase 3 smoke/trial run `phase3_step5_capped_200` is excluded.

Rows are fields. Columns are phases. Each cell shows the best validation score and the model run that produced it. Epoch numbers are intentionally omitted.

For single-label fields, the score is best validation `acc`. For multi-label fields, the score is strict exact-match accuracy.

| Field | Phase 1 best | Phase 2 best | Phase 3 best |
|---|---:|---:|---:|
| `architectural_style` | - | 74.3% `b5_crop_v3` | 72.3% `phase3_full_v1` |
| `building_form` | - | 67.8% `b5_pair_v2` | 66.3% `phase3_full_v1` |
| `stories` | 76.5% `b5_crop_v1` | 76.9% `b5_crop_v3` | 67.4% `phase3_v2_visual_retention` |
| `roof_type` | 67.2% `b5_crop_v1` | 65.8% `b5_full_v3` | 56.3% `phase3_v2_visual_retention` |
| `primary_cladding` | 78.2% `b5_crop_v1` | 78.2% `b5_crop_v4` | 66.9% `phase3_full_v1` |
| `chimney_present` | 95.2% `b5_full_v1` | 95.7% `b5_full_v3` | 90.2% `phase3_full_v1` |
| `setting` | 77.7% `b5_full_v1` | 77.3% `b5_full_v3` | 66.7% `phase3_v2_visual_retention` |
| `wall_features` | - | - | 5.0% `phase3_v2_visual_retention` |
| `landscape_features` | - | - | 2.6% `phase3_v2_visual_retention` |
| `window` | - | - | 1.5% `phase3_v2_visual_retention` |
| `entrance` | - | - | 12.4% `phase3_full_v1` |
| `associated_buildings` | - | - | 34.1% `phase3_full_v1` |
| `building_category` | - | - | 95.1% `phase3_full_v1` |
| `roof_materials` | - | - | 90.4% `phase3_full_v1` |
| `current_use` | - | - | 32.1% `phase3_full_v1` |
| `original_use` | - | - | 42.2% `phase3_full_v1` |
