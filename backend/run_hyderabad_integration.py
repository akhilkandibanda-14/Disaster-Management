from datetime import date
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__)))
from app.services.integration import IntegrationService

print("==================================================")
print("HYDERABAD INTEGRATION TEST")
print("==================================================")

try:
    svc = IntegrationService(data_dir="data/raw/indofloods")

    # Inputs
    lat = 17.3850
    lon = 78.4867
    target = date(2023, 8, 1)

    print(f"Input Coordinates: {lat}, {lon}")
    print(f"Target Date: {target}")

    # Build features
    vector = svc.build_feature_vector(lat, lon, target, max_dist_km=2000.0)

    # Gauge info
    gauge_res = svc.gauge_service.get_nearest_gauge(lat, lon, 2000.0)
    print(f"GaugeID: {gauge_res.reference_gauge.gauge_id}")
    print(f"Gauge Distance: {gauge_res.distance_km:.2f} km")

    # Rainfall
    print("Rainfall T1d-T10d:")
    for i in range(1, 11):
        key = f"T{i}d"
        print(f"  {key}: {vector[key]}")

    # Shape
    df = pd.DataFrame([vector])[svc.num_cols + svc.cat_cols]
    processed = svc.pipeline.named_steps['preprocessor'].transform(df)

    print(f"Raw feature count: {df.shape[1]}")
    print(f"Processed feature count: {processed.shape[1]}")

    # Prediction
    pred = int(svc.pipeline.predict(df)[0])
    prob = svc.pipeline.predict_proba(df)[0]
    
    classes = svc.pipeline.named_steps['model'].classes_
    class_probs = {c: float(p) for c, p in zip(classes, prob)}
    
    print(f"Prediction: {pred}")
    print(f"Class probabilities: {class_probs}")
    
except Exception as e:
    print(f"Integration Test Failed: {e}")
