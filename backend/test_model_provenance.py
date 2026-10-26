"""
Unit and Integration Tests for Milestone 5:
Data Provenance, Source Semantics, Model-Readiness Evaluation, and Geographic Guards.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.hazard import HazardService, get_hazard_service
from app.services.risk_map import RiskMapService, get_risk_map_service
from app.schemas.hazard import HazardRecord
from evaluate_model_readiness import run_model_readiness_evaluation

client = TestClient(app)


def test_source_and_observation_provenance():
    """Verify distinct source_type categorization across hazard types."""
    service = HazardService()
    hazards = service.get_hazards(include_demo=True, include_authoritative=False)
    
    # 1. Municipal survey flood zones must be HISTORICAL_VULNERABILITY + PUBLIC_UNVERIFIED
    vuln_hazards = [h for h in hazards if h.source_type == "HISTORICAL_VULNERABILITY"]
    assert len(vuln_hazards) >= 4
    for h in vuln_hazards:
        assert h.data_status == "PUBLIC_UNVERIFIED"
        assert h.geometry is not None
        assert "survey" in h.geographic_uncertainty.lower() or "municipal" in h.geographic_uncertainty.lower()

    # 2. Simulated Demo hazards must be DEMO
    demo_hazards = [h for h in hazards if h.source_type == "DEMO"]
    assert len(demo_hazards) >= 1
    for h in demo_hazards:
        assert h.data_status == "DEMO"
        assert "[DEMO]" in h.title


def test_forecast_vs_observation_classification():
    """Verify that GloFAS river discharge is classified as MODEL_FORECAST with UNKNOWN severity."""
    service = HazardService()
    
    # Mock GloFAS response
    mock_payload = {
        "latitude": 17.375,
        "longitude": 78.475,
        "daily": {
            "time": ["2026-10-24"],
            "river_discharge": [42.8]
        }
    }
    
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_payload
        
        glofas_hazards = service.fetch_glofas_hydrology(latitude=17.385, longitude=78.486)
        
        assert len(glofas_hazards) == 1
        h = glofas_hazards[0]
        assert h.source_type == "MODEL_FORECAST"
        assert h.data_status == "AUTHORITATIVE"
        # Must NOT convert discharge into arbitrary HIGH/EXTREME without local calibration
        assert h.severity == "UNKNOWN"
        assert h.measurement_unit == "m³/s"
        assert h.raw_value == 42.8
        assert h.forecast_date == "2026-10-24"
        assert h.requested_coordinates == (17.385, 78.486)
        assert h.returned_coordinates == (17.375, 78.475)
        assert "Musi River" in h.catchment_context
        assert "uncalibrated" in h.geographic_uncertainty.lower()


def test_ndma_sachet_no_invented_polygons_and_uncertainty():
    """Verify NDMA SACHET does not invent spatial polygons for district text advisories."""
    service = HazardService()
    
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>NDMA Sachet Telangana Alerts</title>
        <item>
          <title>Heavy to Very Heavy Rain Warning for Hyderabad District</title>
          <link>https://sachet.ndma.gov.in/cap_public_website/alertDetails?identifier=TG20261023001</link>
          <pubDate>Fri, 23 Oct 2026 15:30:00 +0530</pubDate>
          <description>Isolated heavy rainfall likely across Hyderabad.</description>
        </item>
      </channel>
    </rss>"""
    
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = sample_xml.encode("utf-8")
        
        alerts = service.fetch_ndma_sachet_alerts()
        assert len(alerts) == 1
        a = alerts[0]
        assert a.source_type == "OFFICIAL_ALERT"
        assert a.data_status == "AUTHORITATIVE"
        assert a.geometry is None  # Strict constraint: do not invent polygon boundaries
        assert a.administrative_area == "Telangana State / Hyderabad District"
        assert "district-level" in a.geographic_uncertainty.lower()


def test_unverified_municipal_polygon_source():
    """Verify hyderabad_flood_zones.geojson retains unverified classification."""
    service = HazardService()
    records = service.cached_public_hazards
    assert len(records) > 0
    for r in records:
        assert r.data_status == "PUBLIC_UNVERIFIED"
        assert r.source_type == "HISTORICAL_VULNERABILITY"
        assert "sensor" in r.geographic_uncertainty.lower() or "indicative" in r.geographic_uncertainty.lower()


def test_geographic_coverage_guard_and_insufficient_local_data():
    """Verify 50km coverage guard blocks Hyderabad and marks INSUFFICIENT_LOCAL_DATA."""
    response = client.get("/risk-map?latitude=17.3850&longitude=78.4867")
    assert response.status_code == 200
    data = response.json()
    
    assert data["prediction_available"] is False
    assert data["coverage_status"] == "MODEL_UNSUPPORTED"
    assert data["data_readiness_status"] == "INSUFFICIENT_LOCAL_DATA"
    assert data["distance_km"] > 50.0
    assert data["nearest_gauge_distance_km"] == data["distance_km"]
    assert data["coverage_limit_km"] == 50.0
    assert data["gauges_within_50km_count"] == 0
    assert data["catchment_gauges_count"] == 0
    assert "exceeding the 50.0 km" in data["provenance_note"]
    assert "Application Operational" in data["provenance_note"]
    assert "not a software crash" in data["provenance_note"]
    assert "does NOT indicate safety" in data["safety_disclaimer"]
    assert "not a confirmed low-risk result" in data["safety_disclaimer"]


