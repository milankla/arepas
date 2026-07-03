"""
Convert the ArcGIS/City schema export (TEST_HIST_DISCOVERDENVERSRVYS_P.xls) to
the loader's CLEAN.txt (TSV) format for the 4 Format-A neighborhoods, mirroring
the data2/data3 Format-B convention.

This is the "Option 2" stopgap (see docs/DATA3_REVIEW.md): the ArcGIS export is
schema-aligned but (a) lacks an `Alteration Level` column and (b) keeps a few
raw-vocabulary quirks. We therefore:
  1. rename UPPERCASE_UNDERSCORE columns -> internal schema Title-Case names,
  2. normalize categorical values (delimiter -> "; ", canonicalize a handful of
     tokens, blank obvious null tokens, fix Stories spacing),
  3. backfill `Alteration Level` from the raw "All Data Query" files via a lossy
     phrase -> schema 1-5 map, joined on the 5DV number,
  4. backfill the coarse `Roof Type` (the ArcGIS export only carries the parent
     family, e.g. bare `Gable`) with the specific subtype from the raw files'
     `DetailedRoofType` column, joined on the 5DV number. The detailed value is
     *merged* into the coarse one (the gable/hip parent is replaced by its
     subtype while other parts such as Flat/Shed are kept), and hip-direction
     subtypes (Front/Cross/Side Hipped) are collapsed to plain `Hipped` so the
     vocabulary matches data2 / Format-B.

Output (one per neighborhood, co-located with photos like data2/data3):
  data3/<Neighborhood> Photos/<Neighborhood> - CLEAN.txt

Usage:
  python scripts/convert_data3_format_a.py
"""

import csv
import re
from pathlib import Path

import pandas as pd
from loguru import logger

DATA3 = Path("data3")
ARCGIS = "TEST_HIST_DISCOVERDENVERSRVYS_P.xls"
QUOTE_CHARS = "\u201c\u201d\u201e\u201f\"'"
WS_RUN = re.compile(r"[\t\r\n]+")
STORIES_HALF = re.compile(r"(\d)\s+(\d/2)")
# Valid story forms: integer, integer+, X-1/2, X.5, 1/2, or a range X-Y.
STORIES_VALID = re.compile(r"\d+\+?|\d+-1/2|\d+\.5|\d+/2|1/2|\d+-\d+")

# REGIONNAME -> (neighborhood name, photos folder, raw All Data Query file)
REGIONS = {
    "CPW":            ("City Park West",   "City Park West Photos",   "All Data Query_CityParkWest.xlsx"),
    "VV":             ("Virginia Village", "Virginia Village Photos", "All Data Query_VirginiaVillage.xlsx"),
    "ELYRIA SWANSEA": ("Elyria Swansea",   "Elyria Swansea Photos",   "All Data Query_ElyriaSwansea.xlsx"),
    "JEFFERSON PARK": ("Jefferson Park",   "Jefferson Park Photos",   "All Data Query_JeffersonPark.xlsx"),
}

# ArcGIS column -> internal schema Title-Case name
COL_MAP = {
    "DISCOVERDENVERID":         "id",
    "SMITHSONIANNUMBER":        "smithsonianNumber",
    "ADDRESS":                  "address",
    "ARCHITECTURAL_STYLE":      "Architectural Style",
    "BUILDING_FORM":            "Building Form",
    "ROOF_TYPE":                "Roof Type",
    "PRIMARY_CLADDING":         "Primary Cladding",
    "STORIES":                  "Stories",
    "SETTING":                  "Setting",
    "CHIMNEY":                  "Chimney",
    "WINDOW":                   "Window",
    "ENTRANCE":                 "Entrance",
    "ROOFFEATURES":             "Roof Features",
    "ROOF_MATERIALS":           "Roof Materials",
    "ADDITIONALCLADDING":       "Additional Cladding",
    "WALL_FEATURES":            "Wall Features",
    "LANDSCAPE_FEATURES":       "Landscape Features",
    "ASSOCIATEDBUILDINGOBJECTS": "Associated Building and Objects",
    "BUILDINGPLAN":             "Building Plan",
    "ORIGINAL_USE":             "Original Use",
    "CURRENT_USE":              "Current Use",
    "ALTERATIONS_ADDITIONS":    "Alterations-Additions",
    "ALTERATIONS_ENTRANCES":    "Alterations-Entrances",
    "ALTERATIONS_ROOF":         "Alterations-Roof",
    "ALTERATIONS_CLADDING":     "Alterations-Cladding",
    "ALTERATIONS_WINDOWS":      "Alterations-Windows",
}

# Free-text fields: sanitize only (no delimiter/token normalization).
FREE_TEXT = {"address", "Window", "Entrance", "Associated Building and Objects"}

# Categorical label fields get delimiter + token canonicalization.
CATEGORICAL = [v for v in COL_MAP.values()
               if v not in FREE_TEXT and v not in ("id", "smithsonianNumber")]

