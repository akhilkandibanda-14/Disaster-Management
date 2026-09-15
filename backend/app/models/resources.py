from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Shelter(Base):
    __tablename__ = "shelters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    capacity: Mapped[int] = mapped_column(Integer)
    available_capacity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="OPEN")
    accessibility: Mapped[str] = mapped_column(String(32), default="STANDARD")
    contact: Mapped[str | None] = mapped_column(String(80), nullable=True)
    risk_level: Mapped[str] = mapped_column(String(16), default="LOW")
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RoadCondition(Base):
    __tablename__ = "road_conditions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    road_name: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(32), default="OPEN")
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    disaster_type: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16))
    affected_area: Mapped[str] = mapped_column(String(160))
    source: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
