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


def predict(features: dict[str, Any]) -> tuple[float, str]:
    _ensure_ml_package_path()
    from ml.predict import classify_risk, predict_probability

    artifact = load_model()
    cols = artifact.get("feature_columns", [])
    
    if len(cols) >= 13:
        mapped_features = {
            cols[0]: features.get("latitude", 17.385),
            cols[1]: features.get("longitude", 78.486),
            cols[2]: features.get("rainfall", 0.0),
            cols[3]: features.get("temperature", 30.0),
            cols[4]: features.get("humidity", 50.0),
            cols[5]: 1000.0,  # River Discharge
            cols[6]: features.get("water_level", 5.0),
            cols[7]: features.get("elevation", 500.0),
            cols[8]: "Urban", # Land Cover
            cols[9]: "Clay",  # Soil Type
            cols[10]: 5000.0, # Population Density
            cols[11]: 1.0,    # Infrastructure
            cols[12]: 0.0     # Historical Floods
        }
    else:
        mapped_features = features

    probability = predict_probability(artifact, mapped_features)
    thresholds = artifact.get("risk_thresholds", {})
    if thresholds:
        medium = float(thresholds.get("medium", 0.35))
        high = float(thresholds.get("high", 0.70))
        risk_level = "LOW" if probability < medium else "MEDIUM" if probability <= high else "HIGH"
    else:
        risk_level = classify_risk(probability)
    return probability, risk_level
