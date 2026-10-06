import os
import networkx as nx
import osmnx as ox
import logging
from datetime import date

logger = logging.getLogger(__name__)

class RoadNetworkService:
    def __init__(self, data_dir: str = "data/raw/roads"):
        self.data_dir = data_dir
        self.graph_path = os.path.join(self.data_dir, "hyderabad_road_network.graphml")
        self.G = None
        self.is_loaded = False
        
    def load_graph(self):
        """Loads the static road graph from the pre-downloaded GraphML file."""
        if not self.is_loaded:
            if not os.path.exists(self.graph_path):
                raise FileNotFoundError(f"Road network graph not found at {self.graph_path}. Make sure it is downloaded.")
            
            logger.info("Loading static road network from %s...", self.graph_path)
            self.G = ox.load_graphml(self.graph_path)
            self.is_loaded = True
            logger.info("Loaded road network with %d nodes and %d edges.", len(self.G.nodes), len(self.G.edges))

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
        
        # In newer osmnx, nearest_nodes expects G, X, Y
        # X is longitude, Y is latitude
        node_id, dist_meters = ox.distance.nearest_nodes(self.G, X=longitude, Y=latitude, return_dist=True)
            
        node_data = self.G.nodes[node_id]
        node_lat = node_data.get('y', 0.0)
        node_lon = node_data.get('x', 0.0)
        
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