# Per-part value canonicalization (raw token -> schema token).
TOKEN_FIXES = {
    "No Style": "No Clear Architectural Style",
    "Modern Movements": "Modern Movement",
    "Stucco-Historic": "Stucco - Historic",
}

# Null-ish tokens dropped from categorical fields (lowercased).
NULL_TOKENS = {
    "", "n/a", "na", "none", "none visible", "unknown",
    "unknown - not visible", "unknown-not visible",
    "unknown roof material", "other roof material", "indeterminate",
}

# Alteration phrase (lowercased) -> schema severity level (1 = most altered).
ALT_LEVEL = {
    "completely altered": 1,
    "major alterations": 2, "major alterations present": 2,
    "moderate alterations": 3, "moderate alterations present": 3,
    "minor alterations": 4, "minor alterations present": 4,
    "minor alteration present": 4,
    "not altered": 5,
}
ALT_NAME = {1: "Completely Altered", 2: "Major Alterations",
            3: "Moderate Alterations", 4: "Minor Alterations", 5: "Not Altered"}

# Raw DetailedRoofType / coarse RoofType token (lowercased) -> canonical roof
# token aligned to the data2 / Format-B vocabulary. Hip-direction subtypes
# (Front/Cross/Side Hipped) collapse to plain "Hipped"; gable subtypes are kept;
# typos and casing are normalized.
ROOF_CANON = {
    "side gable": "Side Gable",
    "front gable": "Front Gable",
    "cross gable": "Cross Gable",
    "cross-gable": "Cross Gable",      # typo
    "front gabled": "Front Gable",     # typo
    "gable": "Gable",
    "cross hipped": "Hipped",          # collapse hip direction
    "side hipped": "Hipped",
    "front hipped": "Hipped",
    "hipped": "Hipped",
    "dutch hipped": "Dutch Hipped",
    # casing/naming aligned to the data2 / Format-B majority spelling so the
    # backfilled values merge with the existing classes instead of fragmenting.
    "cross hip-on-gable": "Cross Hip-on-Gable",
    "front hip-on-gable": "Hip-on-Gable",
    "side hip-on-gable": "Hip-on-Gable",
    "hip-on-gable": "Hip-on-Gable",
    "cross gambrel": "Gambrel",
    "front gambrel": "Gambrel",
    "gambrel": "Gambrel",
    "mansard": "Mansard",
    "barrel": "Barrel Roof",
    "pyramidal": "Pyramidal",
    "flat": "Flat",
    "shed": "Shed",
    "other": "Other",
}


def clean_id(value: str) -> str:
    return str(value).strip().strip(QUOTE_CHARS).strip()


def sanitize(value: str) -> str:
    return WS_RUN.sub(" ", str(value)).strip()


def canon_categorical(value: str) -> str:
    """Split on , or ; ; canonicalize tokens; drop null tokens; rejoin with '; '."""
    value = sanitize(value)
    if not value:
        return ""
    parts = re.split(r"\s*[;,]\s*", value)
    out = []
    for p in parts:
        p = re.sub(r"\s{2,}", " ", p).strip()
        p = TOKEN_FIXES.get(p, p)
        if p.lower() in NULL_TOKENS:
            continue
        if p not in out:
            out.append(p)
    return "; ".join(out)


def norm_stories(value: str) -> str:
    value = sanitize(value)
    if value.lower() in NULL_TOKENS:
        return ""
    value = STORIES_HALF.sub(r"\1-\2", value)
    # The ArcGIS .xls STORIES column is corrupted by Excel date-coercion
    # (e.g. "1-1/2" -> "1/1/2002", "10-19" -> "19-Oct"); the true value is
    # recovered from the raw All Data Query files (see build_raw_lookups).
    # Gate on a positive whitelist of valid story forms so any corrupted or
    # malformed token (date artifacts, "2-/12", ...) never becomes a label.
    if not STORIES_VALID.fullmatch(value):
        return ""
    return value


def map_alteration(raw: str) -> str:
    """Lossy raw-phrase -> schema '<n> - <name>' (most-severe wins)."""
    raw = sanitize(raw)
    if not raw:
        return ""
    levels = []
    for part in re.split(r"\s*;\s*", raw):
        lvl = ALT_LEVEL.get(part.strip().lower())
        if lvl:
            levels.append(lvl)
    if not levels:
        return ""
    n = min(levels)
    return f"{n} - {ALT_NAME[n]}"


def canon_roof_token(tok: str):
    """Canonicalize a single roof token; return None to drop it."""
    t = sanitize(tok)
    lc = t.lower()
    if lc in NULL_TOKENS or lc == "unknown roof type":
        return None
    return ROOF_CANON.get(lc, t)


def roof_parent(tok: str) -> str:
    """Coarse roof family used to decide which coarse part a detail value covers."""
    t = tok.lower()
    if "hip-on-gable" in t:
        return "hip-on-gable"
    if "gable" in t:
        return "gable"
    if "hipped" in t:          # Hipped, Dutch Hipped
        return "hipped"
    if "gambrel" in t:
        return "gambrel"
    return t


