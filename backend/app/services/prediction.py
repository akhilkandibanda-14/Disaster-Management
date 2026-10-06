from functools import lru_cache
from pathlib import Path
import sys
from typing import Any
import numpy as np
import pandas as pd
import joblib

from app.config import settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]

def _ensure_ml_package_path() -> None:
    project_root = str(PROJECT_ROOT)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

def resolve_model_path() -> Path:
    configured = Path("ml/models/flood_severity_model.joblib")
    return configured if configured.is_absolute() else PROJECT_ROOT / configured

@lru_cache(maxsize=1)
def load_model() -> Any:
    _ensure_ml_package_path()
    return joblib.load(resolve_model_path())

def clear_model_cache() -> None:
    load_model.cache_clear()

def predict(features: dict[str, Any]) -> dict[str, Any]:
    _ensure_ml_package_path()
    
    pipeline = load_model()
    
    try:
        num_cols = pipeline.named_steps['preprocessor'].transformers_[0][2]
        cat_cols = pipeline.named_steps['preprocessor'].transformers_[1][2]
    except Exception as e:
        raise ValueError(f"Could not extract features from pipeline: {e}")

    # Build the exact dataframe row
    row = {c: np.nan for c in num_cols}
    for c in cat_cols:
        row[c] = "Unknown"
        
    # Inject legitimate features from the validated input
    # E.g., T1d-T10d, which are present in IndofloodsModelInput schema.
    for col in num_cols:
        if col in features and features[col] is not None:
            row[col] = features[col]
            
    for col in cat_cols:
        if col in features and features[col] is not None:
            row[col] = features[col]

    df = pd.DataFrame([row])
    # Ensure column order matches exactly what the preprocessor expects
    df = df[list(num_cols) + list(cat_cols)]
    
    predicted_severity = int(pipeline.predict(df)[0])
    probabilities = pipeline.predict_proba(df)[0]
    flood_probability = float(probabilities[0])
    severe_flood_probability = float(probabilities[1])

    return {
        "predicted_severity": predicted_severity,
        "flood_probability": flood_probability,
        "severe_flood_probability": severe_flood_probability,
        "model_name": "INDOFLOODS Severity Model (RandomForest)",
        "model_version_status": "V1 - Real Input"
    }
