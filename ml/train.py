"""Train and persist the flood Random Forest model.

Run from the repository root with:
    python -m ml.train --dataset ml/data/flood_dataset.csv
"""

import argparse
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from ml.preprocess import FEATURE_COLUMNS, load_training_frame


def build_pipeline(seed: int) -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("classifier", RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=seed, n_jobs=-1)),
    ])


def train_model(dataset_path: str | Path, model_path: str | Path, test_size: float = 0.2, seed: int = 42) -> dict[str, object]:
    features, target, target_name = load_training_frame(dataset_path)
    if target.nunique() < 2:
        raise ValueError("The training target must contain at least two classes.")

    x_train, _, y_train, _ = train_test_split(features, target, test_size=test_size, stratify=target, random_state=seed)
    pipeline = build_pipeline(seed)
    pipeline.fit(x_train, y_train)
    artifact = {
        "pipeline": pipeline,
        "feature_columns": FEATURE_COLUMNS,
        "target_column": target_name,
        "risk_thresholds": {"medium": 0.35, "high": 0.70},
        "training_rows": len(features),
    }
    output_path = Path(model_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, output_path)
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the flood risk Random Forest model.")
    parser.add_argument("--dataset", default="ml/data/flood_dataset.csv")
    parser.add_argument("--model", default="ml/models/flood_risk_model.joblib")
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()
    artifact = train_model(args.dataset, args.model, test_size=args.test_size)
    print(f"Saved {artifact['target_column']} model trained on {artifact['training_rows']} rows to {args.model}")

if __name__ == "__main__":
    main()
