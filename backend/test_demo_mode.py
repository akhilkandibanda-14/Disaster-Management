import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_demo_hazard_feed_labelling():
    """Verify DEMO-HAZ-001 is explicitly labeled as demo/simulated data in the hazard feed."""
    response = client.get("/flood-hazards")
    assert response.status_code == 200
    data = response.json()
    assert "hazards" in data
    hazards = data["hazards"]
    
    demo_hazards = [h for h in hazards if h.get("hazard_id") == "DEMO-HAZ-001"]
    assert len(demo_hazards) == 1, "DEMO-HAZ-001 must exist in the hazards feed"
    demo_h = demo_hazards[0]
    
    assert demo_h.get("source_type") == "DEMO"
    assert demo_h.get("data_status") == "DEMO"
    assert "[DEMO]" in demo_h.get("title", "")
    assert "[DEMO]" in demo_h.get("description", "")
    assert "[DEMO]" in demo_h.get("verification_note", "")


def test_demo_musi_causeway_hazard_intersection():
    """Verify simulated flood demo location at Musi River Causeway correctly intersects HYD-FZ-001."""
    musi_lat, musi_lon = 17.3820, 78.4910
    response = client.get(f"/flood-hazards/check-location?latitude={musi_lat}&longitude={musi_lon}")
    assert response.status_code == 200
    data = response.json()
    
    assert data.get("is_in_hazard_zone") is True
    assert data.get("highest_severity") == "HIGH"
    assert data.get("hazard_count") >= 1
    
    intersected_ids = [h.get("hazard_id") for h in data.get("intersected_hazards", [])]
    assert "HYD-FZ-001" in intersected_ids


def test_demo_begumpet_hazard_intersection():
    """Verify simulated flash flood demo location at Begumpet corridor intersects DEMO-HAZ-001."""
    begumpet_lat, begumpet_lon = 17.4420, 78.4750
    response = client.get(f"/flood-hazards/check-location?latitude={begumpet_lat}&longitude={begumpet_lon}")
    assert response.status_code == 200
    data = response.json()
    
    assert data.get("is_in_hazard_zone") is True
    assert data.get("highest_severity") == "HIGH"
    
    intersected_ids = [h.get("hazard_id") for h in data.get("intersected_hazards", [])]
    assert "DEMO-HAZ-001" in intersected_ids


def test_demo_evacuation_routing_workflow():
    """Verify existing evacuation-route endpoint demonstrates workflow honestly from demo location."""
    payload = {
        "origin": {"latitude": 17.3820, "longitude": 78.4910},
        "destination": {"latitude": 17.416844, "longitude": 78.464475},
        "compute_alternatives": True
    }
    response = client.post("/evacuation-route", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "route_status" in data
    assert data["route_status"] in ["ROUTE_AVAILABLE", "NO_SAFE_ROUTE"]
    
    if data["route_status"] == "ROUTE_AVAILABLE":
        assert len(data.get("geometry", [])) > 0
        assert data.get("route_distance_km") is not None
        # Origin intersects active flood zone, so warning must be honest
        warnings = data.get("warnings", [])
        assert any("active flood hazard zone" in w for w in warnings)
    else:
        # If no safe route, verify it doesn't manufacture geometry
        assert len(data.get("geometry", [])) == 0


def test_protection_against_accidental_sos():
    """Verify demo mode operations cannot trigger, create, or call real SOS emergency actions."""
    # 1. Health check reports demo mode without side effects
    health_res = client.get("/health")
    assert health_res.status_code == 200
    
    # 2. Hazard check and routing never create incidents or SOS alerts
    incidents_before = client.get("/incidents").json().get("incidents", [])
    
    # Run demo checks
    client.get("/flood-hazards/check-location?latitude=17.3820&longitude=78.4910")
    client.post("/evacuation-route", json={
        "origin": {"latitude": 17.3820, "longitude": 78.4910},
        "destination": {"latitude": 17.416844, "longitude": 78.464475}
    })
    
    incidents_after = client.get("/incidents").json().get("incidents", [])
    assert len(incidents_before) == len(incidents_after), "Demo operations must not submit public incidents"
    
    # 3. Verify public incident creation requires explicit citizen input and cannot be submitted empty
    incident_empty_res = client.post("/incidents", json={})
    assert incident_empty_res.status_code in [400, 422], "Incidents must require validation"


def test_official_alerts_vs_indicative_zones_distinction():
    """Verify official active alerts are strictly separated from indicative flood-prone zones."""
    official_alerts_res = client.get("/disaster-alerts")
    assert official_alerts_res.status_code == 200
    alerts = official_alerts_res.json()
    assert isinstance(alerts, list)
    
    # Official alerts have official IDs and severity
    for alert in alerts:
        assert "id" in alert or "alert_id" in alert
        assert "severity" in alert
    
    # Indicative zones are served separately from /flood-hazards
    hazard_res = client.get("/flood-hazards")
    assert hazard_res.status_code == 200
    hazards = hazard_res.json().get("hazards", [])
    
    # Provenance metadata distinguishes official government active alerts from historical surveys
    source_types = {h.get("source_type") for h in hazards}
    assert "HISTORICAL_VULNERABILITY" in source_types or "DEMO" in source_types


def test_simulated_weather_is_marked_demo():
    """Verify simulated weather data explicitly indicates demo source."""
    weather_res = client.get("/weather?latitude=17.3820&longitude=78.4910")
    assert weather_res.status_code == 200
    weather = weather_res.json()
    
    assert weather.get("source") == "DEMO / SIMULATED DATA"
    assert "Simulated" in weather.get("warning", "")
