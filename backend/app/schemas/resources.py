from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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



ALLOWED_FLOOD_DISASTER_TYPES = {
    "FLOOD",
    "FLASH_FLOOD",
    "URBAN_INUNDATION",
    "WATERLOGGING",
    "RIVER_OVERFLOW",
    "FLOOD_RELATED_HEAVY_RAINFALL",
}

DISALLOWED_NON_FLOOD_DISASTER_TYPES = {
    "TSUNAMI",
    "EARTHQUAKE",
    "CYCLONE",
    "HURRICANE",
    "TYPHOON",
    "WILDFIRE",
    "LANDSLIDE",
    "DROUGHT",
    "TORNADO",
    "VOLCANO",
}


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    disaster_type: str = Field(..., description="Flood disaster type (e.g. FLOOD, URBAN_INUNDATION, RIVER_OVERFLOW)")
    severity: str
    affected_area: str
    source: str
    description: str
    issued_at: datetime

    @field_validator("disaster_type")
    @classmethod
    def validate_flood_disaster_type(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("disaster_type must be a non-empty string")
        norm = v.strip().upper()
        if norm in DISALLOWED_NON_FLOOD_DISASTER_TYPES:
            raise ValueError(
                f"Unsupported non-flood disaster type: '{v}'. "
                f"SafeMap AI is restricted exclusively to flood management."
            )
        if norm not in ALLOWED_FLOOD_DISASTER_TYPES:
            raise ValueError(
                f"Invalid disaster type '{v}'. Supported flood types: "
                f"{', '.join(sorted(ALLOWED_FLOOD_DISASTER_TYPES))}."
            )
        return norm
