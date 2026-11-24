"""Regla de riego: según la humedad volumétrica del suelo (VWC %) y el rango óptimo de la especie."""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "species.json"


def load_config() -> dict:
    # Se relee en cada análisis para que los cambios en species.json apliquen sin reiniciar.
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def compute_dose(vision_result: dict, cfg: dict, vwc: float | None) -> dict:
    if not vision_result["detected"] or not vision_result["top3"]:
        return {"species": None, "species_es": None, "confidence": None, "vwc": None,
                "vwc_min": None, "vwc_max": None, "vwc_target": None,
                "water_ml": 0, "decision": "Sin vegetal"}

    best = vision_result["top3"][0]
    info = cfg["species"].get(best["species"], {})
    lo, hi = info.get("vwc_min"), info.get("vwc_max")
    target = None if lo is None or hi is None else (lo + hi) / 2
    out = {"species": best["species"],
           "species_es": info.get("nombre", best["species"]),
           "confidence": best["confidence"],
           "vwc": vwc, "vwc_min": lo, "vwc_max": hi, "vwc_target": target}

    if best["confidence"] < cfg.get("min_confidence", 0.6):
        return {**out, "water_ml": 0, "decision": "Confianza baja, no se riega"}
    if target is None:
        return {**out, "water_ml": 0, "decision": "Especie sin rango configurado"}
    if vwc is None:
        return {**out, "water_ml": 0, "decision": "Sin lectura de humedad"}
    if vwc < lo:
        ml = round((target - vwc) / 100 * cfg.get("soil_volume_ml", 2000))
        return {**out, "water_ml": ml, "decision": "Suelo seco, regar"}
    if vwc <= hi:
        return {**out, "water_ml": 0, "decision": "Humedad en rango"}
    return {**out, "water_ml": 0, "decision": "Suelo húmedo, no se riega"}
