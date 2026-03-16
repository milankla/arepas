"""
Build an image-label mapping CSV for any dataset configured via a JSON config file.

Produces a training manifest for Phase 1 multi-task learning.
One row per (building × image) pair.  Only rows where ALL 6 label
columns are non-empty are written; skipped rows are reported.

Pipeline used:
  ConfigurableDataLoader  →  NeighborhoodData.buildings
  field_parser.normalize_value  →  clean label strings

Usage
─────
  # data/ dataset (default)
  python scripts/build_phase1_label_mapping.py

  # data2/ dataset
  python scripts/build_phase1_label_mapping.py \
      --config config/data2.json \
      --output data2/image_label_mapping_phase1.csv

Output columns
──────────────
  building_id          DIS identifier (quotes stripped)
  dataset              e.g. "Clayton-Bungalows"
  neighborhood         from config metadata
  style                from config metadata
  image_path           relative path from workspace root
  architectural_style
  building_form
  roof_type
  primary_cladding
  stories
  alteration_level

TODO (Priority 3): add a record_valid column once architectural_dataset.py
  is wired up — DatasetValidator maps by Address, not smithsonianNumber, so
  the ID spaces need a join key before we can flag rows cheaply.
"""

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.loader import ConfigurableDataLoader
from src.loader.field_parser import normalize_value


# ── Configuration ────────────────────────────────────────────────────────────

# Defaults — override via CLI args (see __main__ block) or main() parameters.
DEFAULT_CONFIG_PATH = "config/data.json"
DEFAULT_SCHEMA_PATH = "schema/Discover Denver Schema.txt"


def _default_output_path(config_path: str) -> str:
    """Derive a sensible output path from the config filename.

    Convention (mirrors the config/data directory naming):
        config/data.json   →  data/image_label_mapping_phase1.csv
        config/data2.json  →  data2/image_label_mapping_phase1.csv
        config/foo.json    →  foo/image_label_mapping_phase1.csv
    """
    stem = Path(config_path).stem   # e.g. "data" or "data2"
    return f"{stem}/image_label_mapping_phase1.csv"

PHASE1_FIELDS = [
    "Architectural Style",
    "Building Form",
    "Roof Type",
    "Primary Cladding",
    "Stories",
    "Alteration Level",
]

# CSV column names (snake_case)
LABEL_COLUMNS = [f.lower().replace(" ", "_") for f in PHASE1_FIELDS]


# ── Helpers ──────────────────────────────────────────────────────────────────

def extract_labels(attributes: dict) -> dict:
    """
    Extract the 6 Phase 1 label strings from a building's attribute dict.

    Uses normalize_value from field_parser — the single source of truth for
    reading raw CSV field values.

    Returns a dict mapping LABEL_COLUMNS keys to strings (possibly '' if empty).
    """
    labels = {}
    for field_name, col_name in zip(PHASE1_FIELDS, LABEL_COLUMNS):
        raw = attributes.get(field_name, {}).get("value", None)
        labels[col_name] = normalize_value(raw)
    return labels


def has_all_labels(labels: dict) -> bool:
    """Return True only if every Phase 1 label is non-empty."""
    return all(labels[col] != "" for col in LABEL_COLUMNS)


# ── Main ─────────────────────────────────────────────────────────────────────

