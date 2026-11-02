from typing import List, Optional
from pydantic import BaseModel, Field


class NearbyHospitalCandidate(BaseModel):
    facility_id: str = Field(..., description="Unique identifier for the hospital POI (e.g., OSM-NODE-2451987301)")
    name: str = Field(..., description="Hospital or medical facility name")
    latitude: float = Field(..., ge=-90, le=90, description="WGS84 latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="WGS84 longitude coordinate")
    distance_km: float = Field(..., ge=0, description="Straight-line distance from user origin in kilometers")
    source: str = Field(default="OpenStreetMap (OSM POI)", description="Authoritative catalog or POI data provider")
    facility_type: str = Field(default="HOSPITAL", description="Facility classification: HOSPITAL or CLINIC")
    data_status: str = Field(default="PUBLIC_UNVERIFIED", description="Data integrity status")
    verification_status: str = Field(default="UNVERIFIED", description="Field validation status")
    operational_status: str = Field(default="UNKNOWN", description="Operational readiness (UNKNOWN unless confirmed)")
    capacity: Optional[float] = Field(default=None, description="Bed/patient capacity (None unless verified)")
    operational_status_verified: bool = Field(default=False, description="Whether live casualty/triage intake is verified")
    capacity_verified: bool = Field(default=False, description="Whether bed capacity is verified in real time")
    verification_note: str = Field(
        default="OpenStreetMap candidate. Not verified for live casualty intake, open status, or bed capacity. Confirm before travel.",
        description="Public safety disclosure regarding verification limitations"
    )
    address: Optional[str] = Field(default=None, description="Street address if mapped")
    area: Optional[str] = Field(default=None, description="Locality or neighborhood in Hyderabad")
    phone: Optional[str] = Field(default=None, description="Contact phone number if mapped")


class NearbyHospitalDiscoveryResponse(BaseModel):
    hospitals: List[NearbyHospitalCandidate] = Field(default_factory=list, description="Sorted list of nearby hospital candidates")
    total: int = Field(default=0, description="Total number of candidates discovered within radius")
    origin_latitude: float = Field(..., description="Origin latitude used for query")
    origin_longitude: float = Field(..., description="Origin longitude used for query")
    radius_km: float = Field(..., description="Search radius in kilometers")
    source: str = Field(default="OpenStreetMap", description="Primary data source")
    data_status: str = Field(default="PUBLIC_UNVERIFIED", description="Dataset integrity status")
    disclaimer: str = Field(
        default="Hospital candidates discovered from OpenStreetMap. Facility operational readiness, triage status, and casualty capacity are NOT verified in real time. Confirm availability before travel.",
        description="Public safety disclaimer"
    )
    warning: Optional[str] = Field(default=None, description="Operational warning if upstream provider degraded or cached data used")