def test_supported_gauge_model_readiness():
    """Verify supported gauge coordinates return SUPPORTED readiness and model predictions."""
    response = client.get("/risk-map?latitude=12.18&longitude=77.73")
    assert response.status_code == 200
    data = response.json()
    
    assert data["prediction_available"] is True
    assert data["coverage_status"] == "MODEL_SUPPORTED"
    assert data["data_readiness_status"] == "SUPPORTED"
    assert data["distance_km"] < 50.0
    assert data["gauges_within_50km_count"] == 3
    assert data["catchment_gauges_count"] == 3
    assert data["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
    assert "INDOFLOODS" in data["provenance_note"]
    assert data["safety_disclaimer"] is not None


def test_catchment_gauges_count_computed_dynamically_from_dataset():
    """Verify gauges_within_50km_count is computed from INDOFLOODS dataset, not a hardcoded default."""
    from app.services.gauge_reference import GaugeReferenceService
    svc = GaugeReferenceService()
    
    # Hyderabad coordinates have exactly 0 INDOFLOODS gauges within 50 km
    hyd_count = svc.count_gauges_within_radius(17.3850, 78.4860, radius_km=50.0)
    assert hyd_count == 0
    assert svc.count_gauges_in_catchment(17.3850, 78.4860, radius_km=50.0) == 0
    
    # Near Gauge 394 (12.18, 77.73) there are 3 gauges within 50 km
    supported_count = svc.count_gauges_within_radius(12.18, 77.73, radius_km=50.0)
    assert supported_count == 3
    assert svc.count_gauges_in_catchment(12.18, 77.73, radius_km=50.0) == 3
    
    # Via HTTP API endpoint
    resp_hyd = client.get("/risk-map?latitude=17.3850&longitude=78.4867")
    assert resp_hyd.status_code == 200
    assert resp_hyd.json()["gauges_within_50km_count"] == 0
    assert resp_hyd.json()["catchment_gauges_count"] == 0
    
    resp_supp = client.get("/risk-map?latitude=12.18&longitude=77.73")
    assert resp_supp.status_code == 200
    assert resp_supp.json()["gauges_within_50km_count"] == 3
    assert resp_supp.json()["catchment_gauges_count"] == 3


def test_missing_data_returns_data_unavailable():
    """Verify that when environmental data retrieval fails inside coverage, DATA_UNAVAILABLE is returned."""
    risk_service = RiskMapService()
    
    # Simulate feature vector building failure
    with patch.object(risk_service.integration_service, "build_feature_vector", side_effect=RuntimeError("Weather API timeout")):
        resp = risk_service.get_risk_for_location(12.18, 77.73)
        assert resp.prediction_available is False
        assert resp.coverage_status == "MODEL_SUPPORTED"
        assert resp.data_readiness_status == "DATA_UNAVAILABLE"
        assert "could not be retrieved" in resp.provenance_note
        assert "does NOT indicate that the location is safe" in resp.safety_disclaimer


def test_reproducible_gauge_grouped_evaluation():
    """Verify reproducible evaluation script runs and produces documented metrics."""
    base_dir = Path(__file__).resolve().parents[1]
    results = run_model_readiness_evaluation(base_dir)
    
    assert results["dataset_samples"] == 4548
    assert results["class_balance"]["severe_1"] > 1000
    assert results["leakage_analysis"]["gauge_leakage_overlap"] == 0
    # Grouped split prevents leakage, showing significant gap
    assert results["leakage_analysis"]["leakage_gap_f1"] > 0.05
    assert results["hyderabad_geographic_audit"]["is_supported"] is False
    assert results["hyderabad_geographic_audit"]["local_data_status"] == "INSUFFICIENT_LOCAL_DATA"
    assert results["hyderabad_geographic_audit"]["nearest_gauge_distance_km"] > 50.0
    
    report_file = base_dir / "docs" / "model_readiness_report.md"
    assert report_file.exists()


def test_safety_guard_invariant_across_multiple_hyderabad_points():
    """Verify safety guard consistently suppresses predictions across Greater Hyderabad."""
    hyderabad_points = [
        ("Begumpet", 17.442, 78.475),
        ("Charminar", 17.3616, 78.4747),
        ("Hitec City", 17.4435, 78.3772),
        ("Uppal / Musi", 17.4022, 78.5601),
        ("Secunderabad", 17.4399, 78.4983),
    ]
    
    for name, lat, lon in hyderabad_points:
        response = client.get(f"/risk-map?latitude={lat}&longitude={lon}")
        assert response.status_code == 200, f"Failed for {name}"
        data = response.json()
        assert data["prediction_available"] is False, f"Model predicted for {name}!"
        assert data["coverage_status"] == "MODEL_UNSUPPORTED"
        assert data["data_readiness_status"] == "INSUFFICIENT_LOCAL_DATA"
        assert data["distance_km"] > 50.0