def _roof_tokens(raw: str) -> list:
    raw = sanitize(raw)
    if not raw:
        return []
    out = []
    for part in re.split(r"\s*[;,]\s*", raw):
        c = canon_roof_token(part)
        if c and c not in out:
            out.append(c)
    return out


def map_roof(coarse_raw: str, detail_raw: str) -> str:
    """Merge the coarse RoofType with the specific DetailedRoofType.

    When a detailed value is present it replaces the coarse parent it describes
    (e.g. coarse `Gable; Flat` + detail `Front Gable` -> `Front Gable; Flat`),
    while coarse parts the detail does not cover (Flat, Shed, ...) are kept.
    """
    coarse = _roof_tokens(coarse_raw)
    detail = _roof_tokens(detail_raw)
    if not detail:
        return "; ".join(coarse)
    det_parents = {roof_parent(t) for t in detail}
    merged = list(detail)
    for t in coarse:
        if roof_parent(t) not in det_parents and t not in merged:
            merged.append(t)
    return "; ".join(merged)


def build_raw_lookups(raw_path: Path) -> tuple[dict, dict, dict]:
    """Map cleaned 5DV ResourceNumber -> (Alteration Level, Stories, DetailedRoofType).

    The raw All Data Query files hold uncorrupted Stories strings (the ArcGIS
    export mangles them via Excel date-coercion) and a `DetailedRoofType` column
    that resolves the coarse roof family into a specific subtype, so we recover
    both here alongside the Alteration Level backfill.
    """
    r = pd.read_excel(raw_path, dtype=str, keep_default_na=False)
    if "ResourceNumber" not in r.columns or "AlterationLevel" not in r.columns:
        logger.warning(f"{raw_path.name}: missing ResourceNumber/AlterationLevel")
        return {}, {}, {}
    has_stories = "Stories" in r.columns
    has_roof = "DetailedRoofType" in r.columns
    alt, stories, roof = {}, {}, {}
    for i, key in enumerate(r["ResourceNumber"]):
        k = clean_id(key)
        if not k:
            continue
        alt[k] = map_alteration(r["AlterationLevel"].iloc[i])
        if has_stories:
            stories[k] = norm_stories(r["Stories"].iloc[i])
        if has_roof:
            roof[k] = r["DetailedRoofType"].iloc[i]
    return alt, stories, roof


def convert_one(region: str, neighborhood: str, photos_dir: str,
                raw_file: str, arc: pd.DataFrame) -> int:
    sub = arc[arc["REGIONNAME"] == region].copy()
    alt_lookup, stories_lookup, roof_lookup = build_raw_lookups(DATA3 / raw_file)

    rows = []
    backfilled = 0
    stories_recovered = 0
    roof_recovered = 0
    for _, src in sub.iterrows():
        row = {}
        for col, name in COL_MAP.items():
            raw_val = src.get(col, "")
            if name in ("id", "smithsonianNumber"):
                row[name] = clean_id(raw_val)
            elif name == "Stories":
                row[name] = norm_stories(raw_val)
            elif name in FREE_TEXT:
                row[name] = sanitize(raw_val)
            else:
                row[name] = canon_categorical(raw_val)
        # Prefer the uncorrupted Stories from the raw file when available.
        raw_stories = stories_lookup.get(row["smithsonianNumber"], "")
        if raw_stories and raw_stories != row["Stories"]:
            row["Stories"] = raw_stories
            stories_recovered += 1
        elif raw_stories:
            row["Stories"] = raw_stories
        # Backfill the coarse roof family with the specific subtype.
        detail_roof = roof_lookup.get(row["smithsonianNumber"], "")
        row["Roof Type"] = map_roof(src.get("ROOF_TYPE", ""), detail_roof)
        if _roof_tokens(detail_roof):
            roof_recovered += 1
        alt = alt_lookup.get(row["smithsonianNumber"], "")
        if alt:
            backfilled += 1
        row["Alteration Level"] = alt
        # ArcGIS exports are intensive (SurveyComplete=1) — they collect the
        # Chimney field, so tag them "Full Survey" to match Format-B's
        # surveyLevel vocabulary (used downstream to gate chimney supervision).
        row["surveyLevel"] = "Full Survey"
        rows.append(row)

    df = pd.DataFrame(rows)
    out = DATA3 / photos_dir / f"{neighborhood} - CLEAN.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, sep="\t", index=False, quoting=csv.QUOTE_MINIMAL)
    logger.success(
        f"{neighborhood}: {len(df)} rows ({backfilled} w/ Alteration Level, "
        f"{stories_recovered} Stories recovered, {roof_recovered} Roof Type "
        f"subtypes recovered) → {out}"
    )
    return len(df)


def main() -> None:
    arc = pd.read_excel(DATA3.parent / ARCGIS, engine="xlrd",
                        dtype=str, keep_default_na=False)
    total = 0
    for region, (neighborhood, photos_dir, raw_file) in REGIONS.items():
        total += convert_one(region, neighborhood, photos_dir, raw_file, arc)
    logger.info(f"Done. {len(REGIONS)} neighborhoods, {total} rows total.")


if __name__ == "__main__":
    main()
