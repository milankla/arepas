"""
Convert data3 "Final-All" (Format B) Excel files to the loader's CLEAN.txt
(TSV) format, mirroring the data2/<Neighborhood>/<Neighborhood> - CLEAN.txt
convention.

Format B columns already match the internal schema field names, so this is a
faithful xlsx → TSV dump with two cleanups:
  1. strip smart/straight quotes from the `id` column (e.g. “DIS.17785" → DIS.17785),
  2. sanitize cell values (replace embedded tab/newline with a single space) so
     the line-oriented RobustCSVParser reads each record as one row.

Output (one per neighborhood, co-located with its photos like data2):
  data3/<Neighborhood> Photos/<Neighborhood> - CLEAN.txt

Usage:
  python scripts/convert_data3_format_b.py
"""

import csv
import re
from pathlib import Path

import pandas as pd
from loguru import logger

# xlsx file  →  (neighborhood name, photos folder)
FORMAT_B = {
    "Five Points_Final-All.xlsx": ("Five Points", "Five Points Photos"),
    "Skyland-Final-All.xlsx":     ("Skyland",     "Skyland Photos"),
    "Valverde-Final-All.xlsx":    ("Valverde",    "Valverde Photos"),
    "Villa Park-Final-all.xlsx":  ("Villa Park",  "Villa Park Photos"),
    "Whittier-Final-All.xlsx":    ("Whittier",    "Whittier Photos"),
}

DATA3 = Path("data3")
QUOTE_CHARS = "\u201c\u201d\u201e\u201f\"'"          # “ ” „ ‟ " '
WS_RUN = re.compile(r"[\t\r\n]+")


def clean_id(value: str) -> str:
    """Strip wrapping quotes and whitespace from an id value."""
    return str(value).strip().strip(QUOTE_CHARS).strip()


def sanitize_cell(value: str) -> str:
    """Flatten embedded tabs/newlines so each record stays on one TSV line."""
    return WS_RUN.sub(" ", str(value)).strip()


def convert_one(xlsx_name: str, neighborhood: str, photos_dir: str) -> int:
    src = DATA3 / xlsx_name
    out = DATA3 / photos_dir / f"{neighborhood} - CLEAN.txt"

    df = pd.read_excel(src, dtype=str, keep_default_na=False, engine="openpyxl")

    if "id" not in df.columns:
        raise ValueError(f"{xlsx_name}: no 'id' column (found {list(df.columns)[:5]}…)")

    df["id"] = df["id"].map(clean_id)
    df = df.map(sanitize_cell)

    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, sep="\t", index=False, quoting=csv.QUOTE_MINIMAL)

    logger.success(f"{neighborhood}: {len(df)} rows → {out}")
    return len(df)


def main() -> None:
    total = 0
    for xlsx_name, (neighborhood, photos_dir) in FORMAT_B.items():
        total += convert_one(xlsx_name, neighborhood, photos_dir)
    logger.info(f"Done. {len(FORMAT_B)} neighborhoods, {total} rows total.")


if __name__ == "__main__":
    main()
