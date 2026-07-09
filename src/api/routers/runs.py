"""
Training runs API — serves run metadata and training history from the outputs/ dir.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.storage import get_storage

router = APIRouter()

_storage = get_storage()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class TaskMetrics(BaseModel):
    acc: float | None = None
    f1: float | None = None
    # setting-specific
    exact: float | None = None
    jaccard: float | None = None
    hamming: float | None = None
    f1_sample: float | None = None


class EpochRecord(BaseModel):
    epoch: int
    train_loss_total: float
    val_loss_total: float
    overall_accuracy: float
    train_losses: dict[str, float]
    val_losses: dict[str, float]
    val_metrics: dict[str, Any]


class RunNotes(BaseModel):
    summary: str = ""
    learnings: list[str] = []
    next_steps: list[str] = []


class RunInfo(BaseModel):
    run_id: str            # e.g. "data2/v1/phase1"
    short_name: str        # e.g. "b5_crop_v4"
    backbone: str
    phase: int
    epochs_completed: int
    best_val_loss: float
    best_overall_acc: float
    batch_size: int
    lr: float
    weight_decay: float
    dataset_version: str
    timestamp: str
    run_name: str
    input_type: str = "full"
    paired_views: bool = False
    paired_fusion_mode: str | None = None
    notes: RunNotes | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _discover_runs() -> list[tuple[str, str, str]]:
    """Return (run_id, history_key, config_key) for every run under outputs/."""
    results = []
    for history_key in _storage.list("outputs", suffix="/training_history.json"):
        run_dir = history_key.rsplit("/", 1)[0]
        config_key = f"{run_dir}/run_config.json"
        run_id = run_dir[len("outputs/"):] if run_dir.startswith("outputs/") else run_dir
        results.append((run_id, history_key, config_key))
    return results


def _best_acc(history: list[dict]) -> float:
    if not history:
        return 0.0
    return max(e["val_metrics"].get("overall_accuracy", 0.0) for e in history)


def _best_loss(history: list[dict]) -> float:
    if not history:
        return 0.0
    return min(e["val_losses"]["total"] for e in history)


def _input_type(run_id: str, config: dict[str, Any]) -> str:
    if config.get("paired_views", False) or "pair" in run_id.lower():
        return "paired"
    return "crop" if "crop" in run_id.lower() else "full"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/runs", response_model=list[RunInfo])
def list_runs() -> list[RunInfo]:
    """List all training runs found under outputs/."""
    runs: list[RunInfo] = []
    for run_id, history_key, config_key in _discover_runs():
        try:
            history = _storage.read_json(history_key)
        except Exception:
            continue

        config: dict = {}
        if _storage.exists(config_key):
            try:
                config = _storage.read_json(config_key)
            except Exception:
                pass

        notes_key = history_key.rsplit("/", 1)[0] + "/run_notes.json"
        notes: RunNotes | None = None
        if _storage.exists(notes_key):
            try:
                notes = RunNotes(**_storage.read_json(notes_key))
            except Exception:
                pass

        # Infer phase from path if not in config
        phase = config.get("start_phase", 0)
        if phase == 0:
            for part in Path(run_id).parts:
                if part.startswith("phase"):
                    try:
                        phase = int(part.replace("phase", ""))
                    except ValueError:
                        pass

        # Derive short name: strip leading "<dataset>/" and all trailing "/phase<N>" segments
        short_name = re.sub(r"^[^/]+/", "", run_id)
        short_name = re.sub(r"(/phase\d+)+$", "", short_name)

        runs.append(RunInfo(
            run_id=run_id,
            short_name=short_name,
            backbone=config.get("backbone", "unknown"),
            phase=phase,
            epochs_completed=len(history),
            best_val_loss=round(_best_loss(history), 6),
            best_overall_acc=round(_best_acc(history), 6),
            batch_size=config.get("batch_size", 0),
            lr=config.get("lr", 0.0),
            weight_decay=config.get("weight_decay", 0.0),
            dataset_version=config.get("dataset_version", ""),
            timestamp=config.get("timestamp", ""),
            run_name=config.get("run_name", run_id),
            input_type=_input_type(run_id, config),
            paired_views=_input_type(run_id, config) == "paired",
            paired_fusion_mode=config.get("paired_fusion_mode"),
            notes=notes,
        ))
    return runs


@router.get("/runs/{run_id:path}/history", response_model=list[EpochRecord])
def get_run_history(run_id: str) -> list[EpochRecord]:
    """Return the full epoch-by-epoch training history for a run."""
    history_key = f"outputs/{run_id}/training_history.json"
    if not _storage.exists(history_key):
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    try:
        history = _storage.read_json(history_key)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    records: list[EpochRecord] = []
    for e in history:
        records.append(EpochRecord(
            epoch=e["epoch"],
            train_loss_total=e["train_losses"]["total"],
            val_loss_total=e["val_losses"]["total"],
            overall_accuracy=e["val_metrics"].get("overall_accuracy", 0.0),
            train_losses=e["train_losses"],
            val_losses=e["val_losses"],
            val_metrics=e["val_metrics"],
        ))
    return records
