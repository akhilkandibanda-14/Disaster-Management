import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.hydrology import get_hydrology_provider, DemoHydrologyProvider

client = TestClient(app)

def test_hydrology_endpoint_demo_station_retrieval():
    # Test valid retrieval for Hyderabad demo station
    response = client.get("/hydrology/water-level?latitude=17.3850&longitude=78.4867")
    assert response.status_code == 200
    data = response.json()
    
    assert data["station_id"] == "DEMO-HYD-001"
    assert "DEMO REFERENCE STATION" in data["station_name"]
    assert data["data_status"] == "DEMO"
    assert data["data_source"] == "SafeMap AI Demo Hydrological Dataset"
    assert data["water_level_unit"] == "m"
    assert data["discharge_unit"] == "m3/s"
    assert "timestamp" in data

def test_deterministic_repeated_response():
    response1 = client.get("/hydrology/water-level?latitude=17.3850&longitude=78.4867")
    response2 = client.get("/hydrology/water-level?latitude=17.3850&longitude=78.4867")
    
    data1 = response1.json()
    data2 = response2.json()
    
    assert data1["station_id"] == data2["station_id"]
    assert data1["water_level"] == data2["water_level"]
    assert data1["discharge"] == data2["discharge"]

def test_invalid_coordinates_missing_station():
    # Coords far away from any demo station (e.g. New York)
    response = client.get("/hydrology/water-level?latitude=40.7128&longitude=-74.0060")
    assert response.status_code == 404
    assert "No hydrological station found" in response.json()["detail"]

def test_water_level_not_in_ml_features():
    # Confirm that water_level is NOT part of the 118 features expected by the model
    # We load the pipeline directly to verify
    import joblib
    pipe = joblib.load('ml/models/flood_severity_model.joblib')
    num_cols = list(pipe.named_steps['preprocessor'].transformers_[0][2])
    cat_cols = list(pipe.named_steps['preprocessor'].transformers_[1][2])
    all_cols = num_cols + cat_cols
    assert "water_level" not in all_cols
    assert len(all_cols) == 118

from unittest.mock import patch

def test_predict_integrated_does_not_call_hydrology():
    # Mock the hydrology provider to ensure it's not called during prediction
    with patch('app.services.hydrology.DemoHydrologyProvider.get_water_level') as mock_get_water_level:
        # We send a valid request to predict/integrated to check if it calls hydrology
        request_data = {
            "latitude": 17.3850,
            "longitude": 78.4867,
            "location_name": "Hyderabad",
            "rainfall": 10.0,
            "temperature": 30.0,
            "humidity": 60.0,
            "water_level": 508.5 # Even if water_level is in the request body schema, it shouldn't trigger hydrology service
        }
        response = client.post("/predict/integrated", json=request_data)
        
        mock_get_water_level.assert_not_called()
