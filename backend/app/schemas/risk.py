from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]


class RiskZone(BaseModel):
    id: str
    risk_level: RiskLevel
    flood_probability: float = Field(ge=0, le=1)
    polygon: list[list[float]] = Field(min_length=4, description="[longitude, latitude] points")
    source: str
    updated_at: datetime


class RiskMapResponse(BaseModel):
    disaster_type: Literal["FLOOD"]
    bounds: list[float] = Field(min_length=4, max_length=4, description="south, west, north, east")
    zones: list[RiskZone]
    source: str
    updated_at: datetime
