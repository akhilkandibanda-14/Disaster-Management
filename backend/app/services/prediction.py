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
    from ml.model import load_artifact

    return load_artifact(resolve_model_path())


def clear_model_cache() -> None:
    load_model.cache_clear()


def predict(features: dict[str, float]) -> tuple[float, str]:
    _ensure_ml_package_path()
    from ml.model import classify_risk, predict_probability

    artifact = load_model()
    probability = predict_probability(artifact, features)
    thresholds = artifact.get("risk_thresholds", {})
    if thresholds:
        medium = float(thresholds.get("medium", 0.35))
        high = float(thresholds.get("high", 0.70))
        risk_level = "LOW" if probability < medium else "MEDIUM" if probability <= high else "HIGH"
    else:
        risk_level = classify_risk(probability)
    return probability, risk_level
