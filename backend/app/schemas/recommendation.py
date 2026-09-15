from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.resources import ShelterResponse


class SafetyBreakdown(BaseModel):
    disaster_safety: float = Field(ge=0, le=100)
    road_safety: float = Field(ge=0, le=100)
    availability: float = Field(ge=0, le=100)
    accessibility: float = Field(ge=0, le=100)
    distance: float = Field(ge=0, le=100)


class ShelterRecommendation(BaseModel):
    shelter: ShelterResponse
    safety_score: float = Field(ge=0, le=100)
    distance_km: float = Field(ge=0)
    estimated_travel_minutes: int = Field(ge=0)
    breakdown: SafetyBreakdown
    reason: str
    source: str
    warning: str | None = None


class RecommendationResponse(BaseModel):
    user_latitude: float
    user_longitude: float
    recommendation: ShelterRecommendation | None
    alternatives: list[ShelterRecommendation]
    generated_at: datetime
    source: str
    warning: str | None = None
