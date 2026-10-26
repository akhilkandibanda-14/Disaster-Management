from typing import Literal, Optional, List
from pydantic import BaseModel, Field

class Coordinates(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

class EvacuationRouteRequest(BaseModel):
    origin: Coordinates
    destination: Optional[Coordinates] = None
    shelter_id: Optional[int] = Field(default=None, gt=0, description="Legacy integer shelter ID")
    facility_id: Optional[str] = Field(default=None, description="Emergency facility or shelter string ID (e.g. HYD-H-001, HYD-S-001)")

class EvacuationRouteResponse(BaseModel):
    geometry: List[List[float]] = Field(description="[longitude, latitude] route points")
    route_distance_km: float = Field(ge=0)
    estimated_duration_min: Optional[int] = None
    origin_node: Optional[int] = None
    destination_node: Optional[int] = None
    origin_snap_distance_km: Optional[float] = None
    destination_snap_distance_km: Optional[float] = None
    road_source: str = "OpenStreetMap"
    route_status: str
    road_condition_status: str = "UNKNOWN"
    
    # Destination & facility details
    shelter_id: Optional[int] = None
    shelter_name: Optional[str] = None
    facility_id: Optional[str] = None
    destination_name: Optional[str] = None
    destination_type: Optional[str] = None
    is_rerouted: bool = False
    
    warnings: List[str] = []
