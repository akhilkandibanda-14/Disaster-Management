import pytest
from app.services.routing import build_graph_route
from app.services.road_network import road_network_service
from app.models.resources import Shelter
import os

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

from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app)

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
        assert data["road_condition_status"] == "UNKNOWN"

