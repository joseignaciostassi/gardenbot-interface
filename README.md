# GardenBot — Interfaz de riego v1

Página web local que usa la cámara de la PC, reconoce la planta con el modelo de
`GardenBot_Vision-master` y dice **cuántos ml de agua** suministrar.

## Instalación (una sola vez)

Desde esta carpeta, en PowerShell:

```powershell
py -3.14 -m venv .venv
.venv\Scripts\activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install flask opencv-python pillow numpy
```

La interfaz busca el repo del modelo en `..\GardenBot_Vision-master`. Si está en otro
lugar: `$env:GARDENBOT_REPO = "C:\ruta\al\repo"` antes de ejecutar.

## Ejecutar y probar con la cámara

```powershell
.venv\Scripts\python app.py
```

1. Abrí **http://localhost:5000** en Chrome o Edge.
2. Permití el acceso a la cámara cuando el navegador lo pida (si tenés varias, aparece un selector).
3. Apuntá a una planta/vegetal y presioná **Analizar planta**.
4. Sin cámara: usá **Subir foto** (por ejemplo `carrot.jpg` u `onion.jpg` del repo).

La primera ejecución descarga los pesos ImageNet del detector (~10 MB, necesita internet).
Para cortar el servidor: `Ctrl+C`.

## Cómo decide la dosis

1. El detector (MobileNetV3 ImageNet) decide si hay un vegetal. Si no → 0 ml.
2. El clasificador elige la especie: zanahoria, cebolla, morrón, papa o zapallito.
3. Si la confianza es menor a `min_confidence` (60 %) → 0 ml, "Confianza baja".
4. Si no → `dose_ml` de esa especie en **`species.json`** (valores estimados: editalos;
   se aplican al próximo análisis sin reiniciar).

Cada análisis se guarda en `data/historial.csv`.

## API (para el rover, a futuro)

- `POST /api/analyze` (multipart, campo `image`) → JSON con `species`, `confidence`,
  `water_ml`, `decision`, `top3`, `timestamp`. El campo `water_ml` es el que va a la bomba.
- `GET /api/history` → últimos 20 análisis y total de ml de hoy.
- `GET /api/species` → contenido de `species.json`.
