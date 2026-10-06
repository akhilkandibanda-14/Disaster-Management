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

from datetime import date
from typing import Dict, Any

class IntegratedPredictionRequest(BaseModel):
    latitude: float
    longitude: float
    target_date: date

class LocationResponse(BaseModel):
    latitude: float
    longitude: float

class ReferenceGaugeResponse(BaseModel):
    gauge_id: str
    latitude: float
    longitude: float

class RainfallResponse(BaseModel):
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

class DataSourcesResponse(BaseModel):
    rainfall: str
    environmental: str

class ModelInfoResponse(BaseModel):
    name: str
    raw_features: int
    processed_features: int

class CoverageStatusResponse(BaseModel):
    status: str
    reference_gauge: Optional[str] = None
    distance_km: Optional[float] = None
    maximum_distance_km: float

class IntegratedPredictionResponse(BaseModel):
    prediction_available: bool
    coverage_status: Optional[str] = None
    coverage: Optional[CoverageStatusResponse] = None
    prediction: Optional[int] = None
    risk_level: Optional[str] = None
    failure_probability: Optional[float] = None
    confidence: Optional[float] = None
    message: Optional[str] = None
    location: LocationResponse
    target_date: date
    nearest_gauge: Optional[str] = None
    reference_gauge: Optional[ReferenceGaugeResponse] = None
    gauge_distance_km: Optional[float] = None
    maximum_supported_distance_km: Optional[float] = None
    rainfall: Optional[RainfallResponse] = None
    data_sources: Optional[DataSourcesResponse] = None
    model: Optional[ModelInfoResponse] = None
