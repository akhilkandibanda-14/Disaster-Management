import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.resources import RoadConditionResponse
from app.services.routing import build_graph_route
from app.services.emergency_facility import get_emergency_facility_service
from datetime import datetime, timezone

client = TestClient(app)


def test_emergency_facilities_endpoint_returns_data():
    """Verify that GET /emergency-facilities returns a structured list of emergency facilities."""
    response = client.get("/emergency-facilities")
    assert response.status_code == 200
    data = response.json()
    assert "facilities" in data
    assert "total" in data
    assert data["total"] > 0
    assert len(data["facilities"]) == data["total"]
    assert "data_disclaimer" in data


def test_hospitals_records_and_coordinates():
    """Verify authentic Hyderabad hospital records (Osmania, Gandhi, NIMS) with accurate coordinates."""
    response = client.get("/emergency-facilities?facility_type=HOSPITAL")
    assert response.status_code == 200
    hospitals = response.json()["facilities"]
    assert len(hospitals) >= 7

    hospital_ids = [h["facility_id"] for h in hospitals]
    assert "HYD-H-001" in hospital_ids  # Osmania General Hospital
    assert "HYD-H-002" in hospital_ids  # Gandhi Hospital
    assert "HYD-H-003" in hospital_ids  # NIMS

    osmania = next(h for h in hospitals if h["facility_id"] == "HYD-H-001")
    assert "Osmania" in osmania["name"]
    assert osmania["facility_type"] == "HOSPITAL"
    assert 17.37 <= osmania["latitude"] <= 17.39
    assert 78.47 <= osmania["longitude"] <= 78.49


def test_facility_type_filtering():
    """Verify that facility_type parameter correctly filters hospitals vs. shelters."""
    resp_hosp = client.get("/emergency-facilities?facility_type=HOSPITAL")
    assert resp_hosp.status_code == 200
    for f in resp_hosp.json()["facilities"]:
        assert f["facility_type"] == "HOSPITAL"

    resp_shelter = client.get("/emergency-facilities?facility_type=SHELTER")
    assert resp_shelter.status_code == 200
    for f in resp_shelter.json()["facilities"]:
        assert f["facility_type"] == "SHELTER"


def test_demo_versus_verified_labeling():
    """Ensure verified, unverified, and demo records are explicitly and truthfully labeled."""
    # Real hospital records must be labeled PUBLIC_UNVERIFIED (never fabricated as verified)
    resp = client.get("/emergency-facilities?facility_type=HOSPITAL")
    for f in resp.json()["facilities"]:
        assert f["data_status"] == "PUBLIC_UNVERIFIED"
        assert "Public" in f["source"]
        assert any(p in f["verification_note"].lower() for p in ["not integrated", "must be verified", "not confirmed"])

    # In demo mode, simulated facilities must be labeled DEMO
    service = get_emergency_facility_service()
    demo_facs = service.get_facilities(include_demo=True)
    demo_records = [f for f in demo_facs if f.data_status == "DEMO"]
    assert len(demo_records) >= 1
    for d in demo_records:
        assert d.data_status == "DEMO"
        assert "DEMO" in d.source
        assert "[DEMO]" in d.name


def test_unavailable_or_unknown_values_not_fabricated():
    """Ensure hospital capacity, occupancy, and triage status are NOT fabricated when unknown."""
    resp = client.get("/emergency-facilities?facility_type=HOSPITAL")
    hospitals = resp.json()["facilities"]
    for h in hospitals:
        # We must never fabricate ICU beds or capacity from static listings
        assert h["capacity"] is None
        assert h["current_occupancy"] is None
        assert h["operational_status"] == "UNKNOWN"


def test_facility_by_id_endpoint():
    """Verify GET /emergency-facilities/{facility_id} returns the facility or 404."""
    resp = client.get("/emergency-facilities/HYD-H-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["facility_id"] == "HYD-H-001"
    assert "Osmania" in data["name"]

    resp_404 = client.get("/emergency-facilities/NON_EXISTENT_999")
    assert resp_404.status_code == 404


def test_routing_with_selected_facility_id():
    """Objective 5: Allow a user to select an emergency facility (hospital) as evacuation destination."""
    payload = {
        "origin": {
            "latitude": 17.3616,
            "longitude": 78.4747
        },
        "facility_id": "HYD-H-001"
    }
    response = client.post("/evacuation-route", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["route_status"] == "ROUTE_AVAILABLE"
    assert data["route_distance_km"] > 0
    assert len(data["geometry"]) > 2
    assert data["destination_name"] == "Osmania General Hospital"
    assert data["destination_type"] == "HOSPITAL"
    assert data["facility_id"] == "HYD-H-001"


def test_routing_with_selected_shelter_facility_id():
    """Objective 5: Allow selecting a shelter string ID (e.g. HYD-S-001) as destination."""
    payload = {
        "origin": {
            "latitude": 17.4100,
            "longitude": 78.4800
        },
        "facility_id": "HYD-S-001"
    }
    response = client.post("/evacuation-route", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["route_status"] == "ROUTE_AVAILABLE"
    assert "HYD-S-001" in data["facility_id"]


def test_routing_with_destination_coordinates():
    """Verify that routing directly to coordinates remains fully functional."""
    payload = {
        "origin": {
            "latitude": 17.3616,
            "longitude": 78.4747
        },
        "destination": {
            "latitude": 17.3789,
            "longitude": 78.4777
        }
    }
    response = client.post("/evacuation-route", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["route_status"] == "ROUTE_AVAILABLE"
    assert data["route_distance_km"] > 0


def test_routing_with_nonexistent_facility_returns_404():
    """Verify routing with unknown facility_id returns 404."""
    payload = {
        "origin": {
            "latitude": 17.3616,
            "longitude": 78.4747
        },
        "facility_id": "UNKNOWN-FACILITY-XYZ"
    }
    response = client.post("/evacuation-route", json=payload)
    assert response.status_code == 404


def test_routing_rerouted_metadata_flag():
    """Verify is_rerouted flag and hazard_avoidance details when route bypasses flooded road."""
    # Route from South of Musi to North of Musi with hazard on shortest path
    res = build_graph_route(
        origin_lat=17.3799,
        origin_lon=78.4860,
        dest_lat=17.3899,
        dest_lon=78.4860,
        road_conditions=[
            RoadConditionResponse(
                id=99,
                road_name="Afzal Gunj Bypass",
                status="FLOODED",
                latitude=17.3830,
                longitude=78.4911,
                notes="[DEMO] Flooded bypass",
                last_updated=datetime.now(timezone.utc)
            )
        ]
    )
    assert res.route_status == "ROUTE_AVAILABLE"
    assert res.road_condition_status == "HAZARDS_AVOIDED"
    assert res.is_rerouted is True
    assert any("safely avoid" in w for w in res.warnings)


def test_legacy_shelters_endpoint_preserved():
    """Constraint: Preserve existing architecture and exact 11 shelters from hyderabad_shelters.csv."""
    response = client.get("/shelters")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 11
    assert len(data["shelters"]) == 11
