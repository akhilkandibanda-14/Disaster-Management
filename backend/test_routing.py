import pytest
import os
from datetime import datetime, timezone
from unittest.mock import patch

from app.services.routing import build_graph_route
from app.services.road_network import road_network_service
from app.schemas.resources import RoadConditionResponse
from app.models.resources import Shelter
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Ensure network is loaded before testing
@pytest.fixture(scope="module", autouse=True)
def setup_network():
    if not os.path.exists(road_network_service.graph_path):
        pytest.skip("Road network graph not found, skipping routing tests.")
    road_network_service.load_graph()

def test_valid_origin_destination_produces_route():
    # Hyderabad coordinates: Charminar to Hussain Sagar
    res = build_graph_route(17.3616, 78.4747, 17.4239, 78.4738)
    assert res.route_status == "ROUTE_AVAILABLE"
    assert res.geometry is not None
    assert len(res.geometry) > 2

def test_route_distance_is_positive():
    res = build_graph_route(17.3616, 78.4747, 17.4239, 78.4738)
    assert res.route_distance_km > 0.0

def test_geometry_is_valid_geojson_linestring_format():
    res = build_graph_route(17.3616, 78.4747, 17.4239, 78.4738)
    # Check that each point is [longitude, latitude]
    for pt in res.geometry:
        assert len(pt) == 2
        assert -180 <= pt[0] <= 180  # lon
        assert -90 <= pt[1] <= 90   # lat

def test_origin_destination_nodes_exist():
    res = build_graph_route(17.3616, 78.4747, 17.4239, 78.4738)
    assert res.origin_node is not None
    assert res.destination_node is not None

def test_snap_distances_returned():
    res = build_graph_route(17.3616, 78.4747, 17.4239, 78.4738)
    assert res.origin_snap_distance_km is not None
    assert res.destination_snap_distance_km is not None

def test_repeated_requests_deterministic():
    res1 = build_graph_route(17.3616, 78.4747, 17.4239, 78.4738)
    res2 = build_graph_route(17.3616, 78.4747, 17.4239, 78.4738)
    assert res1.route_distance_km == res2.route_distance_km
    assert res1.geometry == res2.geometry

def test_invalid_latitude_fails():
    res = build_graph_route(95.0, 78.4747, 17.4239, 78.4738)
    assert res.route_status == "INVALID_ORIGIN"

def test_invalid_longitude_fails():
    res = build_graph_route(17.3616, 78.4747, 17.4239, 200.0)
    assert res.route_status == "INVALID_DESTINATION"

def test_no_route_case_handled():
    # Attempt to route between Hyderabad and New York (which shouldn't be in the graph)
    res = build_graph_route(17.3616, 78.4747, 40.7128, -74.0060)
    # The destination should fail the snap distance constraint
    assert res.route_status == "DESTINATION_OUTSIDE_NETWORK"

def test_road_condition_status_remains_unknown():
    res = build_graph_route(17.3616, 78.4747, 17.4239, 78.4738)
    assert res.road_condition_status == "UNKNOWN"
    assert any("Live road flood/blockage conditions are not currently integrated." in w for w in res.warnings)

def test_duration_is_null():
    res = build_graph_route(17.3616, 78.4747, 17.4239, 78.4738)
    assert res.estimated_duration_min is None

def test_shelters_endpoint_functional():
    response = client.get("/shelters")
    assert response.status_code == 200
    assert isinstance(response.json()["shelters"], list)

def test_shelters_recommended_endpoint_functional():
    # Provide a reasonable coordinate in Hyderabad
    response = client.get("/shelters/recommended?latitude=17.3850&longitude=78.4867&radius_km=5.0&top_n=3")
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)

def test_evacuation_route_api():
    payload = {
        "origin": {
            "latitude": 17.3850,
            "longitude": 78.4867
        },
        "destination": {
            "latitude": 17.4160,
            "longitude": 78.5010
        }
    }
    response = client.post("/evacuation-route", json=payload)
    if response.status_code == 200:
        data = response.json()
        assert data["route_status"] in ["ROUTE_AVAILABLE", "NO_ROUTE", "DESTINATION_OUTSIDE_NETWORK"]
        assert data["road_condition_status"] in ["CLEAR", "HAZARDS_AVOIDED", "UNKNOWN"]


# =========================================================================
# Hazard-Aware Evacuation Routing Milestone Tests
# =========================================================================

def test_normal_route_with_no_blocked_roads():
    """Requirement 9.1: Normal route with empty road conditions or only OPEN roads."""
    open_road = RoadConditionResponse(
        id=10,
        road_name="Open Corridor",
        status="OPEN",
        latitude=17.385,
        longitude=78.486,
        notes="[DEMO] Clear road",
        last_updated=datetime.now(timezone.utc)
    )
    res = build_graph_route(17.3616, 78.4747, 17.4239, 78.4738, road_conditions=[open_road])
    assert res.route_status == "ROUTE_AVAILABLE"
    assert res.road_condition_status == "CLEAR"
    assert res.route_distance_km > 0
    assert not any("Live road flood/blockage conditions are not currently integrated." in w for w in res.warnings)


