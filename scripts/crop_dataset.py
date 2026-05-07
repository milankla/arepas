"""
Offline building-crop pipeline for training data preparation.

Reads an image-label mapping CSV, runs Faster R-CNN detection on every image,
saves tight crops (+ 10% padding) to an output directory, and writes a
crop manifest CSV mapping each source image to its crop.

Detection strategy: Faster R-CNN (COCO-pretrained) has no explicit building/house
class, but in architectural survey photos the largest high-confidence detection
typically covers the building facade.  The detector accepts ANY class and selects
the best candidate by area × centrality.  If no detection passes the confidence
threshold, a geometric fallback is used: trim sky (top) + road (bottom), then
square-crop the centre.

Designed to be:
  • Resumable  — skips images whose crop already exists.
  • Scalable   — a single model load processes all images in one pass.
  • Self-documenting — the manifest records method and confidence for audit.

Usage
─────
    # Crop data2/ dataset (typical use case):
    python scripts/crop_dataset.py \\
        --csv  data2/image_label_mapping_phase1.csv \\
        --out  data2/crops \\
        --manifest data2/crop_manifest.csv

    # Dry-run — print stats without writing any files:
    python scripts/crop_dataset.py --csv ... --out ... --dry-run

    # Limit to first N images (spot-checking):
    python scripts/crop_dataset.py --csv ... --out ... --limit 20

Output columns in crop_manifest.csv
─────────────────────────────────────
    image_path          original relative path (matches CSV column)
    cropped_path        relative path of saved crop (from workspace root)
    method              "detected" | "geometric_fallback" | "error" | "missing_source"
    confidence          detection confidence (0.0 if fallback used)
    crop_w / crop_h     pixel dimensions of the saved crop
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger
from PIL import Image
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.image_preprocessing import GroundingDINODetector


# ── Fallback: geometric crop ──────────────────────────────────────────────────

def geometric_crop(
    img: Image.Image,
    sky_pct: float = 0.10,
    road_pct: float = 0.15,
    target_size: Optional[int] = None,
) -> Image.Image:
    """Trim sky/road margins, square-crop the centre, and optionally resize."""
    w, h = img.size
    top    = int(h * sky_pct)
    bottom = h - int(h * road_pct)
    strip  = img.crop((0, top, w, bottom))
    sw, sh = strip.size
    side   = min(sw, sh)
    left   = (sw - side) // 2
    upper  = (sh - side) // 2
    crop   = strip.crop((left, upper, left + side, upper + side))
    if target_size is not None:
        crop = crop.resize((target_size, target_size), Image.LANCZOS)
    return crop


# ── Single-image processing ───────────────────────────────────────────────────

def process_one(
    image_path: Path,
    crop_path: Path,
    detector: GroundingDINODetector,
    conf_threshold: float,
    sky_pct: float,
    road_pct: float,
    target_size: Optional[int] = None,
) -> dict:
    """Detect and crop a single image.  Returns metadata dict."""
    try:
        detection = detector.detect(str(image_path))
    except Exception as exc:
        logger.warning(f"Detection error on {image_path}: {exc} — using geometric crop")
        detection = None

    img        = Image.open(image_path).convert("RGB")
    method     = "detected"
    confidence = 0.0

    if (
        detection is None
        or not detection.detected
        or not detection.bounding_boxes
        or detection.confidence_scores[0] < conf_threshold
    ):
        method = "geometric_fallback"
        crop   = geometric_crop(img, sky_pct=sky_pct, road_pct=road_pct, target_size=target_size)
    else:
        confidence = detection.confidence_scores[0]
        bbox = detection.bounding_boxes[0]
        try:
            crop = detector.extract_building(str(image_path), bbox, target_size=target_size)
        except Exception as exc:
            logger.warning(f"extract_building failed on {image_path}: {exc} — using geometric crop")
            method = "geometric_fallback"
            crop   = geometric_crop(img, sky_pct=sky_pct, road_pct=road_pct, target_size=target_size)

    crop_path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(str(crop_path), format="JPEG", quality=95)
    return {
        "method":     method,
        "confidence": round(confidence, 4),
        "crop_w":     crop.width,
        "crop_h":     crop.height,
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crop building images from a label-mapping CSV.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--csv", required=True, help="Path to image_label_mapping_phase1.csv")
    parser.add_argument("--out", required=True, help="Directory where cropped images are saved")
    parser.add_argument(
        "--manifest", default=None,
        help="Output path for the crop manifest CSV. Defaults to <out>/crop_manifest.csv",
    )
    parser.add_argument(
        "--image-root", default=".",
        help="Root directory that image_path values in the CSV are relative to",
    )
    parser.add_argument(
        "--conf-threshold", type=float, default=0.25,
        help="Detection confidence below which the geometric fallback is used",
    )
    parser.add_argument(
        "--sky-pct", type=float, default=0.10,
        help="Fraction of image height to remove from top (sky/canopy) in geometric fallback",
    )
    parser.add_argument(
        "--road-pct", type=float, default=0.15,
        help="Fraction of image height to remove from bottom (road/sidewalk) in geometric fallback",
    )
    parser.add_argument(
        "--device", default="auto",
        help="Device for GroundingDINO inference ('auto', 'cpu', 'cuda', 'mps'). "
             "'auto' picks CUDA → MPS → CPU.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N images")
    parser.add_argument(
        "--target-size", type=int, default=456,
        help="Output crop size in pixels (square). Set to 0 to skip resizing.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print plan without writing files")
    args = parser.parse_args()

    csv_path      = Path(args.csv)
    out_dir       = Path(args.out)
    image_root    = Path(args.image_root)
    manifest_path = Path(args.manifest) if args.manifest else out_dir / "crop_manifest.csv"

    if not csv_path.exists():
        logger.error(f"CSV not found: {csv_path}")
        sys.exit(1)

    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df)} rows from {csv_path}")

    image_paths = df["image_path"].unique().tolist()
    if args.limit:
        image_paths = image_paths[: args.limit]
    logger.info(f"Unique images to process: {len(image_paths)}")

    if args.dry_run:
        logger.info("--dry-run set — no files will be written.")
        logger.info(f"Output dir : {out_dir}")
        logger.info(f"Manifest   : {manifest_path}")
        return

    # ── Load detector once ────────────────────────────────────────────────
    logger.info(f"Loading GroundingDINO detector… (device={args.device})")
    detector = GroundingDINODetector(
        device=args.device,
        confidence_threshold=0.25,   # low gate — script applies args.conf_threshold
        text_threshold=0.20,
        min_area_ratio=0.03,
        max_area_ratio=0.99,
        padding_ratio=0.05,
    )

    # ── Load existing manifest (resumable) ───────────────────────────────
    existing: dict[str, dict] = {}
    if manifest_path.exists():
        prev = pd.read_csv(manifest_path)
        for _, row in prev.iterrows():
            existing[row["image_path"]] = row.to_dict()
        logger.info(f"Resuming: {len(existing)} crops already in manifest")

    records      = list(existing.values())
    already_done = set(existing.keys())
    stats        = {"detected": 0, "geometric_fallback": 0, "skipped": 0, "error": 0}

    for img_rel in tqdm(image_paths, desc="Cropping", unit="img"):
        if img_rel in already_done:
            stats["skipped"] += 1
            continue

        src_path  = image_root / img_rel
        stem      = Path(img_rel).stem
        img_par   = Path(img_rel).parent
        # Strip the first path component (e.g. "data2") so crops land at
        # <out>/Cole/x_crop.jpg, not <out>/data2/Cole/x_crop.jpg.
        parts   = img_par.parts
        rel_dir = Path(*parts[1:]) if len(parts) > 1 else img_par
        crop_rel  = rel_dir / f"{stem}_crop.jpg"
        crop_path = out_dir / crop_rel

        if not src_path.exists():
            logger.warning(f"Source image not found: {src_path} — skipping")
            stats["error"] += 1
            records.append({
                "image_path": img_rel, "cropped_path": "",
                "method": "missing_source", "confidence": 0.0,
                "crop_w": 0, "crop_h": 0,
            })
            continue

        try:
            target_size = args.target_size if args.target_size > 0 else None
            result = process_one(
                src_path, crop_path, detector,
                args.conf_threshold, args.sky_pct, args.road_pct,
                target_size=target_size,
            )
            stats[result["method"]] = stats.get(result["method"], 0) + 1
            records.append({
                "image_path": img_rel, "cropped_path": str(crop_rel), **result,
            })
        except Exception as exc:
            logger.error(f"Error on {src_path}: {exc}")
            stats["error"] += 1
            records.append({
                "image_path": img_rel, "cropped_path": "",
                "method": "error", "confidence": 0.0,
                "crop_w": 0, "crop_h": 0,
            })

        if len(records) % 100 == 0:
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(records).to_csv(manifest_path, index=False)

    # ── Final manifest ────────────────────────────────────────────────────
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_df = pd.DataFrame(records)
    manifest_df.to_csv(manifest_path, index=False)
    logger.info(f"Manifest written: {manifest_path}  ({len(manifest_df)} rows)")

    total = len(image_paths)
    det   = stats.get("detected", 0)
    fall  = stats.get("geometric_fallback", 0)
    logger.info(
        f"\nCrop run complete — {total} images\n"
        f"  detected (bbox):      {det}  ({det/max(total,1)*100:.1f}%)\n"
        f"  geometric fallback:   {fall}  ({fall/max(total,1)*100:.1f}%)\n"
        f"  skipped (existing):   {stats['skipped']}\n"
        f"  errors:               {stats['error']}"
    )


if __name__ == "__main__":
    main()
