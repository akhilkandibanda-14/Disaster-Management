import pytest
from app.services.gauge_reference import GaugeReferenceService
import pandas as pd
import numpy as np
import tempfile
import os

@pytest.fixture
def temp_data_dir():
    with tempfile.TemporaryDirectory() as d:
        # Create mock catchment characteristics
        catchment_data = {
            'GaugeID': ['INDOFLOODS-gauge-1013', 'INDOFLOODS-gauge-2000', 'INDOFLOODS-gauge-3000'],
            'Drainage Area': [3542.1, 1000.0, 500.0],
            'Annual Mean Temperature': [22.2, 25.0, 20.0]
        }
        pd.DataFrame(catchment_data).to_csv(os.path.join(d, 'catchment_characteristics_indofloods.csv'), index=False)
        
        # Create mock gauge coordinates (Hyderabad is 1013)
        coords_data = {
            'GaugeID': ['INDOFLOODS-gauge-1013', 'INDOFLOODS-gauge-2000', 'INDOFLOODS-gauge-3000'],
            'Latitude': [17.3850, 28.7041, 12.9716], # Hyderabad, Delhi, Bangalore
            'Longitude': [78.4867, 77.1025, 77.5946]
        }
        pd.DataFrame(coords_data).to_csv(os.path.join(d, 'gauge_coordinates.csv'), index=False)
        
        yield d

@pytest.fixture
def gauge_service(temp_data_dir):
    return GaugeReferenceService(data_dir=temp_data_dir)

def test_nearest_gauge_selection(gauge_service):
    # Test near Delhi
    resp = gauge_service.get_nearest_gauge(latitude=28.7, longitude=77.1, max_dist_km=50)
    assert resp.within_model_coverage is True
    assert resp.reference_gauge.gauge_id == 'INDOFLOODS-gauge-2000'

def test_correct_distance_calculation(gauge_service):
    # Distance from 17.3850, 78.4867 to itself should be 0
    resp = gauge_service.get_nearest_gauge(latitude=17.3850, longitude=78.4867, max_dist_km=50)
    assert resp.distance_km == 0.0

def test_gauge_feature_retrieval(gauge_service):
    resp = gauge_service.get_nearest_gauge(latitude=17.3850, longitude=78.4867, max_dist_km=50)
    assert resp.gauge_features is not None
    assert resp.gauge_features['Drainage Area'] == 3542.1
    assert resp.gauge_features['Annual Mean Temperature'] == 22.2
    
def test_hyderabad_lookup(gauge_service):
    resp = gauge_service.get_nearest_gauge(latitude=17.3850, longitude=78.4867, max_dist_km=50)
    assert resp.reference_gauge.gauge_id == 'INDOFLOODS-gauge-1013'
    assert resp.within_model_coverage is True
    
def test_distant_location_rejection(gauge_service):
    # Somewhere in ocean far from any gauge
    resp = gauge_service.get_nearest_gauge(latitude=0.0, longitude=0.0, max_dist_km=50)
    assert resp.within_model_coverage is False
    assert resp.message == "Location is outside the geographic coverage of the current INDOFLOODS gauge model."
    assert resp.distance_km > 50.0

def test_empty_gauge_reference_data():
    with tempfile.TemporaryDirectory() as empty_dir:
        svc = GaugeReferenceService(data_dir=empty_dir)
        resp = svc.get_nearest_gauge(17.385, 78.486)
        assert resp.within_model_coverage is False
        assert resp.message == "Gauge reference data is missing or empty."

def test_missing_gauge_coordinates(temp_data_dir):
    # Delete the coords file
    os.remove(os.path.join(temp_data_dir, 'gauge_coordinates.csv'))
    svc = GaugeReferenceService(data_dir=temp_data_dir)
    resp = svc.get_nearest_gauge(17.385, 78.486)
    assert resp.within_model_coverage is False
    assert "missing" in resp.message

def test_duplicate_gauge_ids(temp_data_dir):
    # Overwrite with duplicate gauge IDs
    coords_data = {
        'GaugeID': ['INDOFLOODS-gauge-1013', 'INDOFLOODS-gauge-1013'],
        'Latitude': [17.3850, 20.0],
        'Longitude': [78.4867, 80.0]
    }
    pd.DataFrame(coords_data).to_csv(os.path.join(temp_data_dir, 'gauge_coordinates.csv'), index=False)
    
    catchment_data = {
        'GaugeID': ['INDOFLOODS-gauge-1013', 'INDOFLOODS-gauge-1013'],
        'Drainage Area': [3542.1, 1000.0]
    }
    pd.DataFrame(catchment_data).to_csv(os.path.join(temp_data_dir, 'catchment_characteristics_indofloods.csv'), index=False)
    
    svc = GaugeReferenceService(data_dir=temp_data_dir)
    resp = svc.get_nearest_gauge(17.385, 78.486)
    assert resp.within_model_coverage is True
    assert resp.reference_gauge.gauge_id == 'INDOFLOODS-gauge-1013'

def test_invalid_latitude_longitude(gauge_service):
    # Usually pydantic validates this on the endpoint, but testing the service directly 
    # with extreme values just evaluates haversine
    resp = gauge_service.get_nearest_gauge(latitude=999, longitude=999) # math.radians will just process it, but might not make sense geographically
    assert resp.within_model_coverage is False

