"""
Dataset exploration endpoints.

GET /api/datasets
GET /api/datasets/{dataset}/neighborhoods
GET /api/datasets/{dataset}/neighborhoods/{neighborhood}/buildings
GET /api/datasets/{dataset}/buildings/{building_id}
GET /api/datasets/{dataset}/buildings/search?q=&limit=
"""

from __future__ import annotations

import functools
import io
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.storage import get_storage

router = APIRouter()

_storage = get_storage()

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

# The combined "all" view merges every source dataset (data + data2 + data3 + …)
# and is the manifest used for multi-dataset training. It lives outside the
# data*/ folders (in outputs/combined/), so it is registered explicitly.
COMBINED_DATASET_ID = "all"
COMBINED_DIR = ROOT / "outputs" / "combined"


def _discover_datasets() -> dict[str, dict[str, Path]]:
    """Discover datasets from the local filesystem, with S3 fallback.

    When the local ``data*/`` folders don't exist (e.g. inside the App Runner
    container) the function lists manifests from the S3 data bucket via the
    storage abstraction.  Paths are synthetic (they won't exist on disk) but
    they resolve correctly through ``_rel_key`` → ``_storage.read_bytes``.
    """
    result: dict[str, dict[str, Path]] = {}
    import re

    # ── local path ─────────────────────────────────────────────────────────
    found_local = False
    for candidate in sorted(ROOT.iterdir()):
        if not candidate.is_dir():
            continue
        if not re.fullmatch(r"data\d*", candidate.name):
            continue
        csv_path = candidate / _DATASET_CSV_NAME
        if not csv_path.exists():
            continue
        found_local = True
        name = candidate.name
        crop_root = ROOT / "crops" / name
        crop_manifest = crop_root / "crop_manifest.csv"
        if not crop_manifest.exists() and name == "data":
            legacy_manifest = ROOT / "crops" / "combined" / "crop_manifest_legacy.csv"
            if legacy_manifest.exists():
                crop_root = ROOT / "crops" / "combined"
                crop_manifest = legacy_manifest
        result[name] = {
            "csv": csv_path,
            "image_root": candidate,
            "crop_root": crop_root,
            "crop_manifest": crop_manifest,
        }

    # ── S3 fallback (container / no local data) ────────────────────────────
    if not found_local:
        # List all image_label_mapping_phase1.csv files in the data bucket.
        # Keys look like: "data2/image_label_mapping_phase1.csv"
        for key in _storage.list("", suffix=f"/{_DATASET_CSV_NAME}"):
            parts = key.split("/")
            if len(parts) < 2:
                continue
            name = parts[0]
            if not re.fullmatch(r"data\d*", name):
                continue
            # Synthesise Path objects that resolve back to logical S3 keys
            # via _rel_key().  They won't exist on disk; that's fine — all
            # reads go through _storage.read_bytes, not open().
            base = ROOT / name
            result[name] = {
                "csv": base / _DATASET_CSV_NAME,
                "image_root": base,
                "crop_root": ROOT / "crops" / name,
                "crop_manifest": ROOT / "crops" / name / "crop_manifest.csv",
            }

    # ── combined "all" view ────────────────────────────────────────────────
    combined_csv = COMBINED_DIR / _DATASET_CSV_NAME
    combined_key = f"outputs/combined/{_DATASET_CSV_NAME}"
    if combined_csv.exists() or _storage.exists(combined_key):
        result[COMBINED_DATASET_ID] = {
            "csv": combined_csv,
            "image_root": COMBINED_DIR,
            "crop_root": ROOT / "crops" / "combined",
            "crop_manifest": ROOT / "crops" / "combined" / "crop_manifest.csv",
        }
    return result


DATASETS: dict[str, dict[str, Path]] = _discover_datasets()

# Real source datasets (data, data2, data3, …) — every entry except the combined
# "all" view. Used to route combined image_paths to the right static mount.
SOURCE_DATASETS: frozenset = frozenset(
    name for name in DATASETS if name != COMBINED_DATASET_ID
)

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

# Columns that are never building attributes (system/identity columns)
_NON_ATTRIBUTE_COLS = frozenset(
    ["building_id", "address", "dataset", "neighborhood", "image_path"]
)

# ---------------------------------------------------------------------------
# DataFrame cache — load once per dataset
# ---------------------------------------------------------------------------
def _rel_key(path: Path) -> str:
    """Project-relative logical storage key for a discovered absolute path."""
    return str(Path(path).resolve().relative_to(ROOT))


@functools.lru_cache(maxsize=8)
def _load_df(dataset: str) -> pd.DataFrame:
    meta = DATASETS[dataset]
    df = pd.read_csv(io.BytesIO(_storage.read_bytes(_rel_key(meta["csv"]))))
    return df


