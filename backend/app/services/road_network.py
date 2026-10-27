import os
import math
import threading
import numpy as np
from scipy.spatial import cKDTree
import networkx as nx
import osmnx as ox
import logging
from datetime import date

logger = logging.getLogger(__name__)

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

class RoadNetworkService:
    def __init__(self, data_dir: str = "data/raw/roads"):
        candidate = Path(data_dir)
        if candidate.is_absolute() and candidate.exists():
            self.data_dir = str(candidate)
        elif candidate.exists():
            self.data_dir = str(candidate.resolve())
        elif (PROJECT_ROOT / candidate).exists():
            self.data_dir = str((PROJECT_ROOT / candidate).resolve())
        else:
            clean_parts = [part for part in candidate.parts if part != '..']
            if clean_parts and (PROJECT_ROOT / Path(*clean_parts)).exists():
                self.data_dir = str((PROJECT_ROOT / Path(*clean_parts)).resolve())
            else:
                self.data_dir = str((PROJECT_ROOT / candidate).resolve())
        self.graph_path = os.path.join(self.data_dir, "hyderabad_road_network.graphml")
        self.G = None
        self._node_ids = None
        self._kdtree = None
        self.is_loaded = False
        self._lock = threading.Lock()
        self._load_error: str | None = None
        
    def load_graph(self) -> None:
        """Loads the static road graph from the pre-downloaded GraphML file in a thread-safe manner."""
        if not self.is_loaded:
            with self._lock:
                if not self.is_loaded:
                    if not os.path.exists(self.graph_path):
                        self._load_error = f"Road network graph not found at {self.graph_path}. Make sure it is downloaded."
                        raise FileNotFoundError(self._load_error)
                    
                    try:
                        logger.info("Loading static road network from %s...", self.graph_path)
                        self.G = ox.load_graphml(self.graph_path)
                        self._node_ids = list(self.G.nodes())
                        coords = np.array([[self.G.nodes[n].get('x', 0.0), self.G.nodes[n].get('y', 0.0)] for n in self._node_ids])
                        self._kdtree = cKDTree(coords)
                        self.is_loaded = True
                        self._load_error = None
                        logger.info("Loaded road network with %d nodes and %d edges.", len(self.G.nodes), len(self.G.edges))
                    except Exception as e:
                        self.G = None
                        self._node_ids = None
                        self._kdtree = None
                        self.is_loaded = False
                        self._load_error = str(e)
                        logger.error("Failed to load road network from %s: %s", self.graph_path, e)
                        raise

    def load_graph_safe(self) -> bool:
        """Loads the road graph safely without throwing unhandled exceptions, suitable for startup lifespan."""
        try:
            self.load_graph()
            return True
        except FileNotFoundError as e:
            logger.warning(
                "Road network graph not found on startup: %s. Evacuation routing will be unavailable until downloaded.",
                e,
            )
            return False
        except Exception as e:
            logger.error("Error loading road network on startup: %s", e)
            return False

    def _reset_state_for_testing(self) -> None:
        """Resets in-memory graph state for test isolation."""
        with self._lock:
            self.G = None
            self._node_ids = None
            self._kdtree = None
            self.is_loaded = False
            self._load_error = None

    def set_graph_for_testing(self, G: nx.MultiDiGraph) -> None:
        """Sets a mock or synthetic graph in-memory for deterministic unit testing."""
        with self._lock:
            self.G = G
            self._node_ids = list(G.nodes())
            coords = np.array([[G.nodes[n].get('x', 0.0), G.nodes[n].get('y', 0.0)] for n in self._node_ids])
            self._kdtree = cKDTree(coords)
            self.is_loaded = True
            self._load_error = None

    def get_metadata(self) -> dict:
        self.load_graph()
        
        # Check an edge to see what attributes are available
        sample_edge = next(iter(self.G.edges(data=True))) if len(self.G.edges) > 0 else (None, None, {})
        attributes = list(sample_edge[2].keys()) if sample_edge[2] else []
        
        return {
            "source": "OpenStreetMap",
            "geographic_coverage": "Hyderabad, Telangana, India",
            "extraction_date": str(date.today()), 
            "graph_type": "NetworkX MultiDiGraph (Drive)",
            "num_nodes": len(self.G.nodes),
            "num_edges": len(self.G.edges),
            "available_attributes": attributes,
            "crs": str(self.G.graph.get("crs", "epsg:4326")),
            "has_one_way": "oneway" in attributes,
            "has_road_names": "name" in attributes,
            "has_highway_types": "highway" in attributes,
            "static_data_disclaimer": "This is static road-network data and does not represent live road conditions."
        }
        
    def find_nearest_node(self, latitude: float, longitude: float) -> dict:
        self.load_graph()
        
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            raise ValueError("Invalid latitude or longitude.")
        
        if self._kdtree is not None and self._node_ids is not None:
            _, idx = self._kdtree.query([longitude, latitude])
            node_id = self._node_ids[idx]
            node_data = self.G.nodes[node_id]
            node_lat = float(node_data.get('y', 0.0))
            node_lon = float(node_data.get('x', 0.0))
            dist_meters = haversine_distance_meters(latitude, longitude, node_lat, node_lon)
        else:
            node_id, dist_meters = ox.distance.nearest_nodes(self.G, X=longitude, Y=latitude, return_dist=True)
            node_data = self.G.nodes[node_id]
            node_lat = float(node_data.get('y', 0.0))
            node_lon = float(node_data.get('x', 0.0))
        
        distance_km = dist_meters / 1000.0
        
        return {
            "node_id": node_id,
            "node_latitude": float(node_lat),
            "node_longitude": float(node_lon),
            "distance_km": float(distance_km)
        }

    def get_road_condition(self, edge_id: int = None) -> str:
        """
        Since this is a static road network, we DO NOT fabricate fake road conditions.
        It must always return UNKNOWN unless connected to a real dynamic source.
        """
        return "UNKNOWN"

road_network_service = RoadNetworkService()
