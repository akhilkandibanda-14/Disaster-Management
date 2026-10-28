from typing import List, Optional
from pydantic import BaseModel, Field


class AssistantCoordinate(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class AssistantContext(BaseModel):
    location: Optional[AssistantCoordinate] = None
    location_status: Optional[str] = None
    is_in_hazard_zone: Optional[bool] = None
    hazard_names: Optional[List[str]] = Field(default_factory=list)
    highest_severity: Optional[str] = None
    route_status: Optional[str] = None
    route_distance_km: Optional[float] = None
    is_severe_weather: Optional[bool] = None
    is_demo_mode: Optional[bool] = None
    nearest_shelter_name: Optional[str] = None
    nearest_shelter_distance_km: Optional[float] = None
    active_alerts_count: Optional[int] = 0


class AssistantQueryRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1500)
    language: Optional[str] = Field("en", pattern="^(en|te|hi)$")
    context: Optional[AssistantContext] = None


class AssistantQueryResponse(BaseModel):
    reply: str
    language: str
    provider: str
    is_emergency: bool = False
    suggested_actions: List[str] = Field(default_factory=list)
    follow_up_question: Optional[str] = None
    data_sources_evaluated: List[str] = Field(default_factory=list)
    data_disclaimer: Optional[str] = None
