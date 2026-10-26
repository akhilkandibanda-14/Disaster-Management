import concurrent.futures
from unittest.mock import MagicMock, patch
import pytest
import networkx as nx
from fastapi.testclient import TestClient

from app.main import app
from app.services.road_network import RoadNetworkService, road_network_service


def test_thread_safe_load_graph_loads_only_once():
    """Verify that multiple concurrent threads calling load_graph execute the load logic only once."""
    test_service = RoadNetworkService()
    test_service._reset_state_for_testing()

    load_call_count = 0
    dummy_graph = nx.MultiDiGraph()
    dummy_graph.add_node(1, x=78.48, y=17.38)
    dummy_graph.add_edge(1, 1, length=10.0)

    def mock_load(filepath):
        nonlocal load_call_count
        load_call_count += 1
        return dummy_graph

    with patch("os.path.exists", return_value=True), patch("osmnx.load_graphml", side_effect=mock_load):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(test_service.load_graph) for _ in range(20)]
            for f in concurrent.futures.as_completed(futures):
                f.result()

        assert load_call_count == 1
        assert test_service.is_loaded is True
        assert test_service.G is dummy_graph


def test_load_graph_idempotent():
    """Calling load_graph repeatedly does not reload the graph once is_loaded is True."""
    test_service = RoadNetworkService()
    test_service._reset_state_for_testing()
    test_service.G = nx.MultiDiGraph()
    test_service.is_loaded = True

    with patch("osmnx.load_graphml") as mock_load:
        test_service.load_graph()
        mock_load.assert_not_called()


def test_load_graph_safe_handles_missing_file_gracefully():
    """load_graph_safe should log a warning and return False instead of raising FileNotFoundError."""
    test_service = RoadNetworkService(data_dir="non_existent_dir_for_test")
    test_service._reset_state_for_testing()

    with patch("os.path.exists", return_value=False):
        result = test_service.load_graph_safe()
        assert result is False
        assert test_service.is_loaded is False
        assert test_service.G is None
        assert "not found" in (test_service._load_error or "")


def test_load_graph_direct_raises_file_not_found():
    """Calling load_graph directly on a missing file must raise FileNotFoundError for explicit callers."""
    test_service = RoadNetworkService(data_dir="non_existent_dir_for_test")
    test_service._reset_state_for_testing()

    with patch("os.path.exists", return_value=False):
        with pytest.raises(FileNotFoundError):
            test_service.load_graph()


def test_load_graph_safe_handles_loader_exception():
    """load_graph_safe should catch unexpected loader errors and return False without crashing."""
    test_service = RoadNetworkService()
    test_service._reset_state_for_testing()

    with patch("os.path.exists", return_value=True), patch("osmnx.load_graphml", side_effect=RuntimeError("Corrupt XML")):
        result = test_service.load_graph_safe()
        assert result is False
        assert test_service.is_loaded is False
        assert test_service.G is None
        assert "Corrupt XML" in (test_service._load_error or "")


def test_health_endpoint_reports_road_network_status():
    """Health endpoint reports road_network_loaded flag."""
    with TestClient(app) as client:
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert "road_network_loaded" in data
        assert isinstance(data["road_network_loaded"], bool)
