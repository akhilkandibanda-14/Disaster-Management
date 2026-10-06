import pytest
from app.services.road_network import RoadNetworkService
from app.schemas.road_network import RoadNetworkMetadata, NearestNodeResponse
import os
import networkx as nx

@pytest.fixture(scope="module")
def road_service():
    service = RoadNetworkService()
    # Mocking or expecting real data for tests
    # If the real data exists, we'll use it to ensure it loads
    # Otherwise, we might want to skip or mock
    
    # We will test against the real graph assuming it was downloaded
    # by the scratch script.
    return service

def test_road_graph_loads_successfully(road_service):
    if not os.path.exists(road_service.graph_path):
        pytest.skip("Static road network graph not downloaded. Run script first.")
    
    road_service.load_graph()
    assert road_service.is_loaded
    assert road_service.G is not None
    assert isinstance(road_service.G, nx.MultiDiGraph)

def test_graph_contains_nodes_and_edges(road_service):
    if not road_service.is_loaded:
        pytest.skip()
        
    assert len(road_service.G.nodes) > 0
    assert len(road_service.G.edges) > 0

def test_metadata_is_static(road_service):
    if not road_service.is_loaded:
        pytest.skip()
        
    metadata = road_service.get_metadata()
    assert metadata["source"] == "OpenStreetMap"
    assert "static road-network data" in metadata["static_data_disclaimer"]

def test_nearest_node_valid_coordinates(road_service):
    if not road_service.is_loaded:
        pytest.skip()
        
    # Hyderabad Charminar approx coordinates
    lat, lon = 17.3616, 78.4747
    result = road_service.find_nearest_node(lat, lon)
    
    assert "node_id" in result
    assert "node_latitude" in result
    assert "node_longitude" in result
    assert "distance_km" in result
    assert result["distance_km"] >= 0.0

def test_invalid_latitude_rejected(road_service):
    if not road_service.is_loaded:
        pytest.skip()
    with pytest.raises(ValueError, match="Invalid latitude or longitude"):
        road_service.find_nearest_node(95.0, 78.4747)

def test_invalid_longitude_rejected(road_service):
    if not road_service.is_loaded:
        pytest.skip()
    with pytest.raises(ValueError, match="Invalid latitude or longitude"):
        road_service.find_nearest_node(17.3616, 200.0)

def test_no_fake_road_conditions(road_service):
    condition = road_service.get_road_condition(edge_id=123)
    assert condition == "UNKNOWN"

def test_nearest_node_deterministic(road_service):
    if not road_service.is_loaded:
        pytest.skip()
        
    lat, lon = 17.3616, 78.4747
    res1 = road_service.find_nearest_node(lat, lon)
    res2 = road_service.find_nearest_node(lat, lon)
    
    assert res1["node_id"] == res2["node_id"]
    assert res1["distance_km"] == res2["distance_km"]

def test_graph_connected_enough(road_service):
    if not road_service.is_loaded:
        pytest.skip()
        
    # Just a simple heuristic test to ensure it's not empty and has a big component
    # For a real graph, we'd check weakly connected components.
    components = list(nx.weakly_connected_components(road_service.G))
    assert len(components) > 0
    largest_cc = max(components, key=len)
    assert len(largest_cc) > 1000 # Hyderabad graph should have many nodes
