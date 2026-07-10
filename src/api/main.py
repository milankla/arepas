"""
Arepas API — FastAPI application entry point.

Run from the project root:
    uvicorn src.api.main:app --reload --port 8000
"""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.auth import require_guest, require_user
from src.api.routers import datasets, runs
from src.api.routers.datasets import DATASETS
from src.api.routers import inference

app = FastAPI(title="Arepas API", version="0.1.0")

# ---------------------------------------------------------------------------
# CORS — allow the Vite dev server (port 5173) and any localhost origin
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Static file mounts — one mount per discovered dataset
# ---------------------------------------------------------------------------
for ds_name, ds_meta in DATASETS.items():
    if ds_meta["image_root"].exists():
        app.mount(
            f"/images/{ds_name}",
            StaticFiles(directory=str(ds_meta["image_root"])),
            name=f"images_{ds_name}",
        )
    if ds_meta["crop_root"].exists():
        app.mount(
            f"/crops/{ds_name}",
            StaticFiles(directory=str(ds_meta["crop_root"])),
            name=f"crops_{ds_name}",
        )

# ---------------------------------------------------------------------------
# Routers — role enforcement at the router level.
# require_guest: anonymous OK (inference endpoints — everyone can run inference)
# require_user:  must be logged in (explore/training-history endpoints)
# ---------------------------------------------------------------------------
app.include_router(datasets.router, prefix="/api", dependencies=[Depends(require_user)])
app.include_router(runs.router, prefix="/api", dependencies=[Depends(require_user)])
app.include_router(inference.router, prefix="/api", dependencies=[Depends(require_guest)])
