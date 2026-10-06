import joblib
import pandas as pd
from pathlib import Path

def get_risk_level(probability):
    if probability >= 0.70:
        return "HIGH"
    elif 0.40 <= probability < 0.70:
        return "MEDIUM"
    else:
        return "LOW"

def main():
    MODEL_PATH = "ml/models/flood_risk_model.joblib"
    
    if not Path(MODEL_PATH).exists():
        print(f"Error: Model not found at {MODEL_PATH}. Please train the model first.")
        return
        
    print(f"Loading model from {MODEL_PATH}...")
    pipeline = joblib.load(MODEL_PATH)
    
    # A single valid sample from the dataset schema
    sample_data = {
        "Latitude": 25.0,
        "Longitude": 85.0,
        "Rainfall (mm)": 150.5,
        "Temperature (°C)": 28.5,
        "Humidity (%)": 85.0,
        "River Discharge (m³/s)": 1200.0,
        "Water Level (m)": 8.5,
        "Elevation (m)": 100.0,
        "Land Cover": "Urban",
        "Soil Type": "Clay",
        "Population Density": 1500.0,
        "Infrastructure": 5,
        "Historical Floods": 2
    }
    
    print("\nSample Data:")
    for k, v in sample_data.items():
        print(f"  {k}: {v}")
    
    df_sample = pd.DataFrame([sample_data])
    
    prediction = pipeline.predict(df_sample)[0]
    probability = pipeline.predict_proba(df_sample)[0][1]
    
    risk_level = get_risk_level(probability)
    
    print("\n==================================================")
    print(f"Prediction: {prediction}")
    print(f"Flood Probability: {probability:.2f}")
    print(f"Risk Level: {risk_level}")
    print("==================================================")

if __name__ == "__main__":
    main()
