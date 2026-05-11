"""GroundingDINO building detector via HuggingFace Transformers.

Uses the zero-shot open-vocabulary detector with a text prompt
("building. house. facade.") so it directly targets architectural subjects,
unlike COCO-pretrained Faster R-CNN which has no building class.

Model: IDEA-Research/grounding-dino-tiny  (~172 MB, downloads on first use)
       IDEA-Research/grounding-dino-base  (~340 MB, higher recall)

Requirements:
    pip install transformers accelerate
"""

import time
from typing import Optional
import numpy as np
import torch
from PIL import Image
from loguru import logger

from .detector_base import BaseDetector, DetectionResult


_DEFAULT_MODEL = "IDEA-Research/grounding-dino-tiny"
_DEFAULT_PROMPT = "building. house. facade."


class GroundingDINODetector(BaseDetector):
    """Building detector using GroundingDINO (HuggingFace Transformers)."""

    def __init__(
        self,
        model_name: str = _DEFAULT_MODEL,
        device: str = "auto",
        confidence_threshold: float = 0.30,
        text_threshold: float = 0.25,
        text_prompt: str = _DEFAULT_PROMPT,
        min_area_ratio: float = 0.03,
        max_area_ratio: float = 0.99,
        padding_ratio: float = 0.05,
    ):
        """
        Args:
            model_name: HuggingFace model ID.
            device: "auto" | "cpu" | "cuda" | "mps".
            confidence_threshold: Box score threshold.
            text_threshold: Text similarity threshold for GroundingDINO.
            text_prompt: Dot-separated query phrases, each ending with a period.
            min_area_ratio: Smallest accepted bbox as fraction of image area.
            max_area_ratio: Largest accepted bbox as fraction of image area.
            padding_ratio: Fractional padding added around the bbox before crop.
        """
        super().__init__(model_name, device)
        self.display_name = f"GroundingDINO ({model_name.split('/')[-1]})"
        self.confidence_threshold = confidence_threshold
        self.text_threshold = text_threshold
        self.text_prompt = text_prompt
        self.min_area_ratio = min_area_ratio
        self.max_area_ratio = max_area_ratio
        self.padding_ratio = padding_ratio
        self._device = self._resolve_device(device)
        self._processor = None
        self._model = None
        self.load_model()

    @staticmethod
    def _resolve_device(device: str) -> torch.device:
        if device == "auto":
            if torch.cuda.is_available():
                return torch.device("cuda")
            if torch.backends.mps.is_available():
                return torch.device("mps")
            return torch.device("cpu")
        return torch.device(device)

    def load_model(self):
        try:
            from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection

            logger.info(f"Loading GroundingDINO ({self.model_name}) on {self._device}…")
            self._processor = AutoProcessor.from_pretrained(self.model_name)
            self._model = AutoModelForZeroShotObjectDetection.from_pretrained(
                self.model_name
            ).to(self._device)
            self._model.eval()
            logger.info(f"✓ GroundingDINO loaded on {self._device}")
        except ImportError:
            raise ImportError(
                "transformers is required: pip install transformers accelerate"
            )

    def detect(self, image_path: str) -> DetectionResult:
        try:
            start = time.time()
            image = Image.open(image_path).convert("RGB")
            width, height = image.size
            image_area = width * height

            inputs = self._processor(
                images=image,
                text=self.text_prompt,
                return_tensors="pt",
            ).to(self._device)

            with torch.no_grad():
                outputs = self._model(**inputs)

            results = self._processor.post_process_grounded_object_detection(
                outputs,
                inputs.input_ids,
                threshold=self.confidence_threshold,
                text_threshold=self.text_threshold,
                target_sizes=[(height, width)],
            )

            boxes  = results[0]["boxes"].cpu().numpy()   # (x1,y1,x2,y2) absolute pixels
            scores = results[0]["scores"].cpu().numpy()

            # Score by confidence × squareness × centrality.
            # - confidence: the model's own signal, not a proxy like area.
            # - squareness: min(w,h)/max(w,h) — penalises very wide or very tall
            #   boxes that would otherwise force heavy letterboxing.
            # - centrality: 1 - 2*|cx/W - 0.5| — rewards boxes whose centre is
            #   close to the image centre, breaking ties in favour of the
            #   main subject when a side building and a central building have
            #   similar confidence and shape scores.
            # Reject implausibly small or full-frame boxes as before.
            candidates = []
            for box, score in zip(boxes, scores):
                x1, y1, x2, y2 = map(int, box)
                area_ratio = (x2 - x1) * (y2 - y1) / image_area
                if area_ratio < self.min_area_ratio or area_ratio > self.max_area_ratio:
                    continue
                bw, bh = x2 - x1, y2 - y1
                squareness = min(bw, bh) / max(bw, bh)
                centrality = 1.0 - abs((x1 + x2) / 2.0 / width - 0.5) * 2.0
                candidates.append((float(score) * squareness * centrality, (x1, y1, x2, y2), float(score)))

            candidates.sort(key=lambda c: c[0], reverse=True)
            bboxes     = [c[1] for c in candidates]
            confidences = [c[2] for c in candidates]
            detected    = len(bboxes) > 0

            if detected:
                logger.info(
                    f"Detected {len(bboxes)} object(s) in {image_path} "
                    f"(confidence: {confidences[0]:.2f})"
                )
            else:
                logger.warning(f"No objects detected in {image_path}")

            return DetectionResult(
                image_path=image_path,
                detected=detected,
                bounding_boxes=bboxes,
                confidence_scores=confidences,
                processing_time=time.time() - start,
            )

        except Exception as e:
            logger.error(f"GroundingDINO error on {image_path}: {e}")
            return DetectionResult(
                image_path=image_path,
                detected=False,
                bounding_boxes=[],
                confidence_scores=[],
                error=str(e),
            )

    def extract_building(
        self,
        image_path: str,
        bbox: Optional[tuple] = None,
        mask=None,
        target_size: Optional[int] = None,
    ) -> Image.Image:
        """Crop the building from *image_path*.

        Args:
            target_size: When set, the padded bbox is expanded along its
                shorter dimension so the crop region is square, then the
                result is resized to ``target_size × target_size`` pixels.
                The building is always fully preserved — the extra space is
                filled with real image pixels, never letterboxed.
        """
        image = Image.open(image_path).convert("RGB")
        if bbox is None:
            result = self.detect(image_path)
            if not result.bounding_boxes:
                return image
            bbox = result.bounding_boxes[0]

        x1, y1, x2, y2 = bbox
        pad_x = int((x2 - x1) * self.padding_ratio)
        pad_y = int((y2 - y1) * self.padding_ratio)
        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(image.width,  x2 + pad_x)
        y2 = min(image.height, y2 + pad_y)

        if target_size is not None:
            # Try to expand the shorter side using real surrounding pixels so
            # the crop region is square.  If the image boundary prevents a true
            # square (e.g. the building fills the full frame), fall back to
            # letterboxing: resize preserving aspect ratio, then pad with the
            # ImageNet mean colour so no geometric distortion is introduced.
            w = x2 - x1
            h = y2 - y1
            side = max(w, h)
            if w < side:
                delta = side - w
                x1 = max(0, x1 - delta // 2)
                x2 = x1 + side
                if x2 > image.width:
                    x2 = image.width
                    x1 = max(0, x2 - side)
            if h < side:
                delta = side - h
                y1 = max(0, y1 - delta // 2)
                y2 = y1 + side
                if y2 > image.height:
                    y2 = image.height
                    y1 = max(0, y2 - side)

        crop = image.crop((x1, y1, x2, y2))
        logger.debug(f"Extracted building region: ({x1},{y1},{x2},{y2}) → {crop.size}")

        if target_size is not None:
            cw, ch = crop.size
            # Always stretch to square — consistent with how non-cropped images
            # are resized in the dataloader (Resize((size, size)) distorts
            # proportions uniformly).  Letterboxing was abandoned because it
            # introduces variable-sized fill bands that confuse the model.
            if cw != ch:
                logger.debug(f"Stretching non-square crop {cw}×{ch} → {target_size}×{target_size}")
            crop = crop.resize((target_size, target_size), Image.LANCZOS)

        return crop
