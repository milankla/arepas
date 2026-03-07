"""
Shared field-parsing utilities for Discover Denver CSV data.

These functions are the single source of truth for interpreting raw CSV field
values.  They are used by:
  - DatasetValidator  (src/loader/dataset_validator.py)
  - ArchitecturalDataset  (src/loader/architectural_dataset.py, upcoming)
  - Any future consumer that needs to split or compare field values

Keeping the logic here avoids duplicating the separator-priority rules and
whole-value-first matching that are critical for correctness.
"""

from typing import Any, List, Optional, Set, Tuple

import pandas as pd


# ---------------------------------------------------------------------------
# Empty / normalisation helpers
# ---------------------------------------------------------------------------

def is_empty_value(value: Any) -> bool:
    """Return True if *value* is absent or blank (None, NaN, empty string)."""
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def normalize_value(value: Any) -> str:
    """Return *value* as a stripped string, or '' if it is empty."""
    if is_empty_value(value):
        return ""
    return str(value).strip()


# ---------------------------------------------------------------------------
# Multi-value parsing
# ---------------------------------------------------------------------------

def parse_multi_value(value: str) -> List[str]:
    """Split a raw CSV multi-value string into individual option tokens.

    Separator priority (highest to lowest):

    1. ``;;``  — used when an option's own text ends with ``';'``.
       Multiple selections are stored as ``"opt1;; opt2;"`` and the trailing
       ``';'`` is part of each option's text (e.g. Local Criteria, NR Criteria
       options A / B / D).

    2. ``;``   — plain semicolon separator used by other multi-select fields
       (e.g. Landscape Features, Wall Features, NR Criteria option C with
       another selection).  Must be checked *before* ``','`` because several
       option texts contain commas as punctuation.

    3. ``,``   — comma separator, fallback only when no semicolons are present.

    Args:
        value: Raw string value read from CSV.

    Returns:
        List of stripped, non-empty token strings.
    """
    if is_empty_value(value):
        return []

    if ";;" in value:
        tokens = [v.strip() for v in value.split(";;")]
    elif ";" in value:
        tokens = [v.strip() for v in value.split(";")]
    elif "," in value:
        tokens = [v.strip() for v in value.split(",")]
    else:
        tokens = [value.strip()]

    return [t for t in tokens if t]  # drop empty strings


# ---------------------------------------------------------------------------
# Option validation
# ---------------------------------------------------------------------------

def validate_value_against_options(
    value: Any,
    valid_options: Set[str],
    field_type: str,
) -> Tuple[bool, Optional[List[Any]]]:
    """Check whether *value* is (or consists entirely of) valid option tokens.

    For ``'multi'`` fields the check proceeds as follows:

    1. **Whole-value match first** — if the full raw string is itself a valid
       option, return valid immediately.  This correctly handles single
       selections whose option text contains commas or semicolons
       (e.g. ``"Siding - Vertical, Wood"``, NR Criteria option C).

    2. If the whole value is *not* a direct match, split with
       :func:`parse_multi_value` and validate each token.

    3. For each token, also try ``token + ';'`` as a fallback.  When multiple
       ``;;``-separated selections are split, intermediate tokens lose the
       trailing ``';'`` that is part of their option text (e.g. all Local
       Criteria options end with ``';'``).  The last token retains its
       trailing ``';'`` naturally; only intermediate ones need restoration.

    For non-``'multi'`` fields an exact string match against *valid_options*
    is performed.

    Args:
        value:         Raw field value (any type; converted to ``str``).
        valid_options: Set of accepted option name strings from the schema.
        field_type:    Schema field type string (``'multi'``, ``'select'``, …).

    Returns:
        ``(is_valid, invalid_tokens_or_None)``
        *invalid_tokens* is a list of the failing token strings, or ``None``
        when validation passes.
    """
    if field_type == "multi":
        raw = str(value)

        # Step 1 — whole-value shortcut
        if raw in valid_options or (raw + ";") in valid_options:
            return (True, None)

        # Step 2/3 — split and validate each token
        invalid: List[Any] = []
        for token in parse_multi_value(raw):
            if token not in valid_options and (token + ";") not in valid_options:
                invalid.append(token)

        return (len(invalid) == 0, invalid if invalid else None)

    else:
        return (str(value) in valid_options, None)
