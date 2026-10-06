from pydantic import BaseModel, Field
from typing import Optional

class PredictionRequest(BaseModel):
    latitude: float
    longitude: float
    rainfall: float
    temperature: float
    humidity: float
    river_discharge: float
    water_level: float
    elevation: float
    land_cover: str
    soil_type: str
    population_density: float
    infrastructure: float
    historical_floods: float

class IndofloodsModelInput(BaseModel):
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
    annual_mean_temperature: Optional[float] = None
    land_cover: Optional[str] = "Unknown"
    soil_type: Optional[str] = "Unknown"
    population_density: Optional[float] = None
    mean_basin_elevation: Optional[float] = None
    # Can add other features here as needed

class PredictionResponse(BaseModel):
    prediction: Optional[int] = None
    flood_probability: Optional[float] = None
    risk_level: Optional[str] = None
    source: str
    message: Optional[str] = None
    severe_flood_probability: Optional[float] = None
    model_name: Optional[str] = None
    model_version_status: Optional[str] = None
