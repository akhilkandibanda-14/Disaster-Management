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
    data_readiness_status: Optional[str] = Field(
        default=None, 
        description="Truth in data readiness: INSUFFICIENT_LOCAL_DATA, MODEL_UNSUPPORTED, DATA_UNAVAILABLE, or SUPPORTED"
    )
    provenance_note: Optional[str] = Field(
        default=None,
        description="Clear explanation of gauge distance, local training data absence, and why predictions are suppressed"
    )
    nearest_gauge_distance_km: Optional[float] = None
    coverage_limit_km: float = 50.0
    gauges_within_50km_count: int = Field(
        default=0,
        description="Number of calibrated INDOFLOODS gauges within the 50 km geographic model coverage limit"
    )
    catchment_gauges_count: int = Field(
        default=0,
        description="Legacy field alias for gauges within coverage radius (radial proximity, not topological watershed)"
    )
    safety_disclaimer: Optional[str] = Field(
        default=None,
        description="Mandatory notice stating that missing predictions do NOT imply safety"
    )

class GaugePoint(BaseModel):
    gauge_id: str
    latitude: float
    longitude: float

class GaugesResponse(BaseModel):
    gauges: List[GaugePoint]
