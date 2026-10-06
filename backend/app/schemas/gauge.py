from pydantic import BaseModel
from typing import Dict, Any, Optional

class Coordinates(BaseModel):
    latitude: float
    longitude: float

class ReferenceGauge(BaseModel):
    gauge_id: str
    latitude: float
    longitude: float

class NearestGaugeResponse(BaseModel):
    user_location: Coordinates
    reference_gauge: Optional[ReferenceGauge]
    distance_km: Optional[float]
    max_allowed_distance_km: float
    within_model_coverage: bool
    message: Optional[str] = None
    gauge_features: Optional[Dict[str, Any]] = None
