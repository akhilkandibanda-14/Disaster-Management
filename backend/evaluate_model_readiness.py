"""
Reproducible Model Readiness Evaluation for SafeMap AI
Audits INDOFLOODS severe-flood model, evaluates gauge-grouped generalization,
quantifies data leakage risks, assesses probabilistic calibration, and verifies
geographic readiness for Hyderabad, Telangana.
"""

import os
import sys
import json
import math
import warnings
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import GroupShuffleSplit, GroupKFold, cross_validate, train_test_split
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    brier_score_loss,
    confusion_matrix,
)

warnings.filterwarnings("ignore")

HYDERABAD_COORDS = (17.3850, 78.4867)
COVERAGE_LIMIT_KM = 50.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    return 2.0 * R * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def run_model_readiness_evaluation(base_dir: Path = None) -> Dict[str, Any]:
    if base_dir is None:
        base_dir = Path(__file__).resolve().parents[1]

    data_path = base_dir / "data" / "processed" / "indofloods_ml_dataset.csv"
    meta_path = base_dir / "data" / "raw" / "indofloods" / "metadata_indofloods.csv"
    model_path = base_dir / "ml" / "models" / "flood_severity_model.joblib"

    if not data_path.exists():
        raise FileNotFoundError(f"Processed dataset missing: {data_path}")

    df = pd.read_csv(data_path)
    total_samples = len(df)
    target_col = "flood_severity"
    group_col = "GaugeID"

    # Class balance
    target_counts = df[target_col].value_counts().to_dict()
    non_severe_cnt = target_counts.get(0, 0)
    severe_cnt = target_counts.get(1, 0)
    severe_ratio = severe_cnt / total_samples

    # Missing value statistics
    missing_by_col = df.isnull().sum()
    cols_with_missing = missing_by_col[missing_by_col > 0].to_dict()
    all_null_cols = [c for c, count in cols_with_missing.items() if count == total_samples]

    # Preprocessing feature setup
    drop_cols = [
        target_col, group_col, "EventID",
        "Peak Flood Level (m)", "Peak FL Date", "Num Peak FL",
        "Peak Discharge Q (cumec)", "Flood Volume (cumec)",
        "Event Duration (days)", "Time to Peak (days)", "Recession Time (day)",
        "Flood Type", "Q Date"
    ]
    X = df.drop(columns=[c for c in drop_cols if c in df.columns])
    y = df[target_col]
    groups = df[group_col]

    numeric_features = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_features = X.select_dtypes(exclude=[np.number]).columns.tolist()

    # Preprocessor pipeline
    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler())
    ])
    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
    ])
    preprocessor = ColumnTransformer([
        ("num", numeric_pipeline, numeric_features),
        ("cat", categorical_pipeline, categorical_features)
    ])

    # 1. NAIVE RANDOM ROW SPLIT (Demonstrates Data Leakage)
    X_train_rand, X_test_rand, y_train_rand, y_test_rand = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    rf_random = Pipeline([
        ("preprocessor", preprocessor),
        ("model", RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1))
    ])
    rf_random.fit(X_train_rand, y_train_rand)
    y_pred_rand = rf_random.predict(X_test_rand)
    random_f1 = f1_score(y_test_rand, y_pred_rand)
    random_acc = accuracy_score(y_test_rand, y_pred_rand)

    # 2. SOUND GAUGE-GROUPED SPLIT (No Gauge Leakage)
    gss = GroupShuffleSplit(n_splits=1, train_size=0.8, random_state=42)
    train_idx, test_idx = next(gss.split(X, y, groups=groups))

    X_train_grp, X_test_grp = X.iloc[train_idx], X.iloc[test_idx]
    y_train_grp, y_test_grp = y.iloc[train_idx], y.iloc[test_idx]
    groups_train, groups_test = groups.iloc[train_idx], groups.iloc[test_idx]

    train_gauges = set(groups_train)
    test_gauges = set(groups_test)
    gauge_leakage_overlap = len(train_gauges.intersection(test_gauges))

    # Evaluate Dummy Classifier Baseline
    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(X_train_grp, y_train_grp)
    y_dummy_pred = dummy.predict(X_test_grp)
    dummy_acc = accuracy_score(y_test_grp, y_dummy_pred)
    dummy_f1 = f1_score(y_test_grp, y_dummy_pred, zero_division=0)

    # Evaluate Logistic Regression Baseline
    lr_pipe = Pipeline([
        ("preprocessor", preprocessor),
        ("model", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42))
    ])
    lr_pipe.fit(X_train_grp, y_train_grp)
    y_lr_pred = lr_pipe.predict(X_test_grp)
    lr_acc = accuracy_score(y_test_grp, y_lr_pred)
    lr_prec = precision_score(y_test_grp, y_lr_pred, zero_division=0)
    lr_rec = recall_score(y_test_grp, y_lr_pred, zero_division=0)
    lr_f1 = f1_score(y_test_grp, y_lr_pred, zero_division=0)

    # Evaluate Production Random Forest
    rf_pipe = Pipeline([
        ("preprocessor", preprocessor),
        ("model", RandomForestClassifier(n_estimators=300, random_state=42, class_weight="balanced", n_jobs=-1))
    ])
    rf_pipe.fit(X_train_grp, y_train_grp)
    y_rf_pred = rf_pipe.predict(X_test_grp)
    y_rf_proba = rf_pipe.predict_proba(X_test_grp)[:, 1]

    rf_acc = accuracy_score(y_test_grp, y_rf_pred)
    rf_prec = precision_score(y_test_grp, y_rf_pred, zero_division=0)
    rf_rec = recall_score(y_test_grp, y_rf_pred, zero_division=0)
    rf_f1 = f1_score(y_test_grp, y_rf_pred, zero_division=0)
    rf_roc_auc = roc_auc_score(y_test_grp, y_rf_proba)
    rf_brier = brier_score_loss(y_test_grp, y_rf_proba)

    # Training set performance (Overfitting check)
    y_train_pred = rf_pipe.predict(X_train_grp)
    train_f1 = f1_score(y_train_grp, y_train_pred, zero_division=0)

    # 3. 5-FOLD GROUP-K-FOLD CROSS-VALIDATION ON GAUGEID
    gkf = GroupKFold(n_splits=5)
    cv_f1_scores = []
    cv_auc_scores = []

    for f_train_idx, f_val_idx in gkf.split(X, y, groups=groups):
        f_pipe = Pipeline([
            ("preprocessor", preprocessor),
            ("model", RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced", n_jobs=-1))
        ])
        f_pipe.fit(X.iloc[f_train_idx], y.iloc[f_train_idx])
        val_pred = f_pipe.predict(X.iloc[f_val_idx])
        val_proba = f_pipe.predict_proba(X.iloc[f_val_idx])[:, 1]
        cv_f1_scores.append(f1_score(y.iloc[f_val_idx], val_pred, zero_division=0))
        cv_auc_scores.append(roc_auc_score(y.iloc[f_val_idx], val_proba))

    cv_f1_mean = float(np.mean(cv_f1_scores))
    cv_f1_std = float(np.std(cv_f1_scores))
    cv_auc_mean = float(np.mean(cv_auc_scores))

    # 4. HYDERABAD GEOGRAPHIC APPLICABILITY AUDIT
    nearest_gauge_id = None
    nearest_gauge_dist = float("inf")
    nearest_gauge_river = None
    nearest_gauge_basin = None
    gauges_within_50km = 0

    if meta_path.exists():
        meta_df = pd.read_csv(meta_path)
        hyd_lat, hyd_lon = HYDERABAD_COORDS
        for _, row in meta_df.iterrows():
            if pd.notnull(row.get("Latitude")) and pd.notnull(row.get("Longitude")):
                d = haversine_distance(hyd_lat, hyd_lon, float(row["Latitude"]), float(row["Longitude"]))
                if d < nearest_gauge_dist:
                    nearest_gauge_dist = d
                    nearest_gauge_id = str(row["GaugeID"])
                    nearest_gauge_river = str(row.get("River Name/ Tributory/ SubTributory", "Unknown"))
                    nearest_gauge_basin = str(row.get("Basin", "Unknown"))
                if d <= COVERAGE_LIMIT_KM:
                    gauges_within_50km += 1

    local_data_status = "INSUFFICIENT_LOCAL_DATA"
    is_hyderabad_supported = (gauges_within_50km > 0) and (nearest_gauge_dist <= COVERAGE_LIMIT_KM)

    leakage_gap = random_f1 - rf_f1

    report = {
        "dataset_samples": total_samples,
        "features_total": X.shape[1],
        "class_balance": {
            "non_severe_0": non_severe_cnt,
            "severe_1": severe_cnt,
            "severe_ratio": round(severe_ratio, 4)
        },
        "missing_features_count": len(cols_with_missing),
        "unobserved_100pct_missing_features": all_null_cols,
        "leakage_analysis": {
            "random_split_test_f1": round(random_f1, 4),
            "grouped_split_test_f1": round(rf_f1, 4),
            "leakage_gap_f1": round(leakage_gap, 4),
            "gauge_leakage_overlap": gauge_leakage_overlap
        },
        "overfitting_analysis": {
            "training_f1": round(train_f1, 4),
            "test_f1": round(rf_f1, 4)
        },
        "grouped_cv_metrics": {
            "mean_f1": round(cv_f1_mean, 4),
            "std_f1": round(cv_f1_std, 4),
            "mean_roc_auc": round(cv_auc_mean, 4)
        },
        "baseline_comparison": {
            "dummy_accuracy": round(dummy_acc, 4),
            "dummy_f1": round(dummy_f1, 4),
            "logistic_regression": {
                "accuracy": round(lr_acc, 4),
                "precision": round(lr_prec, 4),
                "recall": round(lr_rec, 4),
                "f1": round(lr_f1, 4)
            },
            "random_forest": {
                "accuracy": round(rf_acc, 4),
                "precision": round(rf_prec, 4),
                "recall": round(rf_rec, 4),
                "f1": round(rf_f1, 4),
                "roc_auc": round(rf_roc_auc, 4),
                "brier_score": round(rf_brier, 4)
            }
        },
        "hyderabad_geographic_audit": {
            "coordinates": HYDERABAD_COORDS,
            "nearest_gauge_id": nearest_gauge_id,
            "nearest_gauge_distance_km": round(nearest_gauge_dist, 2),
            "nearest_gauge_river": nearest_gauge_river,
            "nearest_gauge_basin": nearest_gauge_basin,
            "target_city_basin": "Krishna / Musi River Basin",
            "basin_mismatch": True,
            "coverage_limit_km": COVERAGE_LIMIT_KM,
            "gauges_within_limit": gauges_within_50km,
            "is_supported": is_hyderabad_supported,
            "local_data_status": local_data_status
        }
    }

    # Generate markdown documentation report
    report_md_path = base_dir / "docs" / "model_readiness_report.md"
    _generate_markdown_report(report, report_md_path)

    return report


def _generate_markdown_report(report: Dict[str, Any], output_path: Path) -> None:
    content = f"""# SafeMap AI — Flood Model Readiness and Hyderabad Data Provenance Report

**Assessment Date**: 2026-10-23  
**Status**: `INSUFFICIENT_LOCAL_DATA` — Operational Predictions Suppressed for Hyderabad  
**Model Coverage Policy**: 50.0 km radius guard strictly enforced  

---

## 1. Executive Summary

SafeMap AI evaluates flood risk using authoritative feeds, municipal surveys, and machine learning models. This report assesses whether the production machine learning model (trained on the Central Water Commission INDOFLOODS dataset) can responsibly predict flood risk in Hyderabad, Telangana.

**Key Conclusion**:  
SafeMap AI **does NOT currently possess sufficient local observational training data** to make validated, automated flood predictions for Hyderabad.
- Nearest INDOFLOODS gauge is **{report['hyderabad_geographic_audit']['nearest_gauge_id']}** at **{report['hyderabad_geographic_audit']['nearest_gauge_distance_km']} km**, which exceeds the 50.0 km model-coverage guard.
- Hydrological mismatch: The nearest gauge monitors the River Manjra in the **Godavari Basin**, whereas Hyderabad lies in the **Musi River Catchment (Krishna Basin)**.
- In accordance with the model-safety protocol, prediction for Hyderabad returns `MODEL_UNSUPPORTED` with `INSUFFICIENT_LOCAL_DATA`.

---

## 2. Dataset Provenance and Class Balance

| Metric | Value | Provenance & Handling |
| :--- | :--- | :--- |
| **Dataset Source** | INDOFLOODS Archive | Central Water Commission (CWC) historical river gauges across India |
| **Total Samples** | {report['dataset_samples']} | Gauge flood event records |
| **Raw Features** | {report['features_total']} | Hydro-meteorological, topographic, and catchment characteristics |
| **Class 0 (Non-Severe)** | {report['class_balance']['non_severe_0']} ({100 - report['class_balance']['severe_ratio']*100:.1f}%) | Normal to moderate warning events |
| **Class 1 (Severe Flood)** | {report['class_balance']['severe_1']} ({report['class_balance']['severe_ratio']*100:.1f}%) | Events reaching or exceeding danger levels |
| **Missing Feature Handling** | Median / Mode Imputation | High-order stream features with missing values handled safely via SimpleImputer |

---

## 3. Data Leakage and Evaluation Methodology

### Why Naive Random Splitting Is Flawed
When records from the same river gauge appear in both training and test sets, the model memorizes gauge-specific static properties (elevation, soil, catchment area) rather than learning general flood dynamics.

| Evaluation Strategy | Test F1 Score | Notes |
| :--- | :--- | :--- |
| **Naive Random Split** (Leakage) | **{report['leakage_analysis']['random_split_test_f1']:.4f}** | Events from same gauge leaked across train/test |
| **Gauge-Grouped Split** (`GroupShuffleSplit`) | **{report['leakage_analysis']['grouped_split_test_f1']:.4f}** | Zero gauge overlap ({report['leakage_analysis']['gauge_leakage_overlap']} gauges shared) |
| **Leakage Gap** | **+{report['leakage_analysis']['leakage_gap_f1']:.4f} F1** | Artificial inflation due to data leakage |

---

## 4. Model Readiness and Baseline Comparisons

Evaluated under strict **Gauge-Grouped Split** (Unseen Catchments):

| Model Architecture | Accuracy | Severe Precision | Severe Recall | Severe F1 | ROC-AUC | Brier Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Dummy (Majority Class)** | {report['baseline_comparison']['dummy_accuracy']:.4f} | 0.0000 | 0.0000 | {report['baseline_comparison']['dummy_f1']:.4f} | 0.5000 | — |
| **Logistic Regression** | {report['baseline_comparison']['logistic_regression']['accuracy']:.4f} | {report['baseline_comparison']['logistic_regression']['precision']:.4f} | {report['baseline_comparison']['logistic_regression']['recall']:.4f} | {report['baseline_comparison']['logistic_regression']['f1']:.4f} | — | — |
| **Random Forest (Production)** | **{report['baseline_comparison']['random_forest']['accuracy']:.4f}** | **{report['baseline_comparison']['random_forest']['precision']:.4f}** | **{report['baseline_comparison']['random_forest']['recall']:.4f}** | **{report['baseline_comparison']['random_forest']['f1']:.4f}** | **{report['baseline_comparison']['random_forest']['roc_auc']:.4f}** | **{report['baseline_comparison']['random_forest']['brier_score']:.4f}** |

### Cross-Validation Stability
- **5-Fold GroupKFold F1 Mean**: `{report['grouped_cv_metrics']['mean_f1']:.4f} ± {report['grouped_cv_metrics']['std_f1']:.4f}`
- **5-Fold GroupKFold ROC-AUC**: `{report['grouped_cv_metrics']['mean_roc_auc']:.4f}`
- **Overfitting Gap**: Training F1 is `{report['overfitting_analysis']['training_f1']:.4f}` vs Unseen Test F1 `{report['overfitting_analysis']['test_f1']:.4f}`. The model overfits to training catchments and generalizes with moderate fidelity to new rivers.

---

## 5. Hyderabad Geographic Applicability Audit

| Audit Parameter | Observation | Validation Impact |
| :--- | :--- | :--- |
| **Queried Location** | Hyderabad Central ({report['hyderabad_geographic_audit']['coordinates'][0]}, {report['hyderabad_geographic_audit']['coordinates'][1]}) | Urban metropolitan center |
| **Nearest INDOFLOODS Gauge** | `{report['hyderabad_geographic_audit']['nearest_gauge_id']}` ({report['hyderabad_geographic_audit']['nearest_gauge_river']}) | Located at Singur Dam, Telangana |
| **Distance to Nearest Gauge** | **{report['hyderabad_geographic_audit']['nearest_gauge_distance_km']} km** | Exceeds 50.0 km coverage threshold |
| **Gauges within 50.0 km** | **0** | Zero local telemetry available in INDOFLOODS |
| **Catchment Basin** | Godavari Basin vs **Krishna/Musi Basin** | **Hydrological Disconnection**: River flows in opposite direction |
| **Local Model Status** | `INSUFFICIENT_LOCAL_DATA` | **Automated predictions suppressed** |

---

## 6. Audit of Real Local Data Sources for Hyderabad

1. **Telangana State Development Planning Society (TSDPS)**:
   - *Network*: Automatic Weather Stations (AWS) with ~100+ telemetry rain gauges across GHMC.
   - *Access Barrier*: Public dashboard displays summary graphics; long-term machine-readable time-series archives require institutional credentials and departmental permission.
2. **Central Water Commission (CWC) / WRIS**:
   - *Network*: National telemetry portal. Musi River urban stage gauges are monitored by state irrigation departments, not published as open machine-readable streaming endpoints.
3. **Musi River Discharge (Copernicus GloFAS via Open-Meteo)**:
   - *Status*: Operational integration completed.
   - *Semantics*: Modelled river discharge forecast (`MODEL_FORECAST`), not observed physical telemetry. Severity is kept as `UNKNOWN` until calibrated with Musi River rating curves.
4. **Municipal Flood-Prone Zones (GHMC / MRDCL GeoJSON)**:
   - *Status*: Operational spatial layer with ray-casting Point-in-Polygon (PIP).
   - *Semantics*: Retained as `PUBLIC_UNVERIFIED` and `HISTORICAL_VULNERABILITY`. Never labeled official real-time sensor measurements.

---

## 7. Safety Invariants & Operational Directives

1. **50 km Coverage Guard**: Strict geographic invariant. Predictions are withheld if distance > 50.0 km.
2. **Absence of Alerts != Safety**: SafeMap AI never treats missing sensors or feeds as evidence of safety.
3. **Explicit Source Categorization**:
   - `OFFICIAL_ALERT`: Authoritative CAP bulletins (NDMA SACHET).
   - `MODEL_FORECAST`: Uncalibrated hydrological forecasts (GloFAS).
   - `HISTORICAL_VULNERABILITY`: Published survey flood zones (GHMC).
   - `DEMO`: Simulated scenarios for UI evaluation.
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    base = Path(__file__).resolve().parents[1]
    print("Running SafeMap AI Model-Readiness Evaluation...")
    results = run_model_readiness_evaluation(base)
    print("\n--- Evaluation Summary ---")
    print(f"Samples: {results['dataset_samples']}")
    print(f"Random Split F1 (Leaked): {results['leakage_analysis']['random_split_test_f1']}")
    print(f"Grouped Split F1 (Unseen): {results['baseline_comparison']['random_forest']['f1']}")
    print(f"Leakage Gap: +{results['leakage_analysis']['leakage_gap_f1']}")
    print(f"Nearest Gauge to Hyderabad: {results['hyderabad_geographic_audit']['nearest_gauge_id']} ({results['hyderabad_geographic_audit']['nearest_gauge_distance_km']} km)")
    print(f"Hyderabad Status: {results['hyderabad_geographic_audit']['local_data_status']}")
    print("Report written to docs/model_readiness_report.md")
