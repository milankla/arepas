"""
Training runs API — serves run metadata and training history from the outputs/ dir.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

OUTPUTS_ROOT = Path("outputs")


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
    notes: RunNotes | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _discover_runs() -> list[tuple[str, Path, Path]]:
    """Walk outputs/ and yield (run_id, history_path, config_path) tuples."""
    results = []
    if not OUTPUTS_ROOT.exists():
        return results
    for history_path in sorted(OUTPUTS_ROOT.rglob("training_history.json")):
        config_path = history_path.parent / "run_config.json"
        rel = history_path.parent.relative_to(OUTPUTS_ROOT)
        run_id = str(rel).replace(os.sep, "/")
        results.append((run_id, history_path, config_path))
    return results


def _best_acc(history: list[dict]) -> float:
    if not history:
        return 0.0
    return max(e["val_metrics"].get("overall_accuracy", 0.0) for e in history)


def _best_loss(history: list[dict]) -> float:
    if not history:
        return 0.0
    return min(e["val_losses"]["total"] for e in history)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/runs", response_model=list[RunInfo])
def list_runs() -> list[RunInfo]:
    """List all training runs found under outputs/."""
    runs: list[RunInfo] = []
    for run_id, history_path, config_path in _discover_runs():
        try:
            with open(history_path) as f:
                history = json.load(f)
        except Exception:
            continue

        config: dict = {}
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
            except Exception:
                pass

        notes_path = history_path.parent / "run_notes.json"
        notes: RunNotes | None = None
        if notes_path.exists():
            try:
                with open(notes_path) as f:
                    notes = RunNotes(**json.load(f))
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

        runs.append(RunInfo(
            run_id=run_id,
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
            notes=notes,
        ))
    return runs


@router.get("/runs/{run_id:path}/history", response_model=list[EpochRecord])
def get_run_history(run_id: str) -> list[EpochRecord]:
    """Return the full epoch-by-epoch training history for a run."""
    history_path = OUTPUTS_ROOT / run_id / "training_history.json"
    if not history_path.exists():
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    try:
        with open(history_path) as f:
            history = json.load(f)
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
