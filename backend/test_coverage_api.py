import pytest
from datetime import date
from unittest.mock import patch

import app.api.prediction as pred_module
from app.services.integration import IntegrationService
from app.api.prediction import predict_integrated
from app.schemas.prediction import IntegratedPredictionRequest

pred_module.integration_service = IntegrationService(data_dir="data/raw/indofloods")

from app.services.gauge_reference import GaugeReferenceService
from app.schemas.gauge import NearestGaugeResponse, ReferenceGauge, Coordinates

# Mock GaugeReferenceService to test specific distances and threshold behaviors
@pytest.fixture
def mock_gauge_service():
    with patch('app.api.prediction.integration_service.gauge_service.get_nearest_gauge') as mock_get:
        yield mock_get

def test_supported_gauge_coordinate():
    req = IntegratedPredictionRequest(
        latitude=12.18,
        longitude=77.73,
        target_date=date(2023, 8, 1)
    )
    res = predict_integrated(req)
    assert res.prediction_available is True
    assert res.coverage_status == "MODEL_SUPPORTED"
    assert res.coverage.status == "MODEL_SUPPORTED"
    assert res.prediction is not None
    assert res.nearest_gauge is not None
    assert res.gauge_distance_km is not None
    assert res.gauge_distance_km <= 50.0
    
def test_unsupported_hyderabad_coordinate():
    req = IntegratedPredictionRequest(
        latitude=17.3850,
        longitude=78.4867,
        target_date=date(2023, 8, 1)
    )
    # Ensure build_feature_vector (which calls the model) is NOT called
    with patch('app.api.prediction.IntegrationService.build_feature_vector') as mock_build:
        res = predict_integrated(req)
        mock_build.assert_not_called()
        
    assert res.prediction_available is False
    assert res.prediction is None
    assert res.risk_level is None
    assert res.coverage_status == "MODEL_UNSUPPORTED"
    assert res.coverage.status == "MODEL_UNSUPPORTED"
    assert res.gauge_distance_km > 50.0

@patch('app.api.prediction.integration_service.gauge_service.get_nearest_gauge')
def test_distance_exactly_at_threshold(mock_get_nearest_gauge):
    # Mocking distance exactly at 50.0
    mock_get_nearest_gauge.return_value = NearestGaugeResponse(
        user_location=Coordinates(latitude=12.0, longitude=77.0),
        reference_gauge=ReferenceGauge(gauge_id="TEST-GAUGE-1", latitude=12.0, longitude=77.0),
        distance_km=50.0,
        max_allowed_distance_km=50.0,
        within_model_coverage=True,
        message="Exact threshold",
        gauge_features={'foo': 1}
    )
    
    req = IntegratedPredictionRequest(latitude=12.0, longitude=77.0, target_date=date(2023, 8, 1))
    
    with patch('app.api.prediction.IntegrationService.build_feature_vector') as mock_build:
        # We mock build_feature_vector to avoid needing the full rainfall / dummy features
        mock_build.side_effect = Exception("Stop early, we just want to verify coverage status")
        try:
            predict_integrated(req)
        except Exception:
            pass
        
        # If it reached build_feature_vector, it passed the coverage check
        mock_build.assert_called_once()


@patch('app.api.prediction.integration_service.gauge_service.get_nearest_gauge')
def test_distance_greater_than_50(mock_get_nearest_gauge):
    mock_get_nearest_gauge.return_value = NearestGaugeResponse(
        user_location=Coordinates(latitude=12.0, longitude=77.0),
        reference_gauge=ReferenceGauge(gauge_id="TEST-GAUGE-2", latitude=12.0, longitude=77.0),
        distance_km=50.1,
        max_allowed_distance_km=50.0,
        within_model_coverage=False,
        message="Out of bounds"
    )
    
    req = IntegratedPredictionRequest(latitude=12.0, longitude=77.0, target_date=date(2023, 8, 1))
    
    res = predict_integrated(req)
    assert res.prediction_available is False
    assert res.coverage_status == "MODEL_UNSUPPORTED"
    assert res.prediction is None
    assert res.gauge_distance_km == 50.1
