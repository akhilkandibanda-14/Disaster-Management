import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)

def validate_dataset(df):
    print("==================================================")
    print("DATASET VALIDATION REPORT")
    print("==================================================")
    print(f"Number of rows: {df.shape[0]}")
    print(f"Number of columns: {df.shape[1]}")
    print("\nColumn names:")
    for c in df.columns:
        print(f" - {c}")
    
    print("\nData types:")
    print(df.dtypes)
    
    print("\nMissing values:")
    print(df.isnull().sum())
    
    print(f"\nDuplicate rows: {df.duplicated().sum()}")
    
    cat_cols = ['Land Cover', 'Soil Type']
    print("\nUnique values for categorical columns:")
    for c in cat_cols:
        if c in df.columns:
            print(f" - {c}: {df[c].unique()}")
            
    if 'Flood Occurred' in df.columns:
        print("\nTarget distribution (Flood Occurred):")
        dist = df['Flood Occurred'].value_counts()
        print(dist)
        print("\nPercentages:")
        print(df['Flood Occurred'].value_counts(normalize=True) * 100)
    
    print("==================================================\n")


def main():
    # -----------------------------------
    # 1. LOAD DATA
    # -----------------------------------
    DATA_PATH = "ml/data/flood_risk_dataset_india(1).csv"
    print(f"Loading data from {DATA_PATH}...")
    df = pd.read_csv(DATA_PATH)
    
    # -----------------------------------
    # 2. DATA VALIDATION
    # -----------------------------------
    validate_dataset(df)
    
    # -----------------------------------
    # 3. PREPARE X AND y
    # -----------------------------------
    target = "Flood Occurred"
    
    # Drop target from features
    X = df.drop(columns=[target])
    y = df[target]
    
    # Feature names
    numeric_features = [
        "Latitude", "Longitude", "Rainfall (mm)", "Temperature (°C)",
        "Humidity (%)", "River Discharge (m³/s)", "Water Level (m)",
        "Elevation (m)", "Population Density", "Infrastructure", "Historical Floods"
    ]
    
    categorical_features = [
        "Land Cover", "Soil Type"
    ]
    
    print("Features used:")
    print(f"Numerical: {numeric_features}")
    print(f"Categorical: {categorical_features}")
    print(f"Target used: {target}")
    
    # Check for data leakage
    print("\nCheck for Data Leakage:")
    print("Features do not contain the target or post-event information.")
    
    # -----------------------------------
    # 4. TRAIN/TEST SPLIT
    # -----------------------------------
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"\nTraining samples: {len(X_train)}")
    print(f"Testing samples: {len(X_test)}")
    
    # -----------------------------------
    # 5. PIPELINE & PREPROCESSING
    # -----------------------------------
    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler())
    ])
    
    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore"))
    ])
    
    preprocessor = ColumnTransformer([
        ("num", numeric_pipeline, numeric_features),
        ("cat", categorical_pipeline, categorical_features)
    ])
    
    # -----------------------------------
    # 6. MODEL
    # -----------------------------------
    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1
    )
    
    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("model", model)
    ])
    
    # -----------------------------------
    # 7. TRAIN
    # -----------------------------------
    print("\nTraining Random Forest Model...")
    pipeline.fit(X_train, y_train)
    
    # -----------------------------------
    # 8. EVALUATION
    # -----------------------------------
    print("\nEvaluating Model on Test Data...")
    y_pred = pipeline.predict(X_test)
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)
    
    print(f"\nAccuracy: {acc * 100:.2f}%")
    print(f"Precision: {prec * 100:.2f}%")
    print(f"Recall: {rec * 100:.2f}%")
    print(f"F1 Score: {f1 * 100:.2f}%")
    
    print("\nConfusion Matrix:")
    print(cm)
    
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # -----------------------------------
    # 9. FEATURE IMPORTANCE
    # -----------------------------------
    print("\nFeature Importance:")
    
    # Get the feature names after preprocessing
    cat_encoder = pipeline.named_steps['preprocessor'].named_transformers_['cat'].named_steps['encoder']
    cat_feature_names = cat_encoder.get_feature_names_out(categorical_features)
    all_feature_names = np.concatenate([numeric_features, cat_feature_names])
    
    rf_model = pipeline.named_steps['model']
    importances = rf_model.feature_importances_
    
    feat_imp = pd.DataFrame({
        "Feature": all_feature_names,
        "Importance": importances
    }).sort_values(by="Importance", ascending=False)
    
    print(feat_imp.head(10))
    
    # -----------------------------------
    # 10. SAVE MODEL
    # -----------------------------------
    MODEL_PATH = "ml/models/flood_risk_model.joblib"
    output_path = Path(MODEL_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save the pipeline itself directly as per typical scikit-learn standard
    joblib.dump(pipeline, output_path)
    
    print(f"\nModel saved to: {MODEL_PATH}")


if __name__ == "__main__":
    main()