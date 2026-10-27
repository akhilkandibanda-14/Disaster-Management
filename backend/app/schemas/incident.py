from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config import is_in_hyderabad

FLOOD_INCIDENT_CATEGORIES = {
    "WATERLOGGING",
    "ROAD_SUBMERGED",
    "DRAINAGE_OVERFLOW",
    "DRAIN_OVERFLOW",
    "RIVER_SPILL",
    "RIVER_OVERFLOW",
    "FLASH_FLOOD",
    "STRANDED_PERSONS",
    "INFRASTRUCTURE_DAMAGE",
    "OTHER_FLOOD"
}

INCIDENT_SEVERITY_LEVELS = {
    "LOW",
    "MODERATE",
    "HIGH",
    "CRITICAL"
}

VERIFICATION_STATUSES = {
    "PENDING_REVIEW",
    "VERIFIED_MUNICIPAL",
    "REJECTED",
    "RESOLVED"
}


class IncidentCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    latitude: float = Field(..., ge=-90.0, le=90.0, description="Incident latitude coordinate")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Incident longitude coordinate")
    address: Optional[str] = Field(None, max_length=200, description="Street address or local landmark in Hyderabad")
    location_name: Optional[str] = Field(None, max_length=200, description="Optional colloquial landmark name")
    incident_category: str = Field(
        ...,
        description="Flood incident category (WATERLOGGING, ROAD_SUBMERGED, DRAINAGE_OVERFLOW, DRAIN_OVERFLOW, RIVER_SPILL, RIVER_OVERFLOW, FLASH_FLOOD, STRANDED_PERSONS, INFRASTRUCTURE_DAMAGE, OTHER_FLOOD)"
    )
    severity: str = Field(
        default="MODERATE",
        description="Assessed severity (LOW, MODERATE, HIGH, CRITICAL)"
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Detailed description of flood condition (10-1000 chars)"
    )
    reporter_name: Optional[str] = Field(None, max_length=100, description="Optional reporter name (kept private)")
    reporter_contact: Optional[str] = Field(None, max_length=50, description="Optional phone or email for disaster dispatch (kept private)")
    image_data: Optional[str] = Field(None, description="Optional base64 image data URI (JPEG, PNG, or WebP up to 5MB)")

    @model_validator(mode="before")
    @classmethod
    def map_category_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "category" in data and "incident_category" not in data:
                data = dict(data)
                data["incident_category"] = data["category"]
        return data

    @field_validator("incident_category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        norm = v.strip().upper()
        if norm not in FLOOD_INCIDENT_CATEGORIES:
            raise ValueError(
                f"Invalid incident category '{v}'. Allowed flood categories: {', '.join(sorted(FLOOD_INCIDENT_CATEGORIES))}."
            )
        return norm

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        norm = v.strip().upper()
        if norm not in INCIDENT_SEVERITY_LEVELS:
            raise ValueError(
                f"Invalid severity '{v}'. Allowed levels: {', '.join(sorted(INCIDENT_SEVERITY_LEVELS))}."
            )
        return norm

    @field_validator("description")
    @classmethod
    def sanitize_description(cls, v: str) -> str:
        clean = v.replace("<", "").replace(">", "").strip()
        if len(clean) < 10:
            raise ValueError("Incident description must contain at least 10 meaningful characters.")
        return clean

    @field_validator("latitude", "longitude")
    @classmethod
    def validate_location(cls, v, info):
        # Coordinates checked individually; combined check in model_validator if needed
        return v


class IncidentStatusUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    verification_status: str = Field(
        ...,
        description="New verification status (PENDING_REVIEW, VERIFIED_MUNICIPAL, REJECTED, RESOLVED)"
    )
    verification_note: Optional[str] = Field(
        None,
        max_length=500,
        description="Operational review notes"
    )
    duplicate_of_id: Optional[str] = Field(
        None,
        description="Optional parent incident ID if marked as duplicate"
    )

    @model_validator(mode="before")
    @classmethod
    def map_status_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if "status" in data and "verification_status" not in data:
                data["verification_status"] = data["status"]
            if "reviewer_notes" in data and "verification_note" not in data:
                data["verification_note"] = data["reviewer_notes"]
            if "notes" in data and "verification_note" not in data:
                data["verification_note"] = data["notes"]
            if "duplicate_of" in data and "duplicate_of_id" not in data:
                data["duplicate_of_id"] = data["duplicate_of"]
        return data

    @field_validator("verification_status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        norm = v.strip().upper()
        if norm not in VERIFICATION_STATUSES:
            raise ValueError(
                f"Invalid status '{v}'. Allowed statuses: {', '.join(sorted(VERIFICATION_STATUSES))}."
            )
        return norm


class IncidentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str = Field(..., description="Unique incident identifier (e.g. INC-2026-001)")
    latitude: float
    longitude: float
    address: Optional[str] = None
    location_name: Optional[str] = None
    incident_category: str
    category: Optional[str] = None
    severity: str
    description: str
    reporter_contact: Optional[str] = None
    has_image: bool = False
    image_url: Optional[str] = None
    verification_status: str = Field(
        default="PENDING_REVIEW",
        description="PENDING_REVIEW, VERIFIED_MUNICIPAL, REJECTED, RESOLVED"
    )
    status: Optional[str] = None
    data_status: Literal["PUBLIC_UNVERIFIED_REPORT", "VERIFIED_MUNICIPAL", "RESOLVED_INCIDENT"] = "PUBLIC_UNVERIFIED_REPORT"
    duplicate_of_id: Optional[str] = None
    duplicate_of: Optional[str] = None
    report_count: int = 1
    created_at: datetime
    updated_at: datetime
    verified_at: Optional[datetime] = None
    verification_note: str = Field(
        default="Citizen-submitted public report. Has not yet been physically verified by emergency services.",
        description="Status note explaining provenance and verification"
    )
    reviewer_notes: Optional[str] = None

    @model_validator(mode="after")
    def populate_aliases(self) -> "IncidentResponse":
        if self.category is None:
            self.category = self.incident_category
        if self.status is None:
            self.status = self.verification_status
        if self.duplicate_of is None:
            self.duplicate_of = self.duplicate_of_id
        if self.reviewer_notes is None:
            self.reviewer_notes = self.verification_note
        return self


class IncidentListResponse(BaseModel):
    total: int
    pending_count: int
    verified_count: int
    resolved_count: int
    incidents: List[IncidentResponse]
    retrieved_at: datetime
    data_disclaimer: str = Field(
        default="Citizen incident reports represent crowdsourced observations. They are strictly unverified until confirmed by GHMC DRF or municipal response teams. Always rely primarily on authoritative alerts for life-safety decisions.",
        description="Citizen science and safety disclosure"
    )
