from functools import lru_cache
import math
from numbers import Real
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
    configured = Path(settings.flood_model_path)
    return configured if configured.is_absolute() else PROJECT_ROOT / configured

@lru_cache(maxsize=1)
def load_model() -> Any:
    _ensure_ml_package_path()
    return joblib.load(resolve_model_path())

def clear_model_cache() -> None:
    load_model.cache_clear()

def get_feature_schema(pipeline: Any = None) -> tuple[list[str], list[str], dict[str, tuple[Any, ...]]]:
    """Return the fitted pipeline's raw feature order and categorical vocabulary."""
    pipeline = pipeline or load_model()
    try:
        preprocessor = pipeline.named_steps["preprocessor"]
        num_cols = list(preprocessor.transformers_[0][2])
        cat_cols = list(preprocessor.transformers_[1][2])
        encoder = preprocessor.transformers_[1][1].named_steps["encoder"]
        categories = {
            column: tuple(values)
            for column, values in zip(cat_cols, encoder.categories_)
        }
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Could not extract fitted model feature schema: {error}") from error

    raw_columns = num_cols + cat_cols
    if len(raw_columns) != len(set(raw_columns)):
        raise ValueError("Fitted model feature schema contains duplicate columns.")
    if set(categories) != set(cat_cols):
        raise ValueError("Fitted model categorical schema is incomplete.")
    return num_cols, cat_cols, categories


def validate_features(features: dict[str, Any], pipeline: Any = None) -> tuple[list[str], list[str]]:
    """Validate a complete raw feature payload against the fitted pipeline schema."""
    if not isinstance(features, dict):
        raise ValueError("Input must be a JSON object containing the model's raw features.")

    num_cols, cat_cols, categories = get_feature_schema(pipeline)
    expected = set(num_cols + cat_cols)
    actual = set(features)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        raise ValueError(f"Missing required feature(s): {', '.join(missing)}")
    if extra:
        raise ValueError(f"Unknown feature(s): {', '.join(extra)}")

    for column in num_cols:
        value = features[column]
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError(f"Numeric feature '{column}' must be a finite number.")
        if not math.isfinite(float(value)):
            raise ValueError(f"Numeric feature '{column}' must be finite.")

    for column in cat_cols:
        value = features[column]
        if not isinstance(value, str):
            raise ValueError(f"Categorical feature '{column}' must be a string.")
        if value not in categories[column]:
            supported = ", ".join(repr(item) for item in categories[column])
            raise ValueError(
                f"Unsupported category {value!r} for feature '{column}'. "
                f"Supported categories: {supported}"
            )

    return num_cols, cat_cols


def predict(features: dict[str, Any]) -> dict[str, Any]:
    _ensure_ml_package_path()
    
    pipeline = load_model()
    num_cols, cat_cols = validate_features(features, pipeline)

    row = {column: features[column] for column in num_cols + cat_cols}
    df = pd.DataFrame([row])
    # Ensure column order matches exactly what the preprocessor expects
    df = df[list(num_cols) + list(cat_cols)]

    classes = np.asarray(getattr(pipeline.named_steps["model"], "classes_", []))
    if classes.ndim != 1 or len(classes) == 0 or 0 not in classes or 1 not in classes:
        raise ValueError("Model class mapping must contain class 0 (flood) and class 1 (severe flood).")

    preprocessed = pipeline.named_steps["preprocessor"].transform(df)
    expected_processed_features = getattr(pipeline.named_steps["model"], "n_features_in_", None)
    if preprocessed.ndim != 2 or preprocessed.shape[0] != 1 or preprocessed.shape[1] != expected_processed_features:
        raise ValueError(
            f"Transformed feature count mismatch: expected {expected_processed_features}, "
            f"got {preprocessed.shape[1] if preprocessed.ndim == 2 else 'invalid'}."
        )

    predictions = np.asarray(pipeline.predict(df))
    probabilities = np.asarray(pipeline.predict_proba(df))
    if predictions.shape != (1,):
        raise ValueError(f"Model returned an invalid prediction shape: {predictions.shape}.")
    if probabilities.ndim != 2 or probabilities.shape != (1, len(classes)):
        raise ValueError(f"Model returned an invalid score shape: {probabilities.shape}.")
    probabilities = probabilities[0]
    if not all(math.isfinite(float(value)) for value in probabilities):
        raise ValueError("Model returned an invalid score vector.")

    predicted_severity = int(predictions[0])
    if predicted_severity not in classes:
        raise ValueError(f"Model returned an unknown class label: {predicted_severity}")

    score_by_class = {int(label): float(score) for label, score in zip(classes, probabilities)}

    return {
        "predicted_severity": predicted_severity,
        "flood_probability": score_by_class[0],
        "severe_flood_probability": score_by_class[1],
        "model_name": "INDOFLOODS Severity Model (RandomForest)",
        "model_version_status": "V1 - Uncalibrated model scores",
        "score_semantics": "predict_proba outputs are uncalibrated model scores, not real-world probabilities or confidence."
    }
