"""Carga el detector + clasificador del repo GardenBot_Vision y analiza imágenes."""

import os
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
import torchvision.transforms as T
from PIL import Image

REPO = Path(os.environ.get(
    "GARDENBOT_REPO", Path(__file__).resolve().parent.parent / "GardenBot_Vision-master"
))
sys.path.insert(0, str(REPO))

# El checkpoint corresponde a la cabeza de model.py (no model_large.py).
from model import build_model                            # noqa: E402
from detector import VegetableDetector, VEGETABLE_THRESHOLD  # noqa: E402

CHECKPOINT = Path(os.environ.get("GARDENBOT_CHECKPOINT", REPO / "checkpoints" / "best_model.pth"))
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
TOP_K = 3

_transform = T.Compose([
    T.Resize((224, 224)),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


def _preprocess(frame_bgr: np.ndarray) -> np.ndarray:
    """Mismo preprocesado que preprocess_frame() en 6_webcam_predict.py."""
    img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (224, 224), interpolation=cv2.INTER_AREA)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l, a, b = cv2.split(cv2.cvtColor(img, cv2.COLOR_RGB2LAB))
    img = cv2.cvtColor(cv2.merge([clahe.apply(l), a, b]), cv2.COLOR_LAB2RGB)
    return cv2.GaussianBlur(img, (3, 3), sigmaX=0.5)


class Vision:
    def __init__(self):
        try:
            ckpt = torch.load(CHECKPOINT, map_location=DEVICE)
        except Exception:
            # Checkpoint propio del proyecto: se permite el modo no restringido.
            ckpt = torch.load(CHECKPOINT, map_location=DEVICE, weights_only=False)
        self.class_names = ckpt["class_names"]
        self.model = build_model(num_classes=len(self.class_names), phase=2)
        self.model.load_state_dict(ckpt["model_state"])
        self.model.to(DEVICE).eval()
        self.detector = VegetableDetector(DEVICE)
        print(f"Modelos cargados — clases {self.class_names}, "
              f"val_acc={ckpt.get('val_acc', 0):.3f}, dispositivo {DEVICE}")

    @torch.no_grad()
    def analyze(self, image_bytes: bytes, threshold: float = VEGETABLE_THRESHOLD) -> dict:
        frame = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("No se pudo leer la imagen")

        detected, score = self.detector.is_vegetable(
            cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), threshold=threshold
        )
        result = {"detected": bool(detected), "detector_score": float(score), "top3": []}
        if not detected:
            return result

        tensor = _transform(Image.fromarray(_preprocess(frame))).unsqueeze(0).to(DEVICE)
        probs = torch.softmax(self.model(tensor), dim=1).squeeze().cpu()
        top_p, top_i = probs.topk(min(TOP_K, len(self.class_names)))
        result["top3"] = [
            {"species": self.class_names[i], "confidence": round(p, 4)}
            for p, i in zip(top_p.tolist(), top_i.tolist())
        ]
        return result