def main(
    config_path: str = DEFAULT_CONFIG_PATH,
    output_path: str | None = None,
    schema_path: str = DEFAULT_SCHEMA_PATH,
) -> pd.DataFrame:
    """
    Build the image-label mapping CSV.

    Args:
        config_path:  Path to the dataset JSON config  (default: config/data.json)
        output_path:  Destination CSV path.  If None, derived automatically from
                      config_path stem (e.g. data2.json → data2/image_label_mapping_phase1.csv)
        schema_path:  Path to the Discover Denver schema file
    """
    if output_path is None:
        output_path = _default_output_path(config_path)

    logger.info("=" * 72)
    logger.info("  BUILD LABEL MAPPING")
    logger.info(f"  config : {config_path}")
    logger.info(f"  output : {output_path}")
    logger.info("=" * 72)

    # 1. Load datasets via ConfigurableDataLoader
    logger.info(f"Loading datasets from {config_path}…")
    logger.disable("src.loader")
    loader = ConfigurableDataLoader(config_path, schema_path=schema_path)
    all_data = loader.load_all_datasets()
    logger.enable("src.loader")
    total_buildings = sum(n.total_buildings for n in all_data.values())
    total_images    = sum(n.total_images    for n in all_data.values())
    logger.success(
        f"✅ Loaded {len(all_data)} datasets — "
        f"{total_buildings} buildings, {total_images} images"
    )

    # 2. Build rows (one per building × image pair)
    logger.info("Building label mapping rows…")

    rows = []
    skipped_no_images: int = 0
    skipped_missing_labels: dict = defaultdict(int)  # col_name → count

    for dataset_name, neighborhood in all_data.items():
        # Pull neighborhood + style from config metadata
        ds_config = loader.config.get_dataset(dataset_name)
        meta      = ds_config.metadata if ds_config else {}
        nbhd      = meta.get("neighborhood", "")
        style     = meta.get("style", "")

        for bid, bdata in neighborhood.buildings.items():
            images = bdata.get("images", [])

            if not images:
                skipped_no_images += 1
                continue

            labels = extract_labels(bdata["attributes"])

            if not has_all_labels(labels):
                # Tally which specific fields are missing for diagnostics
                for col in LABEL_COLUMNS:
                    if labels[col] == "":
                        skipped_missing_labels[col] += 1
                continue

            for img_path in images:
                rows.append(
                    {
                        "building_id":  bid,
                        "dataset":      dataset_name,
                        "neighborhood": nbhd,
                        "style":        style,
                        "image_path":   img_path,
                        **labels,
                    }
                )

    # 3. Build DataFrame + write CSV
    df = pd.DataFrame(rows)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)

    # 4. Report
    logger.info("")
    logger.info("=" * 72)
    logger.info("  RESULTS")
    logger.info("=" * 72)
    logger.success(f"✅ Rows written    : {len(df)}")
    logger.info(   f"   Unique buildings : {df['building_id'].nunique()}")
    logger.info(   f"   Datasets covered : {df['dataset'].nunique()}")
    logger.info(   f"   Output           : {output}")

    if skipped_no_images:
        logger.warning(f"   Skipped (no images)           : {skipped_no_images} buildings")
    if skipped_missing_labels:
        logger.warning("   Skipped (missing labels) per field:")
        for col, cnt in sorted(skipped_missing_labels.items(), key=lambda x: -x[1]):
            logger.warning(f"     {col}: {cnt} buildings")

    logger.info("")
    logger.info("── Label distributions ─────────────────────────────────────")
    for col in LABEL_COLUMNS:
        counts = Counter(df[col])
        logger.info(f"\n  {col}  ({len(counts)} classes, {len(df)} rows):")
        for label, cnt in counts.most_common():
            pct = cnt / len(df) * 100
            bar = "█" * int(pct / 2)
            logger.info(f"    {label:<40} {cnt:>4}  {pct:>5.1f}%  {bar}")

    logger.info("")
    logger.info("── Per-dataset row counts ──────────────────────────────────")
    for ds, grp in df.groupby("dataset"):
        bldgs = grp["building_id"].nunique()
        imgs  = len(grp)
        logger.info(f"  {ds:<40}  {bldgs:>3} buildings  {imgs:>4} rows")

    logger.info("")
    logger.info("=" * 72)
    logger.success(f"✅ Saved → {output}")
    logger.info("=" * 72)

    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build an image-label mapping CSV for a dataset."
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help=f"Dataset JSON config file (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV path (default: derived from --config, e.g. data2.json → data2/image_label_mapping_phase1.csv)",
    )
    parser.add_argument(
        "--schema",
        default=DEFAULT_SCHEMA_PATH,
        help=f"Discover Denver schema file (default: {DEFAULT_SCHEMA_PATH})",
    )
    args = parser.parse_args()

    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        colorize=True,
        level="INFO",
    )
    main(config_path=args.config, output_path=args.output, schema_path=args.schema)
