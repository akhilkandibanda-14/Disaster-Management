from datetime import datetime

from pydantic import BaseModel, Field


class WeatherResponse(BaseModel):
    latitude: float
    longitude: float
    temperature: float
    humidity: float = Field(ge=0, le=100)
    rainfall: float | None = Field(default=None, ge=0)
    wind_speed: float = Field(ge=0)
    weather_condition: str
    weather_description: str
    pressure: float | None = None
    source: str
    timestamp: datetime
    forecast_available: bool = False
    warning: str | None = None
