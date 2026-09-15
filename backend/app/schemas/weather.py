from datetime import datetime

from pydantic import BaseModel, Field


class WeatherResponse(BaseModel):
    latitude: float
    longitude: float
    rainfall: float = Field(ge=0)
    temperature: float
    humidity: float = Field(ge=0, le=100)
    wind_speed: float = Field(ge=0)
    pressure: float = Field(ge=0)
    condition: str
    source: str
    timestamp: datetime
    forecast_available: bool
    warning: str | None = None
