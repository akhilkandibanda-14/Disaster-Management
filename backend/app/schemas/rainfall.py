from datetime import date
from pydantic import BaseModel, Field

class AntecedentRainfallResponse(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    target_date: date
    data_source: str = "Open-Meteo Historical API"
    data_type: str = "reanalysis/model-derived"
    rainfall_unit: str = "mm"
    
    T1d: float
    T2d: float
    T3d: float
    T4d: float
    T5d: float
    T6d: float
    T7d: float
    T8d: float
    T9d: float
    T10d: float
    
    daily_rainfall_values: dict[str, float | None] | None = None
