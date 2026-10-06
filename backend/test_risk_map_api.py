import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch
import joblib

client = TestClient(app)

def test_risk_map_supported_gauge():
    # Use Gauge 394 (lat=12.18, lon=77.73)
    response = client.get("/risk-map?latitude=12.18&longitude=77.73")
    assert response.status_code == 200
    data = response.json()
    assert data["prediction_available"] is True
    assert data["coverage_status"] == "MODEL_SUPPORTED"
    assert data["distance_km"] < 50
    assert data["predicted_class"] in [0, 1]
    assert data["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
    assert "data_sources" in data

def test_risk_map_hyderabad_unsupported():
    # Hyderabad is unsupported
    response = client.get("/risk-map?latitude=17.3850&longitude=78.4867")
    assert response.status_code == 200
    data = response.json()
    assert data["prediction_available"] is False
    assert data["coverage_status"] == "MODEL_UNSUPPORTED"
    assert data["distance_km"] > 50
    assert data["predicted_class"] is None
    assert data["risk_level"] is None

def test_risk_map_far_away_location():
    # Far away
    response = client.get("/risk-map?latitude=40.7128&longitude=-74.0060")
    assert response.status_code == 200
    data = response.json()
    assert data["prediction_available"] is False
    assert data["coverage_status"] == "MODEL_UNSUPPORTED"

def test_risk_map_invalid_coordinates():
    # Invalid string
    response = client.get("/risk-map?latitude=invalid&longitude=78.4867")
    assert response.status_code == 422

def test_determinism():
    # Repeat calls give the same output
    response1 = client.get("/risk-map?latitude=12.18&longitude=77.73")
    response2 = client.get("/risk-map?latitude=12.18&longitude=77.73")
    json1 = response1.json()
    json2 = response2.json()
    json1.pop('timestamp', None)
    json2.pop('timestamp', None)
    assert json1 == json2

def test_hydrology_independence():
    # Ensure hydrology is NOT called
    with patch('app.services.hydrology.DemoHydrologyProvider.get_water_level') as mock_hydrology:
        response = client.get("/risk-map?latitude=12.18&longitude=77.73")
        assert response.status_code == 200
        mock_hydrology.assert_not_called()

def test_ml_contract_118_features():
    # Verify the model exactly uses 118 raw features
    pipe = joblib.load('ml/models/flood_severity_model.joblib')
    num_cols = list(pipe.named_steps['preprocessor'].transformers_[0][2])
    cat_cols = list(pipe.named_steps['preprocessor'].transformers_[1][2])
    total_raw_features = len(num_cols) + len(cat_cols)
    assert total_raw_features == 118

def test_get_gauges():
    response = client.get("/risk-map/gauges")
    assert response.status_code == 200
    data = response.json()
    assert "gauges" in data
    assert len(data["gauges"]) > 0
