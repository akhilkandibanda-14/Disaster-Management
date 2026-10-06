from pydantic import BaseModel
from typing import List, Optional
from app.schemas.shelter import Shelter

class RequestLocation(BaseModel):
    latitude: float
    longitude: float

class RiskContext(BaseModel):
    prediction_available: bool
    coverage_status: str
    risk_level: Optional[str] = None
    predicted_class: Optional[int] = None

class RecommendedShelter(Shelter):
    rank: int
    candidate_score: float
    safety_status: str = "NOT_VERIFIED"
    
class ShelterRecommendationResponse(BaseModel):
    request_location: RequestLocation
    risk_context: RiskContext
    recommendations: List[RecommendedShelter]
    limitations: List[str]
