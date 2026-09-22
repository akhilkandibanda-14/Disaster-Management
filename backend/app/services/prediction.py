from functools import lru_cache
from pathlib import Path
import sys
from typing import Any

from app.config import settings

# The ML package lives at the repository root while FastAPI is commonly launched
# from either the repository root or the backend directory.
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _ensure_ml_package_path() -> None:
    project_root = str(PROJECT_ROOT)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


def resolve_model_path() -> Path:
    configured = Path(settings.flood_model_path)
    return configured if configured.is_absolute() else PROJECT_ROOT / configured


@lru_cache(maxsize=1)
def load_model() -> dict[str, Any]:
    _ensure_ml_package_path()
    from ml.predict import load_artifact

    return load_artifact(resolve_model_path())


def clear_model_cache() -> None:
    load_model.cache_clear()


import pandas as pd

def predict(features: dict[str, Any]) -> dict[str, Any]:
    _ensure_ml_package_path()
    from ml.predict import load_artifact

    artifact = load_model()
    cols = artifact.get("feature_columns", [])
    
    if len(cols) >= 13:
        row = {
            cols[0]: features.get("latitude"),
            cols[1]: features.get("longitude"),
            cols[2]: features.get("rainfall"),
            cols[3]: features.get("temperature"),
            cols[4]: features.get("humidity"),
            cols[5]: features.get("river_discharge"),
            cols[6]: features.get("water_level"),
            cols[7]: features.get("elevation"),
            cols[8]: features.get("land_cover"),
            cols[9]: features.get("soil_type"),
            cols[10]: features.get("population_density"),
            cols[11]: features.get("infrastructure"),
            cols[12]: features.get("historical_floods")
        }
    else:
        raise ValueError("Model artifact feature columns are missing or incorrect.")

    df = pd.DataFrame([row], columns=cols)
    pipeline = artifact["pipeline"]
    
    prediction = int(pipeline.predict(df)[0])
    probability = float(pipeline.predict_proba(df)[0, 1])

    if probability >= 0.70:
        risk_level = "HIGH"
    elif probability >= 0.40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "prediction": prediction,
        "flood_probability": probability,
        "risk_level": risk_level,
        "source": "ML_MODEL"
    }
