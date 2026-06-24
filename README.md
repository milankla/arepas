# Arepas

<p align="center">
  <img src="src/ui/public/logo.png" alt="Arepas logo" width="160" />
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Arepas fine-tunes a multi-task image classifier on historical architectural buildings.
Each building is labelled with up to 9 attributes (stories, roof type, cladding, architectural style, …).
The model is EfficientNet-B5 trained with per-task loss heads; input images are first cropped to
456×456 with a GroundingDINO-based building detector.

## Pipeline overview

```
data2/ raw images
    │
    ▼
scripts/crop_dataset.py        ← GroundingDINO detector + 456×456 letterbox crop
    │
    ▼  crops/data2/
    │
    ▼
src/models/train_multi_task.py ← EfficientNet-B5, phase 1 → phase 2 → phase 3 (experimental)
    │
    ▼  outputs/ checkpoints + MLflow metrics
```

### Current Production Model

**Best checkpoint:** `outputs/data2/b5/phase2_full/phase2/best_model_phase2.pth`  
**Configuration:** EfficientNet-B5, 7 tasks (Phase 1 + 2)  
**Performance:** 66.63% overall accuracy on validation set (Phase 2 best)

> **Phase 3 status:** Phase 3 training (7 additional fine-grained attributes) has been tabled until the next data collection cycle (2000+ additional buildings). Current dataset is too small for meaningful Phase 3 learning without explicit retention mechanisms. See [docs/PROJECT_TRAINING_STATUS_JUN_2026.md](docs/PROJECT_TRAINING_STATUS_JUN_2026.md) for full analysis and forward plan.

## Getting Started

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Run the UI

The UI is a React + Vite app backed by a FastAPI server.

**1. Start the API** (port 8000):

```sh
source .venv/bin/activate
uvicorn src.api.main:app --reload --port 8000
```

The API serves building data from `data2/image_label_mapping_phase1.csv` and images from `data2/`. Hot-reloads on Python file changes. If you regenerate the CSV, restart the server to flush the cache.

**2. Start the frontend** (port 5173):

```sh
cd src/ui
npm install   # first time only
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

> The frontend proxies `/api` to `http://localhost:8000`, so both processes must be running.

---

### 1. Crop images

Run the offline building-crop pipeline (resumes automatically):

```sh
python scripts/crop_dataset.py \
  --csv data2/image_label_mapping_phase1.csv \
  --out crops/data2 \
  --manifest crops/data2/crop_manifest.csv
```

Preview results in a browser:

```sh
python scripts/preview_crops.py \
  --manifest crops/data2/crop_manifest.csv \
  --out-root crops/data2 --port 8000
```

### 2. Train — Phase 1 (Tier 1 tasks, original images)

```sh
python -m src.models.train_multi_task \
  --csv data2/image_label_mapping_phase1.csv \
  --model-config config/models/efficientnet_b5.json \
  --start-phase 1 --end-phase 1 \
  --epochs 30 --batch-size 16 --lr 3e-4 \
  --output-dir outputs/data2/b5/phase1
```

### 3. Train — Phase 2 (add architectural_style + building_form, cropped images)

```sh
python -m src.models.train_multi_task \
  --csv data2/image_label_mapping_phase1.csv \
  --model-config config/models/efficientnet_b5.json \
  --start-phase 2 --end-phase 2 \
  --load-checkpoint outputs/data2/b5/phase1/best_model_phase1.pth \
  --cropped-root crops/data2 \
  --epochs 20 --batch-size 16 --lr 1e-4 \
  --output-dir outputs/data2/b5/cropped_v1
```

## Building crop pipeline

| Detail | Value |
|--------|-------|
| Model | `IDEA-Research/grounding-dino-tiny` (via `transformers`) |
| Text prompt | `"building. house. facade."` |
| Box / text threshold | 0.25 / 0.20 |
| Scoring | `confidence × squareness × centrality` |
| Output size | 456×456 px (square) |
| Letterbox fill | `(124, 116, 104)` ImageNet mean |
| Padding ratio | 5% around detected bbox |
| Fallback | Geometric centre-crop when no box passes threshold |
| data2/ results | 2,607 / 2,708 detected (96.3%), 0 errors |

`squareness = min(w,h)/max(w,h)` — penalises elongated full-frame boxes.  
`centrality = 1 − 2×|cx/W − 0.5|` — prefers horizontally centred buildings.

## Project Structure

```
📦 arepas/
├── src/
│   ├── image_preprocessing/
│   │   ├── grounding_dino_detector.py  # GroundingDINO detector + crop logic
│   │   └── detector_base.py            # BaseDetector ABC
│   ├── loader/                         # CSV / schema / dataset loading
│   ├── models/
│   │   ├── multi_task_classifier.py    # EfficientNet-B5 multi-task model
│   │   ├── train_multi_task.py         # Training script (phase 1 / 2)
│   │   └── evaluate.py                 # Checkpoint evaluation
│   └── fine_tune.py                    # Legacy entry point
├── scripts/
│   ├── crop_dataset.py                 # Offline crop pipeline
│   ├── preview_crops.py                # Side-by-side HTML preview
│   └── field_coverage_report.py        # Attribute coverage analysis
├── config/
│   ├── data.json / data2.json          # Data loader configs
│   └── models/efficientnet_b5.json     # Model config
├── data2/                              # Raw images + CLEAN.txt attribute files
├── crops/                              # Cropped images (git-ignored)
├── docs/                               # Technical documentation
└── requirements.txt
```

## Documentation

- [docs/MULTI_TASK_STRATEGY.md](docs/MULTI_TASK_STRATEGY.md) — full training strategy and task definitions
- [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) — detailed architecture
- [docs/RUNNING_FROM_COMMAND_LINE.md](docs/RUNNING_FROM_COMMAND_LINE.md) — command reference
- [scripts/README.md](scripts/README.md) — scripts reference

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- Built for processing Denver's historical architectural survey datasets (Discover Denver schema)
- GroundingDINO: [IDEA-Research/GroundingDINO](https://github.com/IDEA-Research/GroundingDINO)