def test_shortest_route_replaced_when_blocked():
    """Requirement 9.2: A shortest route that must be replaced because it contains a blocked segment."""
    res_clean = build_graph_route(17.3799, 78.4860, 17.3899, 78.4860, road_conditions=[])
    assert res_clean.route_status == "ROUTE_AVAILABLE"

    # Blocked hazard on the primary path across Musi River
    blocked_hazard = RoadConditionResponse(
        id=99,
        road_name="Afzal Gunj Bypass",
        status="FLOODED",
        latitude=17.3830,
        longitude=78.4911,
        notes="[DEMO] Simulated flooded section",
        last_updated=datetime.now(timezone.utc)
    )
    res_detour = build_graph_route(17.3799, 78.4860, 17.3899, 78.4860, road_conditions=[blocked_hazard])
    assert res_detour.route_status == "ROUTE_AVAILABLE"
    assert res_detour.road_condition_status == "HAZARDS_AVOIDED"
    # Detour must be longer than unconstrained path and take a different geometry
    assert res_detour.route_distance_km > res_clean.route_distance_km
    assert res_detour.geometry != res_clean.geometry
    assert any("safely avoid" in w for w in res_detour.warnings)


def test_multiple_blocked_segments_avoided():
    """Requirement 9.3: Multiple blocked segments are excluded and avoided."""
    hazard1 = RoadConditionResponse(
        id=101,
        road_name="Primary Bridge",
        status="FLOODED",
        latitude=17.3830,
        longitude=78.4911,
        notes="[DEMO] Flooded bridge",
        last_updated=datetime.now(timezone.utc)
    )
    hazard2 = RoadConditionResponse(
        id=102,
        road_name="Riverside Link",
        status="BLOCKED",
        latitude=17.3850,
        longitude=78.4860,
        notes="[DEMO] Blocked riverside road",
        last_updated=datetime.now(timezone.utc)
    )
    res = build_graph_route(17.3799, 78.4860, 17.3899, 78.4860, road_conditions=[hazard1, hazard2])
    assert res.route_status == "ROUTE_AVAILABLE"
    assert res.road_condition_status == "HAZARDS_AVOIDED"
    assert any("safely avoid 2 hazardous/blocked road segment(s)" in w for w in res.warnings)


def test_no_available_alternative_route():
    """Requirement 9.4: No safe route available returns clear error; never silently falls back to blocked roads."""
    # Origin node 307084293 (at 17.3792, 78.4852) has only 1 exit edge
    flood_at_origin = RoadConditionResponse(
        id=201,
        road_name="Origin Access Road",
        status="FLOODED",
        latitude=17.3792,
        longitude=78.4852,
        notes="[DEMO] Origin street submerged",
        last_updated=datetime.now(timezone.utc)
    )
    res = build_graph_route(17.3799, 78.4860, 17.3899, 78.4860, road_conditions=[flood_at_origin])
    assert res.route_status == "NO_SAFE_ROUTE"
    assert res.road_condition_status == "BLOCKED"
    assert res.geometry == []
    assert res.route_distance_km == 0.0
    assert any("No safe evacuation route could be found" in w for w in res.warnings)


def test_unknown_or_unmatched_road_reports():
    """Requirement 9.5: Unmatched or ambiguous road reports are handled conservatively."""
    distant_road = RoadConditionResponse(
        id=101,
        road_name="Distant Outpost Road",
        status="BLOCKED",
        latitude=18.5000,
        longitude=79.5000,
        notes="Far outside Hyderabad",
        last_updated=datetime.now(timezone.utc)
    )
    res = build_graph_route(17.3616, 78.4747, 17.4239, 78.4738, road_conditions=[distant_road])
    assert res.route_status == "ROUTE_AVAILABLE"
    # Router must NOT claim it avoided the hazard, but must warn about the unmatchable report
    assert any("could not match to graph" in w for w in res.warnings)
    assert res.road_condition_status == "CLEAR"


def test_missing_or_unavailable_graph_data():
    """Requirement 9.6: Missing or unavailable graph data returns structured error response gracefully."""
    with patch.object(road_network_service, "load_graph", side_effect=FileNotFoundError("Road graph file missing")):
        res = build_graph_route(17.3616, 78.4747, 17.4239, 78.4738)
        assert res.route_status == "NO_ROUTE"
        assert any("Graph loading failed" in w for w in res.warnings)
        assert res.geometry == []
        assert res.route_distance_km == 0.0

    with patch.object(road_network_service, "load_graph", return_value=None):
        with patch.object(road_network_service, "G", None):
            res = build_graph_route(17.3616, 78.4747, 17.4239, 78.4738)
            assert res.route_status == "NO_ROUTE"
            assert any("unavailable" in w for w in res.warnings)
            assert res.geometry == []


def test_existing_api_response_compatibility():
    """Requirement 9.7: Verify full API response schema compatibility via FastAPI TestClient."""
    payload = {
        "origin": {
            "latitude": 17.3799,
            "longitude": 78.4860
        },
        "destination": {
            "latitude": 17.3899,
            "longitude": 78.4860
        }
    }
    response = client.post("/evacuation-route", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "geometry" in data
    assert "route_distance_km" in data
    assert "route_status" in data
    assert "road_condition_status" in data
    assert "warnings" in data
    assert isinstance(data["geometry"], list)
    assert data["route_distance_km"] > 0
    assert data["route_status"] == "ROUTE_AVAILABLE"
    # Ensure GeoJSON standard: points are [lon, lat]
    for pt in data["geometry"]:
        assert len(pt) == 2
        assert -180 <= pt[0] <= 180
        assert -90 <= pt[1] <= 90
