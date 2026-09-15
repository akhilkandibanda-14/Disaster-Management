"""Validation and loading for the supplied flood training dataset."""

from pathlib import Path

import pandas as pd

FEATURE_COLUMNS = [
    "latitude",
    "longitude",
    "rainfall",
    "temperature",
    "humidity",
    "water_level",
    "elevation",
]


def validate_feature_columns(columns: list[str]) -> None:
    missing = set(FEATURE_COLUMNS) - set(columns)
    if missing:
        raise ValueError(f"Missing required flood features: {sorted(missing)}")


def load_training_frame(path: str | Path) -> tuple[pd.DataFrame, pd.Series, str]:
    dataset_path = Path(path)
    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Flood dataset not found at {dataset_path}. Upload the approved CSV before training."
        )

    frame = pd.read_csv(dataset_path)
    validate_feature_columns(frame.columns.tolist())
    target_candidates = [name for name in ("flood_occurrence", "flood_risk") if name in frame.columns]
    if len(target_candidates) != 1:
        raise ValueError("Dataset must contain exactly one target: flood_occurrence or flood_risk.")

    target_name = target_candidates[0]
    selected = frame[FEATURE_COLUMNS + [target_name]].copy()
    for column in FEATURE_COLUMNS:
        selected[column] = pd.to_numeric(selected[column], errors="coerce")
    selected[target_name] = pd.to_numeric(selected[target_name], errors="coerce")
    selected = selected.dropna(subset=[target_name])
    if selected.empty:
        raise ValueError("Dataset has no rows with a valid target value.")

    target = selected.pop(target_name).astype(int)
    if not target.isin([0, 1]).all():
        raise ValueError(f"Target {target_name} must contain only binary 0/1 values.")
    return selected, target, target_name
