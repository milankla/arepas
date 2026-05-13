"""
Dataset exploration endpoints.

GET /api/datasets
GET /api/datasets/{dataset}/neighborhoods
GET /api/datasets/{dataset}/neighborhoods/{neighborhood}/buildings
GET /api/datasets/{dataset}/buildings/{building_id}
"""

from __future__ import annotations

import functools
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[3]  # project root

# ---------------------------------------------------------------------------
# Dynamic dataset discovery
#
# A "dataset" is any folder at {ROOT}/{name}/ that contains a
# image_label_mapping_phase1.csv file.  Folders matching the pattern
# data, data2, data3, … are auto-discovered at startup so new datasets
# become available without code changes.
#
# TODO: When a shared datasets root is introduced (e.g. ~/arepas-datasets/),
#       update ROOT_DATASETS below to point there and rescan.
# ---------------------------------------------------------------------------
_DATASET_CSV_NAME = "image_label_mapping_phase1.csv"


def _discover_datasets() -> dict[str, dict[str, Path]]:
    """Scan the project root for dataset folders and return their metadata."""
    result: dict[str, dict[str, Path]] = {}
    import re
    for candidate in sorted(ROOT.iterdir()):
        if not candidate.is_dir():
            continue
        # Accept folders named "data" or "dataN" (data2, data3, …)
        if not re.fullmatch(r"data\d*", candidate.name):
            continue
        csv_path = candidate / _DATASET_CSV_NAME
        if not csv_path.exists():
            continue
        name = candidate.name
        result[name] = {
            "csv": csv_path,
            "image_root": candidate,
            "crop_root": ROOT / "crops" / name,
            "crop_manifest": ROOT / "crops" / name / "crop_manifest.csv",
        }
    return result


DATASETS: dict[str, dict[str, Path]] = _discover_datasets()

ATTRIBUTE_COLUMNS = [
    "architectural_style",
    "building_form",
    "roof_type",
    "primary_cladding",
    "stories",
    "alteration_level",
    "setting",
    "chimney_present",
]

# ---------------------------------------------------------------------------
# DataFrame cache — load once per dataset
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=8)
def _load_df(dataset: str) -> pd.DataFrame:
    meta = DATASETS[dataset]
    df = pd.read_csv(meta["csv"])
    return df


@functools.lru_cache(maxsize=8)
def _load_crop_manifest(dataset: str) -> pd.DataFrame | None:
    meta = DATASETS[dataset]
    path = meta["crop_manifest"]
    if path.exists():
        return pd.read_csv(path)
    return None


def _get_dataset_meta(dataset: str) -> dict[str, Path]:
    if dataset not in DATASETS:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset}' not found.")
    return DATASETS[dataset]


def _image_url(dataset: str, image_path: str) -> str:
    """Convert a raw image_path column value to a URL served by the static mount."""
    # image_path in CSV: "data2/Cole/filename.jpg"
    # static mount: /images/data2/Cole/filename.jpg
    # Strip the leading dataset prefix if present (e.g. "data2/")
    parts = Path(image_path).parts
    # parts[0] is dataset name (e.g. "data2"), rest is neighbourhood/filename
    relative = "/".join(parts[1:]) if parts[0] == dataset else image_path
    return f"/images/{dataset}/{relative}"


def _crop_url(dataset: str, cropped_path: str) -> str:
    """Convert crop_manifest cropped_path to a URL served by the crops static mount."""
    # cropped_path in manifest: "Cole/filename_crop.jpg"
    return f"/crops/{dataset}/{cropped_path}"


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------
class DatasetInfo(BaseModel):
    id: str
    label: str
    building_count: int
    image_count: int
    neighborhoods: list[str]


class AttributeFrequency(BaseModel):
    attribute: str
    counts: dict[str, int]


class NeighborhoodStats(BaseModel):
    neighborhood: str
    building_count: int
    image_count: int
    attribute_frequencies: list[AttributeFrequency]


class BuildingSummary(BaseModel):
    building_id: str
    address: str | None
    neighborhood: str
    image_count: int
    thumbnail_url: str  # first image


class BuildingDetail(BaseModel):
    building_id: str
    address: str | None
    neighborhood: str
    attributes: dict[str, Any]
    images: list[dict[str, str | None]]  # [{original_url, crop_url|null, filename}]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/datasets", response_model=list[DatasetInfo])
