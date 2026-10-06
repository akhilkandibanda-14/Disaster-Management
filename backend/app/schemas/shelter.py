from pydantic import BaseModel
from typing import Optional, List

class Shelter(BaseModel):
    shelter_id: str
    name: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    area: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    capacity: Optional[float] = None
    current_occupancy: Optional[float] = None
    operational_status: Optional[str] = None
    accessibility: Optional[str] = None
    shelter_type: Optional[str] = None
    contact: Optional[float] = None
    source: Optional[str] = None
    last_updated: Optional[str] = None
    data_status: Optional[str] = None
    verification_note: Optional[str] = None
    
    distance_km: Optional[float] = None

class ShelterResponse(BaseModel):
    shelters: List[Shelter]
    total: int
