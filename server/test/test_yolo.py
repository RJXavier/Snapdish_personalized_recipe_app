"""Runs the real YOLO model on a sample photo. Skipped when ultralytics or the
weights are not available."""
from pathlib import Path

import pytest

from core.config import MODEL_PATH
from services.detection import FoodIngredientDetector

SAMPLE = Path(__file__).resolve().parent / "beef_00003.jpg"


def test_detects_beef_in_sample_photo():
    pytest.importorskip("ultralytics")
    if not MODEL_PATH.exists():
        pytest.skip(f"model weights not found at {MODEL_PATH}")
    detections = FoodIngredientDetector().detect_image(SAMPLE)
    assert "beef" in [d["class_name"] for d in detections]
    assert all(0 <= d["confidence"] <= 1 for d in detections)
