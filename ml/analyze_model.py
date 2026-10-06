import pandas as pd
import numpy as np
import warnings
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

warnings.filterwarnings('ignore')

def analyze_target(df, numeric_features, categorical_features, target):
    print("==================================================")
    print("2. TARGET ANALYSIS")
    print("==================================================")
    print(df[target].value_counts())
    print(df[target].value_counts(normalize=True))
    
    print("\nNumerical Feature Means by Target:")
    print(df.groupby(target)[numeric_features].mean().T)
    
    print("\nNumerical Feature Std by Target:")
    print(df.groupby(target)[numeric_features].std().T)
    
    print("\nCategorical Feature Distributions by Target:")
    for cat in categorical_features:
        print(f"\n--- {cat} ---")
        print(pd.crosstab(df[cat], df[target], normalize='index'))

def statistical_signal(df, numeric_features, categorical_features, target):
    print("\n==================================================")
    print("3. STATISTICAL SIGNAL ANALYSIS")
    print("==================================================")
    
    # Point biserial correlation for numeric vs binary target (same as Pearson in this case)
    correlations = df[numeric_features].apply(lambda x: x.corr(df[target]))
    print("\nPearson Correlation with Target:")
    print(correlations.sort_values(key=abs, ascending=False))
    
def test_baselines(X_train, y_train, X_test, y_test, preprocessor):
    print("\n==================================================")
    print("5. BASELINE MODELS")
    print("==================================================")
    
    models = {
        "Dummy": DummyClassifier(strategy="most_frequent"),
        "LogisticRegression": LogisticRegression(max_iter=1000, class_weight='balanced'),
        "RandomForest": RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced', n_jobs=-1),
        "ExtraTrees": ExtraTreesClassifier(n_estimators=100, random_state=42, class_weight='balanced', n_jobs=-1),
        "HistGradientBoosting": HistGradientBoostingClassifier(random_state=42)
    }
    
    results = []
    
    for name, model in models.items():
        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("model", model)
        ])
        
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)
        
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        
        results.append({
            "Model": name,
            "Accuracy": acc,
            "Precision": prec,
            "Recall": rec,
            "F1": f1
        })
        
    results_df = pd.DataFrame(results)
    print(results_df.to_string(index=False))
    return results_df

def cross_validation(X_train, y_train, preprocessor):
    print("\n==================================================")
    print("9. CROSS-VALIDATION (Random Forest)")
    print("==================================================")
    
    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("model", RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced', n_jobs=-1))
    ])
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    scores = cross_validate(
        pipeline, X_train, y_train, cv=cv,
        scoring=['accuracy', 'precision', 'recall', 'f1'],
        n_jobs=-1
    )
    
    print(f"Mean Accuracy: {scores['test_accuracy'].mean():.4f} +/- {scores['test_accuracy'].std():.4f}")
    print(f"Mean Precision: {scores['test_precision'].mean():.4f} +/- {scores['test_precision'].std():.4f}")
    print(f"Mean Recall: {scores['test_recall'].mean():.4f} +/- {scores['test_recall'].std():.4f}")
    print(f"Mean F1: {scores['test_f1'].mean():.4f} +/- {scores['test_f1'].std():.4f}")

def main():
    DATA_PATH = "ml/data/flood_risk_dataset_india(1).csv"
    df = pd.read_csv(DATA_PATH)
    
    target = "Flood Occurred"
    X = df.drop(columns=[target])
    y = df[target]
    
    numeric_features = [
        "Latitude", "Longitude", "Rainfall (mm)", "Temperature (°C)",
        "Humidity (%)", "River Discharge (m³/s)", "Water Level (m)",
        "Elevation (m)", "Population Density", "Infrastructure", "Historical Floods"
    ]
    categorical_features = ["Land Cover", "Soil Type"]
    
    analyze_target(df, numeric_features, categorical_features, target)
    statistical_signal(df, numeric_features, categorical_features, target)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
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
    
    test_baselines(X_train, y_train, X_test, y_test, preprocessor)
    cross_validation(X_train, y_train, preprocessor)
    
    print("\nDone.")

if __name__ == "__main__":
    main()
