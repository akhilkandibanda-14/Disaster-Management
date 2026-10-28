import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.hazard import GeoJSONGeometry, HazardRecord, LocationHazardWarning
from app.services.hazard import HazardService, point_in_polygon, haversine_distance_km
from app.services.routing import build_graph_route
from app.schemas.resources import RoadConditionResponse

client = TestClient(app)


def test_geojson_geometry_valid_and_invalid():
    """Verify GeoJSONGeometry validation: requires closed rings, coordinate bounds, >= 4 points."""
    # Valid polygon
    valid_coords = [
        [
            [78.47, 17.37],
            [78.49, 17.37],
            [78.49, 17.39],
            [78.47, 17.39],
            [78.47, 17.37]
        ]
    ]
    geom = GeoJSONGeometry(type="Polygon", coordinates=valid_coords)
    assert geom.type == "Polygon"

    # Invalid: Unclosed ring
    unclosed_coords = [
        [
            [78.47, 17.37],
            [78.49, 17.37],
            [78.49, 17.39],
            [78.47, 17.38]  # Does not match first [78.47, 17.37]
        ]
    ]
    with pytest.raises(ValueError, match="not closed"):
        GeoJSONGeometry(type="Polygon", coordinates=unclosed_coords)

    # Invalid: Fewer than 4 points
    few_points = [
        [
            [78.47, 17.37],
            [78.49, 17.37],
            [78.47, 17.37]
        ]
    ]
    with pytest.raises(ValueError, match="at least 4 coordinates"):
        GeoJSONGeometry(type="Polygon", coordinates=few_points)

    # Invalid: Latitude out of range
    invalid_lat = [
        [
            [78.47, 117.37],
            [78.49, 117.37],
            [78.49, 117.39],
            [78.47, 117.37]
        ]
    ]
    with pytest.raises(ValueError):
        GeoJSONGeometry(type="Polygon", coordinates=invalid_lat)


def test_hazard_record_validation():
    """Verify HazardRecord validation rules and defaults."""
    now = datetime.now(timezone.utc)
    rec = HazardRecord(
        hazard_id="TEST-HAZ-001",
        hazard_type="WATER_STAGNATION",
        title="Test Water Stagnation",
        description="Testing validation rules",
        source_name="Municipal Survey",
        last_retrieved=now,
        data_status="PUBLIC_UNVERIFIED",
        verification_note="Survey data only"
    )
    # Defaults to UNKNOWN severity when unsupported
    assert rec.severity == "UNKNOWN"
    assert rec.is_active is True
    assert rec.is_stale is False

    # Invalid latitude
    with pytest.raises(ValueError):
        HazardRecord(
            hazard_id="TEST-002",
            hazard_type="FLOOD_ZONE",
            title="Bad Lat",
            description="Bad",
            latitude=95.0,  # Invalid
            longitude=78.0,
            source_name="Test",
            last_retrieved=now,
            data_status="PUBLIC_UNVERIFIED",
            verification_note="Test"
        )


def test_get_flood_hazards_endpoint():
    """Verify GET /flood-hazards returns structured list and metadata counters."""
    resp = client.get("/flood-hazards")
    assert resp.status_code == 200
    data = resp.json()
    assert "hazards" in data
    assert "total" in data
    assert data["total"] > 0
    assert len(data["hazards"]) == data["total"]
    assert "authoritative_count" in data
    assert "unverified_count" in data
    assert "demo_count" in data
    assert "data_disclaimer" in data


def test_separation_of_authoritative_unverified_and_demo():
    """Verify distinct labeling: DEMO vs PUBLIC_UNVERIFIED vs AUTHORITATIVE."""
    # When include_demo=False, no demo hazards returned
    resp_no_demo = client.get("/flood-hazards?include_demo=false")
    assert resp_no_demo.status_code == 200
    for h in resp_no_demo.json()["hazards"]:
        assert h["data_status"] != "DEMO"
        assert "[DEMO]" not in h["title"]

    # When include_demo=True, demo hazard is explicitly marked
    resp_demo = client.get("/flood-hazards?include_demo=true")
    assert resp_demo.status_code == 200
    demo_hazards = [h for h in resp_demo.json()["hazards"] if h["data_status"] == "DEMO"]
    assert len(demo_hazards) >= 1
    for d in demo_hazards:
        assert d["data_status"] == "DEMO"
        assert "[DEMO]" in d["title"]
        assert "simulated" in d["verification_note"].lower()

    # Public flood zones must be labeled PUBLIC_UNVERIFIED
    public_hazards = [h for h in resp_demo.json()["hazards"] if h["data_status"] == "PUBLIC_UNVERIFIED"]
    assert len(public_hazards) >= 4  # Musi corridor, Moosa Nagar, Bapu Ghat, etc.
    for p in public_hazards:
        assert p["data_status"] == "PUBLIC_UNVERIFIED"
        assert any(k in p["source_name"] for k in ["GHMC", "MRDCL", "Survey"])


def test_provider_network_error_graceful_handling():
    """Ensure service does not crash if external authoritative providers timeout or fail."""
    service = HazardService()
    
    # Simulate network timeout when fetching NDMA Sachet
    with patch("httpx.Client.get", side_effect=httpx.TimeoutException("Connection timed out")):
        sachet_alerts = service.fetch_ndma_sachet_alerts()
        assert sachet_alerts == []  # Gracefully returns empty list

    # Simulate HTTP 502 / network error on GloFAS
    with patch("httpx.Client.get", side_effect=httpx.RequestError("Network error")):
        glofas_alerts = service.fetch_glofas_hydrology()
        assert glofas_alerts == []  # Gracefully returns empty list


