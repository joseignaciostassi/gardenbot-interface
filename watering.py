"""Regla de riego v1: dosis fija por especie, solo si la detección es confiable."""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "species.json"


def load_config() -> dict:
    # Se relee en cada análisis para que los cambios en species.json apliquen sin reiniciar.
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def compute_dose(vision_result: dict, cfg: dict) -> dict:
    if not vision_result["detected"] or not vision_result["top3"]:
        return {"species": None, "species_es": None, "confidence": None,
                "water_ml": 0, "decision": "Sin vegetal"}

    best = vision_result["top3"][0]
    info = cfg["species"].get(best["species"], {})
    out = {"species": best["species"],
           "species_es": info.get("nombre", best["species"]),
           "confidence": best["confidence"]}

    if best["confidence"] < cfg.get("min_confidence", 0.6):
        return {**out, "water_ml": 0, "decision": "Confianza baja, no se riega"}
    if "dose_ml" not in info:
        return {**out, "water_ml": 0, "decision": "Especie sin dosis configurada"}
    return {**out, "water_ml": info["dose_ml"], "decision": "Riego recomendado"}
