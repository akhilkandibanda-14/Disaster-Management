"""Reusable flood model loading and risk classification helpers."""

from pathlib import Path
from typing import Any

import joblib
import pandas as pd

RISK_THRESHOLDS = {"medium": 0.35, "high": 0.70}


def classify_risk(probability: float) -> str:
    if probability < RISK_THRESHOLDS["medium"]:
        return "LOW"
    if probability <= RISK_THRESHOLDS["high"]:
        return "MEDIUM"
    return "HIGH"


def load_artifact(path: str | Path) -> dict[str, Any]:
    artifact_path = Path(path)
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Flood model not found at {artifact_path}. Train it after uploading the approved dataset."
        )
    artifact = joblib.load(artifact_path)
    if not isinstance(artifact, dict) or "pipeline" not in artifact or "feature_columns" not in artifact:
        raise ValueError("Flood model artifact is missing required metadata.")
    return artifact


def predict_probability(artifact: dict[str, Any], features: dict[str, float]) -> float:
    frame = pd.DataFrame([features], columns=artifact["feature_columns"])
    probability = artifact["pipeline"].predict_proba(frame)[0, 1]
    return float(probability)
