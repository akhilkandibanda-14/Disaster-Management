from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ShelterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    latitude: float
    longitude: float
    capacity: int
    available_capacity: int
    status: str
    accessibility: str
    contact: str | None
    risk_level: str
    last_updated: datetime


class RoadConditionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    road_name: str
    status: str
    latitude: float
    longitude: float
    notes: str | None
    last_updated: datetime


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    disaster_type: str
    severity: str
    affected_area: str
    source: str
    description: str
    issued_at: datetime
