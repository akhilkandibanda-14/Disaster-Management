import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))
from app.api.prediction import predict_integrated
from app.schemas.prediction import IntegratedPredictionRequest
from datetime import date
from fastapi import HTTPException

print("==================================================")
print("HYDERABAD TEST (UNSUPPORTED)")
print("==================================================")
hyd_req = IntegratedPredictionRequest(
    latitude=17.3850,
    longitude=78.4867,
    target_date=date(2023, 8, 1)
)

try:
    hyd_res = predict_integrated(hyd_req)
    print(f"Status Code: 200")
    print(f"Prediction Available: {hyd_res.prediction_available}")
    print(f"Coverage Status: {hyd_res.coverage.status}")
    print(f"Gauge Distance: {hyd_res.coverage.distance_km} km")
    print(f"Message: {hyd_res.message}")
    print(f"Prediction: {hyd_res.prediction}")
except HTTPException as e:
    print(f"Error {e.status_code}: {e.detail}")
except Exception as e:
    print(f"Failed to call API: {e}")

print("\n==================================================")
print("SUPPORTED GAUGE TEST")
print("==================================================")
# INDOFLOODS-gauge-394
gauge_req = IntegratedPredictionRequest(
    latitude=12.18,
    longitude=77.73,
    target_date=date(2023, 8, 1)
)

try:
    g_res = predict_integrated(gauge_req)
    print(f"Status Code: 200")
    print(f"Prediction Available: {g_res.prediction_available}")
    print(f"Coverage Status: {g_res.coverage.status}")
    print(f"Reference Gauge: {g_res.coverage.reference_gauge}")
    print(f"Gauge Distance: {g_res.coverage.distance_km} km")
    print(f"Prediction: {g_res.prediction}")
    print(f"Risk Level: {g_res.risk_level}")
except HTTPException as e:
    print(f"Error {e.status_code}: {e.detail}")
except Exception as e:
    print(f"Failed to call API: {e}")
