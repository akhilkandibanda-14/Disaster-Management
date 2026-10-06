import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch
import pandas as pd

client = TestClient(app)

def test_shelters_all_returns_dataset():
    response = client.get("/shelters")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 11
    assert len(data["shelters"]) == 11

def test_shelter_ids_and_coordinates():
    response = client.get("/shelters")
    shelters = response.json()["shelters"]
    ids = [s["shelter_id"] for s in shelters]
    assert "HYD-S-001" in ids
    
    hyd_001 = next(s for s in shelters if s["shelter_id"] == "HYD-S-001")
    assert hyd_001["latitude"] == 17.4445
    assert hyd_001["longitude"] == 78.463

def test_missing_values_preserved():
    response = client.get("/shelters")
    shelters = response.json()["shelters"]
    hyd_001 = next(s for s in shelters if s["shelter_id"] == "HYD-S-001")
    assert hyd_001["address"] is None
    assert hyd_001["district"] is None
    assert hyd_001["capacity"] is None
    assert hyd_001["current_occupancy"] is None
    assert hyd_001["contact"] is None

def test_public_unverified_preserved():
    response = client.get("/shelters")
    shelters = response.json()["shelters"]
    for s in shelters:
        assert s["data_status"] == "PUBLIC_UNVERIFIED"

def test_source_and_verification_note_preserved():
    response = client.get("/shelters")
    shelters = response.json()["shelters"]
    for s in shelters:
        assert "must be verified with GHMC" in s["source"]
        assert "Not confirmed as an emergency flood shelter" in s["verification_note"]

def test_valid_lat_lon():
    response = client.get("/shelters?latitude=17.3850&longitude=78.4867")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 11
    # Distances should be populated
    assert all("distance_km" in s and s["distance_km"] is not None for s in data["shelters"])
    
    # Should be sorted by distance
    distances = [s["distance_km"] for s in data["shelters"]]
    assert distances == sorted(distances)

def test_invalid_lat():
    response = client.get("/shelters?latitude=100&longitude=78.4867")
    assert response.status_code == 422

def test_invalid_lon():
    response = client.get("/shelters?latitude=17.3850&longitude=-200")
    assert response.status_code == 422

def test_invalid_radius():
    response = client.get("/shelters?latitude=17.3850&longitude=78.4867&radius_km=-5")
    assert response.status_code == 422

def test_radius_without_coords():
    response = client.get("/shelters?radius_km=10")
    assert response.status_code == 400

def test_radius_filtering():
    # Find one within a small radius
    response = client.get("/shelters?latitude=17.4445&longitude=78.4630&radius_km=1.0")
    assert response.status_code == 200
    data = response.json()
    # At least HYD-S-001 should be found, distance 0
    assert data["total"] >= 1
    assert any(s["shelter_id"] == "HYD-S-001" for s in data["shelters"])
    
    # Verify all returned shelters are within radius
    assert all(s["distance_km"] <= 1.0 for s in data["shelters"])

def test_determinism():
    r1 = client.get("/shelters?latitude=17.3850&longitude=78.4867")
    r2 = client.get("/shelters?latitude=17.3850&longitude=78.4867")
    assert r1.json() == r2.json()

def test_ml_not_called():
    with patch('app.services.risk_map.RiskMapService.get_risk_for_location') as mock_ml:
        client.get("/shelters?latitude=17.3850&longitude=78.4867")
        mock_ml.assert_not_called()

def test_hydrology_not_called():
    with patch('app.services.hydrology.DemoHydrologyProvider.get_water_level') as mock_hydro:
        client.get("/shelters?latitude=17.3850&longitude=78.4867")
        mock_hydro.assert_not_called()
