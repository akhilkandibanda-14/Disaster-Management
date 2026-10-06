from pydantic import BaseModel

class NearestNodeRequest(BaseModel):
    latitude: float
    longitude: float

class NearestNodeResponse(BaseModel):
    node_id: int
    node_latitude: float
    node_longitude: float
    distance_km: float

class RoadNetworkMetadata(BaseModel):
    source: str
    geographic_coverage: str
    extraction_date: str
    graph_type: str
    num_nodes: int
    num_edges: int
    available_attributes: list[str]
    crs: str
    has_one_way: bool
    has_road_names: bool
    has_highway_types: bool
    static_data_disclaimer: str
