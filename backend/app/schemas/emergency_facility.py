from pydantic import BaseModel, Field
from typing import Optional, List


class EmergencyFacility(BaseModel):
    facility_id: str
    name: str
    facility_type: str = Field(description="HOSPITAL, SHELTER, EMERGENCY_CENTER")
    latitude: float
    longitude: float
    address: Optional[str] = None
    area: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    capacity: Optional[float] = None
    current_occupancy: Optional[float] = None
    operational_status: Optional[str] = "UNKNOWN"
    accessibility: Optional[str] = None
    contact: Optional[str] = None
    source: str
    last_verified: Optional[str] = None
    data_status: str = Field(default="PUBLIC_UNVERIFIED", description="PUBLIC_UNVERIFIED, VERIFIED, or DEMO")
    verification_note: Optional[str] = None
    distance_km: Optional[float] = None
    # Milestone 9: Granular verification distinction
    location_verified: bool = Field(
        default=False,
        description="True if physical facility existence and coordinates are verified against official registries."
    )
    operational_status_verified: bool = Field(
        default=False,
        description="True only if live emergency operational status is verified by field telemetry or official dispatch."
    )
    capacity_verified: bool = Field(
        default=False,
        description="True only if live bed occupancy or available space is verified in real-time."
    )
    verification_scope: str = Field(
        default="IDENTITY_ONLY",
        description="Scope of verification: IDENTITY_ONLY, FULL_REAL_TIME, or UNVERIFIED."
    )


class EmergencyFacilityListResponse(BaseModel):
    facilities: List[EmergencyFacility]
    total: int
    location_verified_count: int = Field(0, description="Facilities with verified physical location")
    operational_status_verified_count: int = Field(0, description="Facilities with verified live operational status")
    capacity_verified_count: int = Field(0, description="Facilities with verified live capacity/bed occupancy")
    unverified_status_count: int = Field(0, description="Facilities where live operational status is unverified")
    unverified_capacity_count: int = Field(0, description="Facilities where bed/space capacity is unverified")
    data_disclaimer: str = (
        "Facility identities and coordinates are verified against official municipal/health registries. "
        "However, real-time bed availability, live occupancy, and emergency flood operational status "
        "are NOT verified in real-time. Unverified capacity or status must never be assumed safe without direct confirmation."
    )


class VerificationPromotionRequest(BaseModel):
    """
    Authorized administrator request to promote or update facility verification state.
    Strictly requires documented evidence source.
    """
    operational_status_verified: Optional[bool] = None
    capacity_verified: Optional[bool] = None
    operational_status: Optional[str] = None
    capacity: Optional[float] = None
    data_status: Optional[str] = None
    verification_evidence_source: str = Field(
        ...,
        min_length=5,
        description="Official traceable evidence citation supporting the verification update."
    )
    verification_note: Optional[str] = None

