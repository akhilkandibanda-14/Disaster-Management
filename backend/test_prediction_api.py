from fastapi.testclient import TestClient
import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
import joblib

from app.main import app
from app.services.integration import IntegrationService, ValidationError
from app.schemas.rainfall import AntecedentRainfallResponse
import app.api.prediction as pred_module

client = TestClient(app)

@pytest.fixture
def mock_rainfall_response():
    return AntecedentRainfallResponse(
        latitude=12.18,
        longitude=77.73,
        target_date=date(2023, 8, 1),
        T1d=10.0, T2d=15.0, T3d=0.0, T4d=5.0, T5d=20.0,
        T6d=2.0, T7d=1.0, T8d=0.0, T9d=0.0, T10d=0.0,
        daily_rainfall_values={}
    )

@patch('app.services.integration.calculate_antecedent_rainfall')
def test_supported_gauge_prediction(mock_calc_rain, mock_rainfall_response):
    # Tests 1, 7, 8, 9, 10
    mock_calc_rain.return_value = mock_rainfall_response
    
    pred_module.integration_service = IntegrationService(data_dir="data/raw/indofloods")
    
    # INDOFLOODS-gauge-394
    response = client.post("/api/v1/predict/integrated", json={
        "latitude": 12.18,
        "longitude": 77.73,
        "target_date": "2023-08-01"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["prediction_available"] is True
    assert data["coverage"]["status"] == "MODEL_SUPPORTED"
    assert "reference_gauge" in data["coverage"]
    assert data["coverage"]["distance_km"] < 50.0
    assert data["prediction"] is not None
    assert "failure_probability" in data
    assert data["data_sources"]["environmental"] == "INDOFLOODS"

def test_unsupported_hyderabad_prediction():
    # Tests 2, 4, 5, 6, 7
    pred_module.integration_service = IntegrationService(data_dir="data/raw/indofloods")
    
    response = client.post("/api/v1/predict/integrated", json={
        "latitude": 17.3850,
        "longitude": 78.4867,
        "target_date": "2023-08-01"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["prediction_available"] is False
    assert data["coverage"]["status"] == "MODEL_UNSUPPORTED"
    assert data["coverage"]["distance_km"] > 50.0
    assert data["prediction"] is None
    assert data["failure_probability"] is None
    assert data["risk_level"] is None
    assert "does not provide validated coverage" in data["message"]
    
def test_gauge_far_out_of_coverage():
    # Test 4
    response = client.post("/api/v1/predict/integrated", json={
        "latitude": 0.0,
        "longitude": 0.0,
        "target_date": "2023-08-01"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["prediction_available"] is False
    assert data["coverage"]["status"] == "MODEL_UNSUPPORTED"
    assert data["coverage"]["distance_km"] > 50.0
    assert data["prediction"] is None


def test_invalid_target_date():
    future_date = (date.today() + timedelta(days=5)).isoformat()
    response = client.post("/api/v1/predict/integrated", json={
        "latitude": 12.18,
        "longitude": 77.73, # Supported location to pass coverage check
        "target_date": future_date
    })
    assert response.status_code == 400
    assert "Failed to fetch rainfall data" in response.json()["detail"]


@patch('app.services.integration.calculate_antecedent_rainfall')
def test_open_meteo_failure(mock_calc_rain):
    mock_calc_rain.side_effect = Exception("Open-Meteo down")
    
    response = client.post("/api/v1/predict/integrated", json={
        "latitude": 12.18,
        "longitude": 77.73,
        "target_date": "2023-08-01"
    })
    assert response.status_code == 400
    assert "Failed to fetch rainfall data" in response.json()["detail"]

@patch('app.api.prediction.IntegrationService')
def test_model_artifact_unavailable(mock_integration_service):
    mock_integration_service.side_effect = Exception("File not found")
    pred_module.integration_service = None # Reset
    
    response = client.post("/api/v1/predict/integrated", json={
        "latitude": 18.995,
        "longitude": 81.332,
        "target_date": "2023-08-01"
    })
    assert response.status_code == 503
    assert "Failed to load integration service or model artifact" in response.json()["detail"]

