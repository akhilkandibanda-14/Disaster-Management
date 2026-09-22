import pandas as pd
import joblib
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

# -----------------------------------
# 1. LOAD DATA
# -----------------------------------

DATA_PATH = "ml/data/flood_risk_dataset_india.csv"

df = pd.read_csv(DATA_PATH)

print("Dataset shape:", df.shape)
print("\nColumns:")
print(df.columns.tolist())

# -----------------------------------
# 2. TARGET
# -----------------------------------

target = "Flood Occurred"

X = df.drop(columns=[target])
y = df[target]

# -----------------------------------
# 3. IDENTIFY FEATURES
# -----------------------------------

numeric_features = X.select_dtypes(
    include=["int64", "float64"]
).columns.tolist()

categorical_features = X.select_dtypes(
    include=["object"]
).columns.tolist()

print("\nNumeric features:")
print(numeric_features)

print("\nCategorical features:")
print(categorical_features)

# -----------------------------------
# 4. NUMERIC PIPELINE
# -----------------------------------

numeric_pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])

# -----------------------------------
# 5. CATEGORICAL PIPELINE
# -----------------------------------

categorical_pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("encoder", OneHotEncoder(handle_unknown="ignore"))
])

# -----------------------------------
# 6. PREPROCESSOR
# -----------------------------------

preprocessor = ColumnTransformer([
    ("num", numeric_pipeline, numeric_features),
    ("cat", categorical_pipeline, categorical_features)
])

# -----------------------------------
# 7. MODEL
# -----------------------------------

model = RandomForestClassifier(
    n_estimators=200,
    random_state=42,
    class_weight="balanced",
    n_jobs=-1
)

# -----------------------------------
# 8. COMPLETE PIPELINE
# -----------------------------------

pipeline = Pipeline([
    ("preprocessor", preprocessor),
    ("model", model)
])

# -----------------------------------
# 9. TRAIN TEST SPLIT
# -----------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# -----------------------------------
# 10. TRAIN
# -----------------------------------

print("\nTraining model...")

pipeline.fit(X_train, y_train)

# -----------------------------------
# 11. EVALUATE
# -----------------------------------

y_pred = pipeline.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)

print("\nAccuracy:", accuracy)

print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# -----------------------------------
# 12. SAVE MODEL
# -----------------------------------

MODEL_PATH = "ml/models/flood_risk_model.joblib"

# Modified to save as a dictionary expected by the backend
artifact = {
    "pipeline": pipeline,
    "feature_columns": X.columns.tolist(),
    "target_column": target,
    "risk_thresholds": {"medium": 0.35, "high": 0.70},
    "training_rows": len(X)
}

output_path = Path(MODEL_PATH)
output_path.parent.mkdir(parents=True, exist_ok=True)
joblib.dump(artifact, output_path)

print("\nModel artifact saved to:")
print(MODEL_PATH)