@functools.lru_cache(maxsize=8)
def _load_crop_manifest(dataset: str) -> pd.DataFrame | None:
    if dataset == COMBINED_DATASET_ID:
        # The combined view has no crops of its own. Aggregate the per-source
        # manifests instead — each is already keyed by a full image_path with
        # its source-dataset prefix, so crop lookups resolve across datasets.
        frames = []
        for src in sorted(SOURCE_DATASETS):
            key = _rel_key(DATASETS[src]["crop_manifest"])
            if _storage.exists(key):
                frames.append(pd.read_csv(io.BytesIO(_storage.read_bytes(key))))
        if not frames:
            return None
        return pd.concat(frames, ignore_index=True)
    meta = DATASETS[dataset]
    key = _rel_key(meta["crop_manifest"])
    if _storage.exists(key):
        return pd.read_csv(io.BytesIO(_storage.read_bytes(key)))
    return None


def _get_dataset_meta(dataset: str) -> dict[str, Path]:
    if dataset not in DATASETS:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset}' not found.")
    return DATASETS[dataset]


def _image_url(dataset: str, image_path: str) -> str:
    """Return a URL for the given image.

    * Local (``LocalStorage``): returns the ``/images/…`` static-mount path,
      exactly as before.
    * S3 (``S3Storage``): returns a presigned URL so the browser can fetch
      the image directly from S3 without proxying through the API.
    """
    from src.storage.local import LocalStorage
    if isinstance(_storage, LocalStorage):
        parts = Path(image_path).parts
        if parts and parts[0] in SOURCE_DATASETS:
            return f"/images/{parts[0]}/" + "/".join(parts[1:])
        relative = "/".join(parts[1:]) if parts and parts[0] == dataset else image_path
        return f"/images/{dataset}/{relative}"
    # S3 path — image_path is the logical key (e.g. "data2/Cole/x.jpg")
    return _storage.url(image_path)


def _crop_url(dataset: str, cropped_path: str) -> str:
    """Return a URL for the given crop image.

    * Local: ``/crops/{dataset}/{cropped_path}`` (static mount).
    * S3: presigned URL using the canonical crops key.
    """
    from src.storage.local import LocalStorage
    if isinstance(_storage, LocalStorage):
        return f"/crops/{dataset}/{cropped_path}"
    # cropped_path in manifest: "Cole/filename_crop.jpg"
    return _storage.url(f"crops/{dataset}/{cropped_path}")


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
    dataset: str  # source dataset the building belongs to (data / data2 / data3)
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


@router.get("/datasets/{dataset}/buildings/search", response_model=list[BuildingSummary])
def search_buildings(
    dataset: str,
    q: str = "",
    limit: int = 10,
) -> list[BuildingSummary]:
    """Search buildings by address or building_id substring (case-insensitive)."""
    _get_dataset_meta(dataset)
    if not q or len(q) < 2:
        return []
    df = _load_df(dataset)
    q_lower = q.lower()
    # Match against building_id or address
    mask = df["building_id"].str.lower().str.contains(q_lower, regex=False)
    if "address" in df.columns:
        mask = mask | df["address"].fillna("").str.lower().str.contains(q_lower, regex=False)
    matched = df[mask].drop_duplicates(subset="building_id").head(limit)
    results = []
    for _, row in matched.iterrows():
        addr = row.get("address", None)
        results.append(BuildingSummary(
            building_id=str(row["building_id"]),
            address=str(addr) if addr and str(addr) != "nan" else None,
            neighborhood=str(row["neighborhood"]),
            image_count=int((df["building_id"] == row["building_id"]).sum()),
            thumbnail_url=_image_url(dataset, row["image_path"]),
        ))
    return results


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
    # Return all columns except system ones, with known columns first
    known = [col for col in ATTRIBUTE_COLUMNS if col in row.index]
    extra = [col for col in row.index if col not in _NON_ATTRIBUTE_COLS and col not in ATTRIBUTE_COLUMNS]
    attributes = {col: row[col] for col in known + extra}

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
        # Route the crop to its source dataset's mount (mirrors _image_url) so
        # the combined "all" view shows crops from each source dataset.
        src = Path(img_path).parts[0]
        crop_ds = src if src in SOURCE_DATASETS else dataset
        images.append(
            {
                "filename": Path(img_path).name,
                "original_url": _image_url(dataset, img_path),
                "crop_url": _crop_url(crop_ds, cropped_path) if cropped_path else None,
            }
        )

    # Source dataset (data / data2 / data3) inferred from the image_path prefix.
    source_dataset = Path(row["image_path"]).parts[0]
    dataset_label = source_dataset if source_dataset in SOURCE_DATASETS else dataset

    return BuildingDetail(
        building_id=building_id,
        address=str(addr) if addr and str(addr) != "nan" else None,
        neighborhood=str(row["neighborhood"]),
        dataset=dataset_label,
        attributes={k: (str(v) if not pd.isna(v) else None) for k, v in attributes.items()},
        images=images,
    )
