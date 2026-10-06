import joblib
import pandas as pd
from pathlib import Path

def main():
    MODEL_PATH = "ml/models/flood_severity_model.joblib"
    
    if not Path(MODEL_PATH).exists():
        print(f"Error: Model not found at {MODEL_PATH}")
        return
        
    print(f"Loading model from {MODEL_PATH}...")
    pipeline = joblib.load(MODEL_PATH)
    
    # We construct a dummy valid feature record from the INDOFLOODS dataset schema
    sample_data = {
        "T1d": 10.5,
        "T2d": 12.0,
        "T3d": 15.0,
        "T4d": 8.0,
        "T5d": 0.0,
        "T6d": 0.0,
        "T7d": 0.0,
        "T8d": 0.0,
        "T9d": 0.0,
        "T10d": 0.0,
        "Drainage Area": 1500.5,
        "Annual Mean Temperature": 25.4,
        "Land cover": "Unknown",
        "Soil type": "Unknown"
    }
    
    print("\nSample Data:")
    for k, v in sample_data.items():
        print(f"  {k}: {v}")
        
    df_sample = pd.DataFrame([sample_data])
    
    # Predict
    prediction = pipeline.predict(df_sample)[0]
    probabilities = pipeline.predict_proba(df_sample)[0]
    
    prob_flood = probabilities[0]
    prob_severe = probabilities[1]
    
    print("\n==================================================")
    print(f"Prediction: {prediction} ({'Severe Flood' if prediction == 1 else 'Flood'})")
    print(f"Probability for Flood (0): {prob_flood:.4f}")
    print(f"Probability for Severe Flood (1): {prob_severe:.4f}")
    print("==================================================")

if __name__ == "__main__":
    main()
