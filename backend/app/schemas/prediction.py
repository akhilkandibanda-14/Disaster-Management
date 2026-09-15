from datetime import datetime

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    rainfall: float = Field(ge=0)
    temperature: float
    humidity: float = Field(ge=0, le=100)
    water_level: float = Field(ge=0)
    elevation: float


class PredictionResponse(PredictionRequest):
    flood_probability: float = Field(ge=0, le=1)
    risk_level: str
    source: str
    timestamp: datetime
