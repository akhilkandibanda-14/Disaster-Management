"""Evaluate the saved flood model on a held-out test split."""

import argparse
from pathlib import Path

from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from ml.model import load_artifact
from ml.preprocess import load_training_frame


def evaluate_model(dataset_path: str | Path, model_path: str | Path, test_size: float = 0.2, seed: int = 42) -> dict[str, object]:
    features, target, _ = load_training_frame(dataset_path)
    if target.nunique() < 2:
        raise ValueError("The evaluation target must contain at least two classes.")
    _, x_test, _, y_test = train_test_split(features, target, test_size=test_size, stratify=target, random_state=seed)
    pipeline = load_artifact(model_path)["pipeline"]
    predictions = pipeline.predict(x_test)
    probabilities = pipeline.predict_proba(x_test)[:, 1]
    return {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "f1": float(f1_score(y_test, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
        "classification_report": classification_report(y_test, predictions, zero_division=0),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the saved flood risk model.")
    parser.add_argument("--dataset", default="ml/data/flood_dataset.csv")
    parser.add_argument("--model", default="ml/models/flood_risk_model.joblib")
    args = parser.parse_args()
    print(evaluate_model(args.dataset, args.model))

if __name__ == "__main__":
    main()
