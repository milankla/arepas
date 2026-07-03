"""
Combine the per-dataset Phase-1 label manifests (data / data2 / data3) into a
single training manifest, de-duplicating by building_id.

Why de-dup: some buildings appear in more than one drop (notably all 1,122
data2 "Skyland" buildings are re-surveyed in data3 "Skyland-data3", and the
small legacy data/ set is largely re-covered by the newer drops). When the same
building_id appears in multiple manifests we keep the row(s) from the
highest-priority (newest / most complete) manifest only, so every building
contributes exactly one survey's labels + images.

Priority (highest first): data3 > data2 > data.

All three manifests share the identical 30-column schema produced by
scripts/build_phase1_label_mapping.py, and image_path values are relative to the
workspace root (IMAGE_ROOT_DEFAULT="."), so the combined file is consumed by
training exactly like a single-dataset manifest:

    python -m src.models.train_multi_task \
        --csv outputs/combined/image_label_mapping_phase1.csv ...

Usage:
    python scripts/combine_manifests.py
    python scripts/combine_manifests.py \
        --manifests data3/image_label_mapping_phase1.csv \
                    data2/image_label_mapping_phase1.csv \
                    data/image_label_mapping_phase1.csv \
        --output outputs/combined/image_label_mapping_phase1.csv
"""

import argparse
from pathlib import Path

import pandas as pd
from loguru import logger

# Highest priority first: a building present in several manifests is taken from
# the first manifest (left-most) that contains it.
DEFAULT_MANIFESTS = [
    "data3/image_label_mapping_phase1.csv",
    "data2/image_label_mapping_phase1.csv",
    "data/image_label_mapping_phase1.csv",
]
DEFAULT_OUTPUT = "outputs/combined/image_label_mapping_phase1.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifests", nargs="+", default=DEFAULT_MANIFESTS,
                        help="Manifest CSVs, highest priority first.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT,
                        help="Path for the combined manifest CSV.")
    args = parser.parse_args()

    seen_ids: set[str] = set()
    parts: list[pd.DataFrame] = []
    ref_columns: list[str] | None = None

    for path in args.manifests:
        p = Path(path)
        if not p.exists():
            logger.warning(f"Skipping missing manifest: {p}")
            continue
        df = pd.read_csv(p, dtype=str, keep_default_na=False)
        if ref_columns is None:
            ref_columns = list(df.columns)
        elif list(df.columns) != ref_columns:
            raise SystemExit(
                f"Column mismatch in {p}:\n  expected {ref_columns}\n  got      {list(df.columns)}"
            )

        keep = df[~df["building_id"].isin(seen_ids)]
        dropped = len(df) - len(keep)
        new_ids = set(keep["building_id"])
        seen_ids |= new_ids
        parts.append(keep)
        logger.info(
            f"{p}: {df['building_id'].nunique()} buildings / {len(df)} rows "
            f"→ kept {len(new_ids)} new buildings / {len(keep)} rows "
            f"(dropped {dropped} duplicate rows)"
        )

    if not parts:
        raise SystemExit("No manifests found to combine.")

    combined = pd.concat(parts, ignore_index=True)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(out, index=False)

    logger.success(
        f"✅ Combined → {out} "
        f"({combined['building_id'].nunique()} buildings, {len(combined)} rows, "
        f"{combined['dataset'].nunique()} datasets)"
    )


if __name__ == "__main__":
    main()