def list_datasets() -> list[DatasetInfo]:
    result = []
    for ds_id in DATASETS:
        df = _load_df(ds_id)
        result.append(
            DatasetInfo(
                id=ds_id,
                label=ds_id,
                building_count=int(df["building_id"].nunique()),
                image_count=len(df),
                neighborhoods=sorted(df["neighborhood"].unique().tolist()),
            )
        )
    return result


@router.get("/datasets/{dataset}/neighborhoods", response_model=list[NeighborhoodStats])
def list_neighborhoods(dataset: str) -> list[NeighborhoodStats]:
    _get_dataset_meta(dataset)
    df = _load_df(dataset)

    result = []
    for hood, group in df.groupby("neighborhood"):
        freq: list[AttributeFrequency] = []
        for col in ATTRIBUTE_COLUMNS:
            if col not in group.columns:
                continue
            # setting is multi-label (semicolon-separated) — split before counting
            if col == "setting":
                values: list[str] = []
                for v in group[col].dropna():
                    values.extend([s.strip() for s in str(v).split(";")])
                counts = dict(Counter(values))
            else:
                counts = group[col].dropna().value_counts().to_dict()
            freq.append(AttributeFrequency(attribute=col, counts={str(k): int(v) for k, v in counts.items()}))

        result.append(
            NeighborhoodStats(
                neighborhood=str(hood),
                building_count=int(group["building_id"].nunique()),
                image_count=len(group),
                attribute_frequencies=freq,
            )
        )

    return sorted(result, key=lambda n: n.neighborhood)


@router.get(
    "/datasets/{dataset}/neighborhoods/{neighborhood}/buildings",
    response_model=list[BuildingSummary],
)
def list_buildings(dataset: str, neighborhood: str) -> list[BuildingSummary]:
    _get_dataset_meta(dataset)
    df = _load_df(dataset)

    hood_df = df[df["neighborhood"] == neighborhood]
    if hood_df.empty:
        raise HTTPException(status_code=404, detail=f"Neighborhood '{neighborhood}' not found.")

    result = []
    for building_id, group in hood_df.groupby("building_id"):
        first_image = group.iloc[0]["image_path"]
        addr = group.iloc[0].get("address", None)
        result.append(
            BuildingSummary(
                building_id=str(building_id),
                address=str(addr) if addr and str(addr) != "nan" else None,
                neighborhood=neighborhood,
                image_count=len(group),
                thumbnail_url=_image_url(dataset, first_image),
            )
        )

    return sorted(result, key=lambda b: b.building_id)


@router.get("/datasets/{dataset}/buildings/{building_id}", response_model=BuildingDetail)
def get_building(dataset: str, building_id: str) -> BuildingDetail:
    _get_dataset_meta(dataset)
    df = _load_df(dataset)
    crop_manifest = _load_crop_manifest(dataset)

    building_df = df[df["building_id"] == building_id]
    if building_df.empty:
        raise HTTPException(status_code=404, detail=f"Building '{building_id}' not found.")

    row = building_df.iloc[0]
    addr = row.get("address", None)
    attributes = {col: row[col] for col in ATTRIBUTE_COLUMNS if col in row.index}

    # Build crop lookup: image_path → cropped_path
    crop_lookup: dict[str, str] = {}
    if crop_manifest is not None:
        for _, crow in crop_manifest[
            crop_manifest["image_path"].isin(building_df["image_path"])
        ].iterrows():
            crop_lookup[crow["image_path"]] = crow["cropped_path"]

    images = []
    for _, img_row in building_df.iterrows():
        img_path = img_row["image_path"]
        cropped_path = crop_lookup.get(img_path)
        images.append(
            {
                "filename": Path(img_path).name,
                "original_url": _image_url(dataset, img_path),
                "crop_url": _crop_url(dataset, cropped_path) if cropped_path else None,
            }
        )

    return BuildingDetail(
        building_id=building_id,
        address=str(addr) if addr and str(addr) != "nan" else None,
        neighborhood=str(row["neighborhood"]),
        attributes={k: (str(v) if not pd.isna(v) else None) for k, v in attributes.items()},
        images=images,
    )
