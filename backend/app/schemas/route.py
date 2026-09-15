from typing import Literal

from pydantic import BaseModel, Field


class EvacuationRouteRequest(BaseModel):
    user_latitude: float = Field(ge=-90, le=90)
    user_longitude: float = Field(ge=-180, le=180)
    shelter_id: int | None = Field(default=None, gt=0)


class EvacuationRouteResponse(BaseModel):
    shelter_id: int
    shelter_name: str
    geometry: list[list[float]] = Field(min_length=2, description="[longitude, latitude] route points")
    distance_km: float = Field(ge=0)
    duration_minutes: int = Field(ge=0)
    route_risk: Literal["LOW", "MEDIUM", "HIGH"]
    warnings: list[str]
    source: str
    avoided_road_ids: list[int]
