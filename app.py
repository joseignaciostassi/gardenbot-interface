"""GardenBot — interfaz v1. Ejecutar: python app.py  →  http://localhost:5000"""

import csv
import random
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from vision import Vision
from watering import compute_dose, load_config

BASE = Path(__file__).resolve().parent
HISTORY = BASE / "data" / "historial.csv"
FIELDS = ["timestamp", "species", "species_es", "confidence",
          "vwc", "vwc_min", "vwc_max", "water_ml", "decision"]

app = Flask(__name__, static_folder="static")
vision = Vision()


def read_soil_moisture(cfg: dict) -> tuple[float | None, bool]:
    """Lectura de humedad volumétrica (%). Por ahora simulada; acá irá el sensor real."""
    sim = cfg.get("simulated_sensor", {})
    if sim.get("enabled", True):
        return round(random.uniform(sim.get("min", 15), sim.get("max", 35)), 1), True
    return None, False


def append_history(entry: dict) -> None:
    HISTORY.parent.mkdir(exist_ok=True)
    if HISTORY.exists():
        with HISTORY.open(encoding="utf-8") as f:
            header = f.readline().strip().split(",")
        if header != FIELDS:  # historial con columnas viejas: se aparta para no mezclar
            HISTORY.replace(HISTORY.with_name("historial_anterior.csv"))
    new_file = not HISTORY.exists()
    with HISTORY.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        if new_file:
            w.writeheader()
        w.writerow(entry)


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/analyze")
def analyze():
    file = request.files.get("image")
    if file is None:
        return jsonify(error="Falta el campo 'image'"), 400
    try:
        result = vision.analyze(file.read())
    except ValueError as e:
        return jsonify(error=str(e)), 400

    cfg = load_config()
    vwc, simulated = read_soil_moisture(cfg) if result["detected"] else (None, False)
    dose = compute_dose(result, cfg, vwc)
    entry = {"timestamp": datetime.now().isoformat(timespec="seconds"),
             "vwc_simulated": simulated, **dose}
    append_history(entry)

    # `entry` es lo que en el futuro se enviará al rover (especie + water_ml).
    return jsonify({**result, **entry})


@app.get("/api/species")
def species():
    return jsonify(load_config())


@app.get("/api/history")
def history():
    rows = []
    if HISTORY.exists():
        with HISTORY.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    today = datetime.now().date().isoformat()
    todays = [r for r in rows if r["timestamp"].startswith(today)]
    total = sum(float(r["water_ml"] or 0) for r in todays)
    return jsonify(items=rows[-20:][::-1], today_ml=total, today_count=len(todays))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
