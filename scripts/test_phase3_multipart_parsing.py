"""Regression test: Phase 3 multipart parsing (window, entrance).

Verifies two things after the Format-A tolerance rewrite of
``_parse_phase3_multipart_labels``:

1. **Format-B parsing is unchanged** — schema-qualified "Window Type: X" /
   "Entrance Type: Y" strings still parse to exactly the same labels.
2. **Format-A / bare shapes now parse** — the previously-dropped data3 forms
   ("Type: Fixed; Type: Sliding", bare "Stoop - Low") produce the right labels.

Run: python scripts/test_phase3_multipart_parsing.py
"""
import sys

sys.path.insert(0, ".")

from src.loader.architectural_dataset import parse_multilabel_value  # noqa: E402

# (col, raw, expected sorted labels)
CASES = [
    # ---- Format-B (regression: must be unchanged) — real strings carry a
    #      "Window N:" / "Entrance N:" record-index prefix before the subfield. ----
    (
        "window",
        "Window 1: Window Type: Double/Single Hung; Window Location: Front Facade; Window Features: Stone Sill",
        ["Window Features: Stone Sill", "Window Type: Double/Single Hung"],
    ),
    (
        "window",
        "Window 1: Window Type: Fixed  |  Window 2: Window Type: Sliding",
        ["Window Type: Fixed", "Window Type: Sliding"],
    ),
    (
        "entrance",
        "Entrance 1: Entrance Type: Flush Door - No Porch or Stoop; Entrance Location: Front Facade",
        ["Entrance Location: Front Facade", "Entrance Type: Flush Door - No Porch or Stoop"],
    ),
    (
        "entrance",
        "Entrance 1: Entrance Type: Stoop - High; Entrance Location: Front Facade  |  Entrance 2: Entrance Location: Left Side",
        [
            "Entrance Location: Front Facade",
            "Entrance Location: Left Side",
            "Entrance Type: Stoop - High",
        ],
    ),
    # ---- Format-A: short aliases + repeated subfields (previously dropped) ----
    (
        "window",
        "Type:  Fixed; Type:  Sliding; Material:  Vinyl; Location:  Front Facade",
        ["Window Type: Fixed", "Window Type: Sliding"],  # Material/Location ignored
    ),
    (
        "window",
        "Type: Double/Single Hung; Features: Rowlock Sill; Material: Wood",
        ["Window Features: Rowlock Sill", "Window Type: Double/Single Hung"],
    ),
    # ---- Bare entrance values with no "key:" prefix (previously dropped) ----
    ("entrance", "Stoop - Low", ["Entrance Type: Stoop - Low"]),
    (
        "entrance",
        "Porch - Partial Width - Projecting",
        ["Entrance Type: Porch - Partial Width - Projecting"],
    ),
    # ---- Non-schema value stays dropped ----
    ("entrance", "Patio - Projecting", []),
    # ---- Excluded subfield key must not leak into a head ----
    ("window", "Material: Vinyl; Location: Front Facade", []),
]


def main() -> int:
    all_ok = True
    for col, raw, expected in CASES:
        got = parse_multilabel_value(col, raw)
        ok = got == sorted(expected)
        all_ok = all_ok and ok
        status = "OK " if ok else "FAIL"
        print(f"[{status}] {col}: {raw!r}")
        if not ok:
            print(f"        expected: {sorted(expected)}")
            print(f"        got:      {got}")
    print("\nAll passed." if all_ok else "\nFAILURES present.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
