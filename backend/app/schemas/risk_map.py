from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class DataSourceInfo(BaseModel):
    rainfall: str
    environmental: str

class ModelInfo(BaseModel):
    name: str
    raw_features: int
    processed_features: int

class GeographicRiskResponse(BaseModel):
    latitude: float
    longitude: float
    gauge_id: Optional[str] = None
    distance_km: Optional[float] = None
    coverage_status: str
    prediction_available: bool
    predicted_class: Optional[int] = None
    risk_level: Optional[str] = None
    predicted_severe_flood_probability: Optional[float] = None
    data_sources: Optional[DataSourceInfo] = None
    model_info: Optional[ModelInfo] = None
    timestamp: datetime

class GaugePoint(BaseModel):
    gauge_id: str
    latitude: float
    longitude: float

class GaugesResponse(BaseModel):
    gauges: List[GaugePoint]
