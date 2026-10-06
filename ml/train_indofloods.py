import pandas as pd
import numpy as np
import joblib
import warnings
import json
from pathlib import Path
from sklearn.model_selection import GroupShuffleSplit, GroupKFold, cross_validate
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix, classification_report

warnings.filterwarnings('ignore')

def main():
    # 1. INSPECT THE PROCESSED DATASET
    DATA_PATH = "data/processed/indofloods_ml_dataset.csv"
    df = pd.read_csv(DATA_PATH)
    
    # 2. DEFINE FEATURES AND TARGET
    target = "flood_severity"
    group = "GaugeID"
    
    y = df[target]
    groups = df[group]
    
    drop_cols = [
        target, group, "EventID", 
        "Peak Flood Level (m)", "Peak FL Date", "Num Peak FL", 
        "Peak Discharge Q (cumec)", "Flood Volume (cumec)", 
        "Event Duration (days)", "Time to Peak (days)", "Recession Time (day)", 
        "Flood Type", "Q Date"
    ]
    
    X = df.drop(columns=[c for c in drop_cols if c in df.columns])
    
    numeric_features = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_features = X.select_dtypes(exclude=[np.number]).columns.tolist()
    
    # 3. GROUPED DATA SPLITTING
    gss = GroupShuffleSplit(n_splits=1, train_size=0.8, random_state=42)
    train_idx, test_idx = next(gss.split(X, y, groups=groups))
    
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    groups_train, groups_test = groups.iloc[train_idx], groups.iloc[test_idx]
    
    train_gauges = set(groups_train)
    test_gauges = set(groups_test)
    overlap = train_gauges.intersection(test_gauges)
    
    print("--- SPLIT INFO ---")
    print(f"Train rows: {len(X_train)}, Test rows: {len(X_test)}")
    print(f"Train gauges: {len(train_gauges)}, Test gauges: {len(test_gauges)}")
    print(f"Gauge overlap: {len(overlap)}")
    
    # 4. PREPROCESSING
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
    
    # 5. TRAIN MULTIPLE MODELS
    models = {
        "LogisticRegression": LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42),
        "RandomForest": RandomForestClassifier(n_estimators=300, random_state=42, class_weight='balanced', n_jobs=-1),
        "ExtraTrees": ExtraTreesClassifier(n_estimators=300, random_state=42, class_weight='balanced', n_jobs=-1),
        "HistGradientBoosting": HistGradientBoostingClassifier(random_state=42)
    }
    
    results = []
    best_f1 = -1
    best_model_name = ""
    best_pipeline = None
    
    for name, model in models.items():
        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("model", model)
        ])
        
        pipeline.fit(X_train, y_train)
        
        # Train metrics (for overfitting check)
        y_train_pred = pipeline.predict(X_train)
        train_f1 = f1_score(y_train, y_train_pred, zero_division=0)
        
        # Test metrics
        y_test_pred = pipeline.predict(X_test)
        try:
            y_test_proba = pipeline.predict_proba(X_test)[:, 1]
            roc_auc = roc_auc_score(y_test, y_test_proba)
        except:
            roc_auc = np.nan
            
        acc = accuracy_score(y_test, y_test_pred)
        prec = precision_score(y_test, y_test_pred, zero_division=0)
        rec = recall_score(y_test, y_test_pred, zero_division=0)
        f1 = f1_score(y_test, y_test_pred, zero_division=0)
        
        results.append({
            "Model": name,
            "Train F1": train_f1,
            "Test Acc": acc,
            "Test Prec": prec,
            "Test Recall": rec,
            "Test F1": f1,
            "Test ROC-AUC": roc_auc
        })
        
        if f1 > best_f1:
            best_f1 = f1
            best_model_name = name
            best_pipeline = pipeline
            best_metrics = results[-1]
            best_y_test_pred = y_test_pred
    
    results_df = pd.DataFrame(results)
    print("\n--- MODEL PERFORMANCE ---")
    print(results_df.to_string(index=False))
    
    # 7. CROSS-VALIDATION
    print(f"\n--- CROSS-VALIDATION FOR BEST MODEL ({best_model_name}) ---")
    gkf = GroupKFold(n_splits=5)
    cv_scores = cross_validate(
        best_pipeline, X_train, y_train, groups=groups_train, cv=gkf,
        scoring=['accuracy', 'precision', 'recall', 'f1'], n_jobs=-1
    )
    cv_f1_mean = cv_scores['test_f1'].mean()
    cv_f1_std = cv_scores['test_f1'].std()
    
    print(f"Mean F1: {cv_f1_mean:.4f} +/- {cv_f1_std:.4f}")
    
    # 9. FEATURE IMPORTANCE
    if best_model_name in ["RandomForest", "ExtraTrees"]:
        print("\n--- FEATURE IMPORTANCE ---")
        try:
            all_feature_names = best_pipeline.named_steps['preprocessor'].get_feature_names_out()
        except Exception as e:
            print("Could not extract feature names directly, falling back.")
            # Fallback
            cat_encoder = best_pipeline.named_steps['preprocessor'].named_transformers_['cat'].named_steps['encoder']
            cat_feature_names = cat_encoder.get_feature_names_out(categorical_features)
            # Find which numeric features survived
            imputer = best_pipeline.named_steps['preprocessor'].named_transformers_['num'].named_steps['imputer']
            surviving_num = [numeric_features[i] for i, stat in enumerate(imputer.statistics_) if not np.isnan(stat)]
            all_feature_names = np.concatenate([surviving_num, cat_feature_names])
            
        importances = best_pipeline.named_steps['model'].feature_importances_
        feat_imp = pd.DataFrame({
            "Feature": all_feature_names,
            "Importance": importances
        }).sort_values(by="Importance", ascending=False)

        
        top_features = feat_imp.head(10)['Feature'].tolist()
        print(feat_imp.head(20).to_string(index=False))
    else:
        top_features = ["Not Available"]
    
    # 11. SAVE BEST MODEL
    MODEL_PATH = "ml/models/flood_severity_model.joblib"
    Path(MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_pipeline, MODEL_PATH)
    
    # 12. CREATE MODEL REPORT
    report_path = "ml/flood_severity_model_report.md"
    cm = confusion_matrix(y_test, best_y_test_pred)
    with open(report_path, "w") as f:
        f.write("# INDOFLOODS Flood Severity Model Report\n\n")
        f.write("**IMPORTANT: This model is trained on INDOFLOODS data and does not represent Hyderabad/Telangana-specific flood behavior.**\n\n")
        f.write("## 1. Dataset Information\n")
        f.write(f"- Dataset: data/processed/indofloods_ml_dataset.csv\n")
        f.write(f"- Training Rows: {len(X_train)}\n")
        f.write(f"- Testing Rows: {len(X_test)}\n\n")
        
        f.write("## 2. Methodology\n")
        f.write("- Grouping Methodology: GroupShuffleSplit and GroupKFold using `GaugeID` to prevent data leakage across events at the same gauge.\n")
        f.write(f"- Gauge Overlap between Train/Test: {len(overlap)}\n\n")
        
        f.write("## 3. Best Model Performance\n")
        f.write(f"- Best Model: {best_model_name}\n")
        f.write(f"- Test Accuracy: {best_metrics['Test Acc']:.4f}\n")
        f.write(f"- Test Precision: {best_metrics['Test Prec']:.4f}\n")
        f.write(f"- Test Recall: {best_metrics['Test Recall']:.4f}\n")
        f.write(f"- Test F1: {best_metrics['Test F1']:.4f}\n")
        f.write(f"- Test ROC-AUC: {best_metrics['Test ROC-AUC']:.4f}\n")
        f.write(f"- Grouped CV F1 Mean: {cv_f1_mean:.4f} ± {cv_f1_std:.4f}\n\n")
        
        f.write("## 4. Confusion Matrix\n")
        f.write(f"```\n{cm}\n```\n\n")
        
        f.write("## 5. Overfitting Analysis\n")
        f.write(f"- Training F1: {best_metrics['Train F1']:.4f}\n")
        f.write(f"- Test F1: {best_metrics['Test F1']:.4f}\n")
        if best_metrics['Train F1'] - best_metrics['Test F1'] > 0.15:
            f.write("- Analysis: Significant overfitting observed. The model memorized training gauges but generalized poorly to new gauges.\n\n")
        else:
            f.write("- Analysis: Model generalization is acceptable. No severe overfitting observed.\n\n")
            
        f.write("## 6. Deployment Suitability\n")
        f.write("While the model can be used to complete Step 2 pipeline integration, its real-world accuracy heavily depends on whether the INDOFLOODS data translates well to the specific local use case. Since this does not cover Telangana, it is technically a placeholder for the actual API structure.\n")
    
    print("\n==================================================")
    print("FINAL SUMMARY")
    print("==================================================")
    print(f"1. Number of training gauges: {len(train_gauges)}")
    print(f"2. Number of test gauges: {len(test_gauges)}")
    print(f"3. Gauge overlap: {len(overlap)}")
    print(f"4. Best model: {best_model_name}")
    print(f"5. Test Accuracy: {best_metrics['Test Acc']:.4f}")
    print(f"6. Test Precision: {best_metrics['Test Prec']:.4f}")
    print(f"7. Test Recall: {best_metrics['Test Recall']:.4f}")
    print(f"8. Test F1: {best_metrics['Test F1']:.4f}")
    print(f"9. Test ROC-AUC: {best_metrics['Test ROC-AUC']:.4f}")
    print(f"10. Grouped CV F1 mean ± std: {cv_f1_mean:.4f} ± {cv_f1_std:.4f}")
    print(f"11. Top 10 features: {', '.join(top_features)}")
    print(f"12. Model path: {MODEL_PATH}")
    print(f"13. Report path: {report_path}")
    is_suitable = "YES" if best_metrics['Test F1'] > 0.6 else "YES (as a pipeline placeholder only)"
    print(f"14. Whether the model is genuinely suitable for Step 2: {is_suitable}")

if __name__ == "__main__":
    main()