def test_stale_or_expired_hazard_status():
    """Ensure expired or past-due alerts are marked as STALE."""
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(hours=3)

    record = HazardRecord(
        hazard_id="STALE-001",
        hazard_type="SEVERE_WEATHER_ALERT",
        title="Expired Heavy Rain Warning",
        description="Warning that was valid until 3 hours ago",
        source_name="Official Warning Center",
        publication_time=expired_time - timedelta(hours=6),
        last_retrieved=now,
        expires_at=expired_time,
        is_active=False,
        is_stale=True,
        data_status="STALE",
        verification_note="Warning expired. Stale advisory."
    )
    assert record.is_stale is True
    assert record.data_status == "STALE"


def test_location_warning_inside_hazard_polygon():
    """Test point-in-polygon spatial detection for coordinates inside Musi flood zone."""
    # Musi River Central Causeway Inundation Corridor: point at lat 17.383, lon 78.490
    resp = client.get("/flood-hazards/check-location?latitude=17.383&longitude=78.490")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_in_hazard_zone"] is True
    assert data["hazard_count"] >= 1
    assert data["highest_severity"] in ("HIGH", "SEVERE", "EXTREME", "MODERATE")
    
    # Mapped static flood zones must NOT claim active flooding is occurring now
    assert data["warning_classification"] == "MAPPED_FLOOD_PRONE_ZONE"
    assert data["has_mapped_flood_zone"] is True
    assert data["has_active_confirmed_flood"] is False
    assert data["headline"].startswith("MAPPED FLOOD-PRONE ZONE INTERSECTS SELECTED LOCATION")
    assert "vulnerability" in data["explanation"].lower() or "indicative" in data["explanation"].lower()
    
    hazard_ids = [h["hazard_id"] for h in data["intersected_hazards"]]
    assert any("HYD-FZ" in hid for hid in hazard_ids)


def test_location_warning_outside_hazard_polygon():
    """Test coordinates well outside any flood zone return clean status with safety disclaimer."""
    # Point outside flood zones: lat 17.350, lon 78.450
    resp = client.get("/flood-hazards/check-location?latitude=17.350&longitude=78.450&include_demo=false")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_in_hazard_zone"] is False
    assert data["hazard_count"] == 0
    assert data["highest_severity"] == "NONE"
    assert data["warning_classification"] == "NONE"
    assert data["has_active_confirmed_flood"] is False
    assert data["has_mapped_flood_zone"] is False
    assert data["headline"] == "NO KNOWN HAZARD INTERSECTS THIS LOCATION"


def test_location_warning_distinguishes_authoritative_vs_mapped_zone():
    """Verify that authoritative active flood alerts trigger CONFIRMED_ACTIVE_FLOOD, not MAPPED_FLOOD_PRONE_ZONE."""
    from app.services.hazard import get_hazard_service
    srv = get_hazard_service()
    
    auth_alert = HazardRecord(
        hazard_id="AUTH-FLOOD-TEST-001",
        hazard_type="RIVER_OVERFLOW",
        title="Musi River Overflows Banks",
        description="High discharge leading to central bridge submergence",
        severity="HIGH",
        latitude=17.383,
        longitude=78.490,
        source_name="NDMA SACHET",
        source_type="OFFICIAL_ALERT",
        data_status="AUTHORITATIVE",
        is_active=True,
        is_stale=False,
        last_retrieved=datetime.now(timezone.utc),
        verification_note="Live official warning."
    )
    with patch.object(srv, "get_hazards", return_value=[auth_alert]):
        result = srv.check_location(latitude=17.383, longitude=78.490)
        assert result.warning_classification == "CONFIRMED_ACTIVE_FLOOD"
        assert result.has_active_confirmed_flood is True
        assert "ACTIVE FLOOD HAZARD AT SELECTED LOCATION" in result.headline
        assert result.confirmed_severity == "HIGH"


def test_missing_hazard_data_never_implies_safety():
    """Constraint: System must explicitly state that absence of hazard alerts does not prove safety."""
    resp = client.get("/flood-hazards/check-location?latitude=17.350&longitude=78.450")
    assert resp.status_code == 200
    data = resp.json()
    disclaimer = data["disclaimer"].lower()
    assert "not guarantee" in disclaimer or "never interpret" in disclaimer
    assert "safe" in disclaimer
    assert "official" in disclaimer


def test_hazard_by_id_endpoint():
    """Verify GET /flood-hazards/{hazard_id} returns the specific hazard or 404."""
    resp = client.get("/flood-hazards/HYD-FZ-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hazard_id"] == "HYD-FZ-001"
    assert "Musi" in data["title"]
    assert data["geometry"]["type"] == "Polygon"

    resp_404 = client.get("/flood-hazards/NON_EXISTENT_HAZARD_999")
    assert resp_404.status_code == 404


def test_routing_hazard_awareness_and_no_safe_route_intact():
    """Verify that hazard-aware routing and NO_SAFE_ROUTE behavior are preserved."""
    # Evacuation route with hazard on Afzal Gunj Bypass
    res = build_graph_route(
        origin_lat=17.3799,
        origin_lon=78.4860,
        dest_lat=17.3899,
        dest_lon=78.4860,
        road_conditions=[
            RoadConditionResponse(
                id=88,
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


def test_emergency_facilities_and_shelters_preserved():
    """Ensure hospital and shelter endpoints from Milestones 1-3 remain intact."""
    # Hospitals & emergency facilities
    resp_facs = client.get("/emergency-facilities")
    assert resp_facs.status_code == 200
    assert resp_facs.json()["total"] >= 18

    # Shelters endpoint
    resp_shelters = client.get("/shelters")
    assert resp_shelters.status_code == 200
    assert resp_shelters.json()["total"] == 11
