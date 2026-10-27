from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Incident(Base):
    """
    SQLAlchemy model for citizen-reported flood incidents and municipal review status.
    Provides indexing for spatial lookups, temporal queries, severity, and verification status.
    """
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    incident_category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="MODERATE")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reporter_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    reporter_contact: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    has_image: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    image_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(32), default="PENDING_REVIEW", nullable=False)
    data_status: Mapped[str] = mapped_column(String(32), default="PUBLIC_UNVERIFIED_REPORT", nullable=False)
    duplicate_of_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    report_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    client_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_incidents_spatial", "latitude", "longitude"),
        Index("ix_incidents_status_cat", "verification_status", "incident_category"),
        Index("ix_incidents_created_at_desc", created_at.desc()),
        Index("ix_incidents_severity", "severity"),
        Index("ix_incidents_duplicate_of", "duplicate_of_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "address": self.address,
            "location_name": self.location_name,
            "incident_category": self.incident_category,
            "category": self.incident_category,
            "severity": self.severity,
            "description": self.description,
            "reporter_name": self.reporter_name,
            "reporter_contact": self.reporter_contact,
            "has_image": self.has_image,
            "image_url": None,
            "verification_status": self.verification_status,
            "status": self.verification_status,
            "data_status": self.data_status,
            "duplicate_of_id": self.duplicate_of_id,
            "duplicate_of": self.duplicate_of_id,
            "report_count": self.report_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "verification_note": self.verification_note or "Citizen-submitted public report.",
            "reviewer_notes": self.verification_note,
        }
