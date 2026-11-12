from pathlib import Path
from typing import List

from core.config import MODEL_PATH

# Ingredient names used in the database for the classes the model was trained on
KNOWN_INGREDIENTS = [
    "beef", "butter", "capsicum", "carrot", "chicken breast", "egg",
    "onion", "potatoes", "shrimp", "tofu", "tomatoes", "rice",
]


# Model labels that use a different word than the database
_ALIASES = {"prawn": "shrimp", "prawns": "shrimp", "bell pepper": "capsicum"}


class DetectionUnavailable(RuntimeError):
    """Raised when the YOLO model or its dependencies are missing."""


def _singular(word: str) -> str:
    word = word.lower().strip()
    if word.endswith("oes"):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def map_class_name(class_name: str) -> str:
    """Map a model class label (e.g. 'Potato', 'chicken_breast') to a database name."""
    cleaned = class_name.lower().replace("_", " ").replace("-", " ").strip()
    cleaned = " ".join(_ALIASES.get(word, word) for word in cleaned.split())
    for known in KNOWN_INGREDIENTS:
        if _singular(cleaned) == _singular(known):
            return known
    for known in KNOWN_INGREDIENTS:
        if _singular(known) in cleaned.split() or _singular(cleaned) in known.split():
            return known
    return cleaned


class FoodIngredientDetector:
    """YOLO ingredient detector. The model is loaded on first use so the API
    still starts when the weights or ultralytics are not installed."""

    def __init__(self, model_path=MODEL_PATH):
        self.model_path = Path(model_path)
        self._model = None

    @property
    def model(self):
        if self._model is None:
            if not self.model_path.exists():
                raise DetectionUnavailable(f"Model weights not found: {self.model_path}")
            try:
                from ultralytics import YOLO
            except ImportError as exc:
                raise DetectionUnavailable(
                    "The 'ultralytics' package is not installed"
                ) from exc
            self._model = YOLO(str(self.model_path))
        return self._model

    def detect_image(self, image_path, conf_threshold: float = 0.25) -> List[dict]:
        """Detect ingredients in one image.

        Returns one entry per ingredient: {"class_name", "confidence"},
        keeping the highest confidence, most confident first.
        """
        results = self.model.predict(source=str(image_path), conf=conf_threshold,
                                     save=False, verbose=False)
        detections = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                detections.append({
                    "class_name": self.model.names[int(box.cls[0])],
                    "confidence": float(box.conf[0]),
                })
        return self.process_detection(detections)

    def process_detection(self, detections: List[dict]) -> List[dict]:
        best = {}
        for detection in detections:
            name = map_class_name(detection["class_name"])
            confidence = float(detection["confidence"])
            if name not in best or confidence > best[name]["confidence"]:
                best[name] = {"class_name": name, "confidence": confidence}
        return sorted(best.values(), key=lambda d: d["confidence"], reverse=True)
