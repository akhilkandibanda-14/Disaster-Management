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
    compute_alternatives: bool = Field(default=True, description="Whether to compute an alternative evacuation route if available")


class AlternativeRoute(BaseModel):
    geometry: List[List[float]] = Field(description="[longitude, latitude] alternative path coordinates")
    route_distance_km: float = Field(ge=0)
    estimated_duration_min: Optional[int] = None
    road_condition_status: str = "CLEAR"
    description: str = Field(..., description="Arterial or secondary route description")


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
    alternatives: List[AlternativeRoute] = Field(
        default_factory=list,
        description="Verified alternative evacuation routes computed on evaluated hazard-avoidance road network"
    )
    data_sources_used: List[str] = Field(
        default_factory=list,
        description="Authoritative and municipal data sources queried for road and hazard conditions"
    )
    observation_freshness: Optional[str] = Field(
        default=None,
        description="Timestamp or freshness indicator of evaluated hazard feeds"
    )
    hazard_coverage_limitations: Optional[str] = Field(
        default=None,
        description="Known spatial/temporal limitations in active flood hazard coverage"
    )
    stale_hazards_present: bool = Field(
        default=False,
        description="Flag indicating if any upstream hazard feed returned cached or stale data"
    )
    validation_level: str = Field(
        default="GEOMETRY_INTERSECTION_VALIDATED",
        description="Validation rigor applied (e.g. GEOMETRY_INTERSECTION_VALIDATED)"
    )
    safety_disclaimer: str = Field(
        default="Evacuation routes are computed based on currently known road conditions and flood hazard information. Real-time water depth, debris, and sudden flash floods may not be modeled. Never attempt to drive or walk through flooded roadways.",
        description="Mandatory evacuation safety caveat"
    )
