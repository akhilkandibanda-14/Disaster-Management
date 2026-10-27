import json
import logging
import math
import os
import re
import uuid
from collections import deque
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.config import is_in_hyderabad, settings
from app.database import SessionLocal, check_db_connectivity
from app.models.incident import Incident
from app.schemas.incident import (
    FLOOD_INCIDENT_CATEGORIES,
    INCIDENT_SEVERITY_LEVELS,
    IncidentCreate,
    IncidentListResponse,
    IncidentResponse,
    IncidentStatusUpdate,
)

VALID_CATEGORIES = FLOOD_INCIDENT_CATEGORIES
VALID_SEVERITIES = INCIDENT_SEVERITY_LEVELS

logger = logging.getLogger(__name__)

DUPLICATE_RADIUS_KM = 0.15  # 150 meters
DUPLICATE_WINDOW_HOURS = 3.0
MAX_SUBMISSIONS_PER_MINUTE = 5


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two coordinates in kilometers."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


class IncidentService:
    """
    Manages citizen flood incident submissions, abuse protection,
    spatial duplicate correlation, privacy protection, and operational review.
    Supports PostgreSQL persistence with transactional integrity and concurrency safety.
    """

    def __init__(self, storage_path: Optional[str] = None):
        base_dir = Path(__file__).resolve().parents[2]
        self.data_dir = base_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.storage_file = Path(storage_path) if storage_path else self.data_dir / "incidents.json"
        self.rate_limit_tracker: Dict[str, deque] = {}
        self.incidents: Dict[str, Dict[str, Any]] = {}
        self._load_fallback_storage()

    def _is_db_available(self, db: Optional[Session] = None) -> bool:
        """Checks if a valid database connection is available."""
        if db is not None:
            return True
        probe = check_db_connectivity()
        return probe["status"] == "connected"

    def _load_fallback_storage(self) -> None:
        """Loads incidents from persistent JSON file for offline/fallback mode."""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.incidents = {item["id"]: item for item in data}
                    logger.info(f"Loaded {len(self.incidents)} incident report(s) from {self.storage_file}")
                    return
            except Exception as e:
                logger.error(f"Failed to load incidents file {self.storage_file}: {e}")

        # Initialize realistic seed reports for Hyderabad flood management if file not present
        now = datetime.now(timezone.utc)
        seeds = [
            {
                "id": "INC-2026-001",
                "latitude": 17.3789,
                "longitude": 78.4892,
                "address": "Chaderghat Causeway, Musi River Corridor",
                "incident_category": "RIVER_SPILL",
                "severity": "HIGH",
                "description": "Musi river water level rising rapidly. Causeway bridge submerged under 1.2 feet of flowing water. Police barricades placed.",
                "has_image": True,
                "image_url": None,
                "verification_status": "VERIFIED_MUNICIPAL",
                "data_status": "VERIFIED_MUNICIPAL",
                "duplicate_of_id": None,
                "report_count": 4,
                "created_at": (now - timedelta(hours=2)).isoformat(),
                "updated_at": (now - timedelta(minutes=45)).isoformat(),
                "verification_note": "Verified by GHMC Disaster Response Force (DRF) Unit 4. Causeway closed to all vehicular traffic.",
                "reporter_name": "[CONFIDENTIAL]",
                "reporter_contact": "[REDACTED]"
            },
            {
                "id": "INC-2026-002",
                "latitude": 17.3971,
                "longitude": 78.4118,
                "address": "Tolichowki Flyover Underpass, Gachibowli Road",
                "incident_category": "WATERLOGGING",
                "severity": "MODERATE",
                "description": "Severe storm water stagnation beneath Tolichowki flyover. Knee-deep water obstructing two-wheeler traffic in service lane.",
                "has_image": False,
                "image_url": None,
                "verification_status": "PENDING_REVIEW",
                "data_status": "PUBLIC_UNVERIFIED_REPORT",
                "duplicate_of_id": None,
                "report_count": 2,
                "created_at": (now - timedelta(hours=1, minutes=15)).isoformat(),
                "updated_at": (now - timedelta(minutes=20)).isoformat(),
                "verification_note": "Citizen-submitted public report. Has not yet been physically verified by emergency services.",
                "reporter_name": "[CONFIDENTIAL]",
                "reporter_contact": "[REDACTED]"
            },
            {
                "id": "INC-2026-003",
                "latitude": 17.4424,
                "longitude": 78.4745,
                "address": "Rasoolpura Junction & Prakash Nagar Subway",
                "incident_category": "ROAD_SUBMERGED",
                "severity": "HIGH",
                "description": "Prakash Nagar subway flooded with 2.5 feet of accumulated water. Vehicular movement completely suspended by traffic police.",
                "has_image": True,
                "image_url": None,
                "verification_status": "VERIFIED_MUNICIPAL",
                "data_status": "VERIFIED_MUNICIPAL",
                "duplicate_of_id": None,
                "report_count": 7,
                "created_at": (now - timedelta(hours=3)).isoformat(),
                "updated_at": (now - timedelta(hours=1)).isoformat(),
                "verification_note": "Verified by Hyderabad Traffic Police & GHMC Monsoon Emergency Team. Diversion active via Begumpet main flyover.",
                "reporter_name": "[CONFIDENTIAL]",
                "reporter_contact": "[REDACTED]"
            },
            {
                "id": "INC-2026-004",
                "latitude": 17.4350,
                "longitude": 78.4480,
                "address": "Panjagutta Main Junction, Near Central Mall",
                "incident_category": "WATERLOGGING",
                "severity": "MODERATE",
                "description": "Drain grate blocked by plastic debris. 8-10 inches of waterlogging on left lane causing heavy traffic tailback toward Banjara Hills.",
                "has_image": False,
                "image_url": None,
                "verification_status": "RESOLVED",
                "data_status": "RESOLVED_INCIDENT",
                "duplicate_of_id": None,
                "report_count": 3,
                "created_at": (now - timedelta(hours=5)).isoformat(),
                "updated_at": (now - timedelta(minutes=30)).isoformat(),
                "verification_note": "Resolved: GHMC emergency de-silting crew cleared catch-pit gratings. Road water receded, traffic flowing normally.",
                "reporter_name": "[CONFIDENTIAL]",
                "reporter_contact": "[REDACTED]"
            },
            {
                "id": "INC-2026-005",
                "latitude": 17.4116,
                "longitude": 78.4593,
                "address": "Khairatabad RTA Office Road",
                "incident_category": "DRAINAGE_OVERFLOW",
                "severity": "MODERATE",
                "description": "Major storm drain overflowing onto road surface. Foul water entering commercial basements. Monsoon teams notified.",
                "has_image": False,
                "image_url": None,
                "verification_status": "PENDING_REVIEW",
                "data_status": "PUBLIC_UNVERIFIED_REPORT",
                "duplicate_of_id": None,
                "report_count": 1,
                "created_at": (now - timedelta(minutes=40)).isoformat(),
                "updated_at": (now - timedelta(minutes=40)).isoformat(),
                "verification_note": "Citizen-submitted public report. Has not yet been physically verified by emergency services.",
                "reporter_name": "[CONFIDENTIAL]",
                "reporter_contact": "[REDACTED]"
            }
        ]
        self.incidents = {item["id"]: item for item in seeds}
        self._save_fallback_storage()

    def _save_fallback_storage(self) -> None:
        """Saves current state to local JSON file for backward compatibility."""
        try:
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(list(self.incidents.values()), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to persist incidents to {self.storage_file}: {e}")

    def check_rate_limit(self, client_ip: str) -> bool:
        """Enforces sliding-window rate limit (max 5 submissions per minute per IP)."""
        now = datetime.now(timezone.utc)
        one_min_ago = now - timedelta(minutes=1)

        if client_ip not in self.rate_limit_tracker:
            self.rate_limit_tracker[client_ip] = deque()

        queue = self.rate_limit_tracker[client_ip]
        while queue and queue[0] < one_min_ago:
            queue.popleft()

        if len(queue) >= MAX_SUBMISSIONS_PER_MINUTE:
            return False

        queue.append(now)
        return True

    def validate_image_data(self, image_data: Optional[str]) -> bool:
        """Validates base64 data URI format and payload size (< 5MB)."""
        if not image_data:
            return True
        if len(image_data) > 7_000_000:  # ~5MB binary base64 encoded
            return False
        if image_data.startswith("data:image/"):
            valid_mimes = ("data:image/jpeg", "data:image/png", "data:image/webp", "data:image/jpg")
            return any(image_data.startswith(m) for m in valid_mimes)
        return False

    def _find_duplicate_db(
        self,
        db: Session,
        lat: float,
        lon: float,
        category: str,
        now: datetime
    ) -> Optional[str]:
        """
        Concurrency-safe spatial duplicate detection in PostgreSQL/SQLAlchemy.
        Queries recent reports within spatial delta box and checks Haversine distance < 150m.
        """
        window_start = now - timedelta(hours=DUPLICATE_WINDOW_HOURS)
        delta_deg = 0.003  # ~300 meters bounding box filter for index acceleration

        stmt = select(Incident).where(
            Incident.created_at >= window_start,
            Incident.latitude.between(lat - delta_deg, lat + delta_deg),
            Incident.longitude.between(lon - delta_deg, lon + delta_deg),
            func.upper(Incident.incident_category) == category.upper(),
        ).order_by(Incident.created_at.asc())

        # If PostgreSQL, use with_for_update() to lock candidates and prevent race conditions
        try:
            if db.bind and db.bind.dialect.name == "postgresql":
                stmt = stmt.with_for_update()
        except Exception:
            pass

        candidates = db.scalars(stmt).all()
        for cand in candidates:
            dist = haversine_distance_km(lat, lon, cand.latitude, cand.longitude)
            if dist <= DUPLICATE_RADIUS_KM:
                return cand.id
        return None

    def _generate_next_id_db(self, db: Session, now: datetime) -> str:
        """Generates sequential incident identifier in database (e.g. INC-2026-001)."""
        year = now.strftime("%Y")
        prefix = f"INC-{year}-"
        count = db.scalar(select(func.count(Incident.id)).where(Incident.id.like(f"{prefix}%"))) or 0
        seq = count + 1
        new_id = f"{prefix}{seq:03d}"
        # Ensure absolute uniqueness if prior deleted or fragmented sequences exist
        while db.scalar(select(Incident.id).where(Incident.id == new_id)):
            seq += 1
            new_id = f"{prefix}{seq:03d}"
        return new_id

    def create_incident(
        self, 
        data: IncidentCreate, 
        client_ip: str, 
        db: Optional[Session] = None
    ) -> IncidentResponse:
        """
        Creates, validates, and stores a citizen flood incident report.
        Enforces geographic boundary checks, rate-limiting, privacy masking,
        and automatic duplicate correlation with PostgreSQL persistence.
        """
        # 1. Geographic boundary verification
        if not is_in_hyderabad(data.latitude, data.longitude):
            raise ValueError(
                f"Incident location ({data.latitude:.4f}, {data.longitude:.4f}) is outside "
                f"the Greater Hyderabad municipal boundary. SafeMap AI operates exclusively within Hyderabad."
            )

        # 2. Rate limit check
        if not self.check_rate_limit(client_ip):
            raise PermissionError("Submission rate limit exceeded. Please wait a moment before submitting another incident report.")

        # 3. Image validation
        has_image = False
        if data.image_data:
            if not self.validate_image_data(data.image_data):
                raise ValueError("Attached image must be a valid JPEG, PNG, or WebP image under 5 MB.")
            has_image = True

        # 4. Privacy protection: sanitize phone and email occurrences
        clean_desc = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[REDACTED_EMAIL]', data.description)
        clean_desc = re.sub(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+?\d{10,13}', '[REDACTED_PHONE]', clean_desc)

        clean_contact = "[REDACTED]"
        if data.reporter_contact:
            clean_contact = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[REDACTED_EMAIL]', data.reporter_contact)
            clean_contact = re.sub(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+?\d{10,13}', '[REDACTED_PHONE]', clean_contact)

        now = datetime.now(timezone.utc)

        # 5. Database execution path
        if db is not None or self._is_db_available():
            session = db or SessionLocal()
            close_session = (db is None)
            try:
                # Concurrency-safe duplicate correlation
                duplicate_id = self._find_duplicate_db(session, data.latitude, data.longitude, data.incident_category, now)
                
                if duplicate_id:
                    parent = session.scalar(select(Incident).where(Incident.id == duplicate_id))
                    if parent:
                        parent.report_count += 1
                        parent.updated_at = now

                new_id = self._generate_next_id_db(session, now)

                incident_model = Incident(
                    id=new_id,
                    latitude=round(data.latitude, 6),
                    longitude=round(data.longitude, 6),
                    address=data.address or data.location_name or "Hyderabad Municipal Location",
                    location_name=data.location_name or data.address,
                    incident_category=data.incident_category,
                    severity=data.severity,
                    description=clean_desc,
                    reporter_name=data.reporter_name or "[ANONYMOUS]",
                    reporter_contact=clean_contact,
                    has_image=has_image,
                    image_data=data.image_data if has_image else None,
                    verification_status="PENDING_REVIEW",
                    data_status="PUBLIC_UNVERIFIED_REPORT",
                    duplicate_of_id=duplicate_id,
                    report_count=1,
                    created_at=now,
                    updated_at=now,
                    verification_note="Citizen-submitted public report. Has not yet been physically verified by emergency services.",
                    client_ip=client_ip,
                )

                session.add(incident_model)
                session.commit()
                session.refresh(incident_model)

                # Keep local mirror up to date
                self.incidents[new_id] = incident_model.to_dict()
                if duplicate_id and duplicate_id in self.incidents:
                    self.incidents[duplicate_id]["report_count"] = self.incidents[duplicate_id].get("report_count", 1) + 1
                    self.incidents[duplicate_id]["updated_at"] = now.isoformat()
                self._save_fallback_storage()

                return self._to_response(incident_model.to_dict())
            except (SQLAlchemyError, Exception) as err:
                try:
                    session.rollback()
                except Exception:
                    pass
                logger.error("Database error during incident creation: %s", err)
                if settings.is_production():
                    raise RuntimeError("Production database persistence failed during incident creation.")
                logger.warning("Falling back to local storage due to database error in non-production.")
            finally:
                if close_session:
                    try:
                        session.close()
                    except Exception:
                        pass

        # In production, do not silently fall back to JSON
        if settings.is_production():
            raise RuntimeError("Database connection is required in production environment.")

        # Non-production fallback path (isolated test fixture without active DB)
        duplicate_id = None
        window_start = now - timedelta(hours=DUPLICATE_WINDOW_HOURS)
        for cand in self.incidents.values():
            raw_time = cand.get("created_at")
            if isinstance(raw_time, str):
                cand_time = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
            else:
                cand_time = raw_time
            if cand_time and cand_time.tzinfo is None:
                cand_time = cand_time.replace(tzinfo=timezone.utc)

            if cand_time and cand_time >= window_start and cand.get("incident_category") == data.incident_category:
                dist = haversine_distance_km(data.latitude, data.longitude, cand["latitude"], cand["longitude"])
                if dist <= DUPLICATE_RADIUS_KM:
                    duplicate_id = cand["id"]
                    break

        year = now.strftime("%Y")
        seq = len(self.incidents) + 1
        new_id = f"INC-{year}-{seq:03d}"
        while new_id in self.incidents:
            seq += 1
            new_id = f"INC-{year}-{seq:03d}"

        if duplicate_id and duplicate_id in self.incidents:
            self.incidents[duplicate_id]["report_count"] = self.incidents[duplicate_id].get("report_count", 1) + 1
            self.incidents[duplicate_id]["updated_at"] = now.isoformat()

        record = {
            "id": new_id,
            "latitude": round(data.latitude, 6),
            "longitude": round(data.longitude, 6),
            "address": data.address or data.location_name or "Hyderabad Municipal Location",
            "location_name": data.location_name or data.address,
            "incident_category": data.incident_category,
            "severity": data.severity,
            "description": clean_desc,
            "has_image": has_image,
            "image_url": None,
            "verification_status": "PENDING_REVIEW",
            "data_status": "PUBLIC_UNVERIFIED_REPORT",
            "duplicate_of_id": duplicate_id,
            "report_count": 1,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "verified_at": None,
            "verification_note": "Citizen-submitted public report. Has not yet been physically verified by emergency services.",
            "reporter_name": data.reporter_name or "[ANONYMOUS]",
            "reporter_contact": clean_contact,
            "client_ip": client_ip,
        }
        self.incidents[new_id] = record
        self._save_fallback_storage()
        return self._to_response(record)

    def list_incidents(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> IncidentListResponse:
        """Returns sanitized, privacy-safe list of active incident reports."""
        now = datetime.now(timezone.utc)

        # Database query path
        if db is not None or self._is_db_available():
            session = db or SessionLocal()
            close_session = (db is None)
            try:
                stmt = select(Incident)
                if category:
                    stmt = stmt.where(func.upper(Incident.incident_category) == category.upper())
                if status:
                    stmt = stmt.where(func.upper(Incident.verification_status) == status.upper())
                if severity:
                    stmt = stmt.where(func.upper(Incident.severity) == severity.upper())

                stmt = stmt.order_by(Incident.created_at.desc()).limit(limit)
                records = session.scalars(stmt).all()

                pending_count = session.scalar(select(func.count(Incident.id)).where(Incident.verification_status == "PENDING_REVIEW")) or 0
                verified_count = session.scalar(select(func.count(Incident.id)).where(Incident.verification_status == "VERIFIED_MUNICIPAL")) or 0
                resolved_count = session.scalar(select(func.count(Incident.id)).where(Incident.verification_status == "RESOLVED")) or 0

                items = [self._to_response(r.to_dict()) for r in records]
                return IncidentListResponse(
                    total=len(items),
                    pending_count=pending_count,
                    verified_count=verified_count,
                    resolved_count=resolved_count,
                    incidents=items,
                    retrieved_at=now,
                )
            except (SQLAlchemyError, Exception) as err:
                logger.error("Database query failed in list_incidents: %s", err)
                if settings.is_production():
                    raise RuntimeError("Database query failed.")
            finally:
                if close_session:
                    try:
                        session.close()
                    except Exception:
                        pass

        # Offline/in-memory fallback path
        items = list(self.incidents.values())
        items.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)

        filtered = []
        for inc in items:
            if category and inc.get("incident_category", "").upper() != category.upper():
                continue
            if status and inc.get("verification_status", "").upper() != status.upper():
                continue
            if severity and inc.get("severity", "").upper() != severity.upper():
                continue
            filtered.append(self._to_response(inc))

        pending_count = sum(1 for inc in items if inc.get("verification_status") == "PENDING_REVIEW")
        verified_count = sum(1 for inc in items if inc.get("verification_status") == "VERIFIED_MUNICIPAL")
        resolved_count = sum(1 for inc in items if inc.get("verification_status") == "RESOLVED")

        return IncidentListResponse(
            total=len(filtered[:limit]),
            pending_count=pending_count,
            verified_count=verified_count,
            resolved_count=resolved_count,
            incidents=filtered[:limit],
            retrieved_at=now,
        )

    def get_incident(self, incident_id: str, db: Optional[Session] = None) -> Optional[IncidentResponse]:
        """Retrieves a single sanitized incident report by ID."""
        if db is not None or self._is_db_available():
            session = db or SessionLocal()
            close_session = (db is None)
            try:
                rec = session.scalar(select(Incident).where(Incident.id == incident_id.upper()))
                if rec:
                    return self._to_response(rec.to_dict())
            except (SQLAlchemyError, Exception) as err:
                logger.error("Database lookup failed: %s", err)
            finally:
                if close_session:
                    try:
                        session.close()
                    except Exception:
                        pass

        rec = self.incidents.get(incident_id.upper())
        if not rec:
            return None
        return self._to_response(rec)

    def update_status(
        self, 
        incident_id: str, 
        update: IncidentStatusUpdate,
        db: Optional[Session] = None,
        is_institutional: bool = False,
    ) -> Optional[IncidentResponse]:
        """
        Updates review status and notes for an incident.
        Public callers can only submit community corroboration ('COMMUNITY_CORROBORATED') or resolution ('RESOLVED').
        Official municipal verification ('VERIFIED_MUNICIPAL', 'REJECTED') requires is_institutional=True.
        """
        req_status = update.verification_status.upper()
        if not is_institutional and req_status in ("VERIFIED_MUNICIPAL", "RESOLVED", "REJECTED"):
            raise PermissionError(
                f"Unauthorized provenance escalation / status transition: Public web requests cannot assert '{req_status}'. "
                "Official incident resolution ('RESOLVED') and municipal verification ('VERIFIED_MUNICIPAL') "
                "require authoritative institutional telemetry or emergency dispatch intake."
            )

        now = datetime.now(timezone.utc)

        if db is not None or self._is_db_available():
            session = db or SessionLocal()
            close_session = (db is None)
            try:
                rec = session.scalar(select(Incident).where(Incident.id == incident_id.upper()))
                if not rec:
                    return None

                rec.verification_status = req_status
                rec.updated_at = now

                if req_status == "COMMUNITY_CORROBORATED":
                    rec.data_status = "PUBLIC_UNVERIFIED_REPORT"
                    rec.report_count = (rec.report_count or 1) + 1
                    rec.verification_note = update.verification_note or "Community corroborated: additional citizen confirmation received."
                elif req_status == "COMMUNITY_RESOLUTION_OBSERVED":
                    rec.data_status = "PUBLIC_UNVERIFIED_REPORT"
                    rec.verification_note = update.verification_note or "Citizen observation: floodwater reported receding or drained (awaiting official municipal confirmation)."
                elif req_status == "VERIFIED_MUNICIPAL" and is_institutional:
                    rec.data_status = "VERIFIED_MUNICIPAL"
                    rec.verified_at = now
                    rec.verification_note = update.verification_note or "Verified by municipal disaster response authorities."
                elif req_status == "RESOLVED" and is_institutional:
                    rec.data_status = "RESOLVED_INCIDENT"
                    rec.verification_note = update.verification_note or "Issue resolved and receding (confirmed by emergency services)."
                elif req_status == "REJECTED" and is_institutional:
                    rec.data_status = "PUBLIC_UNVERIFIED_REPORT"
                    rec.verification_note = update.verification_note or "Report rejected after physical field verification."

                if update.duplicate_of_id:
                    rec.duplicate_of_id = update.duplicate_of_id

                session.commit()
                session.refresh(rec)

                # Mirror locally
                self.incidents[rec.id] = rec.to_dict()
                self._save_fallback_storage()
                return self._to_response(rec.to_dict())
            except (SQLAlchemyError, Exception) as err:
                try:
                    session.rollback()
                except Exception:
                    pass
                logger.error("Database error updating incident status: %s", err)
                if settings.is_production():
                    raise RuntimeError("Failed to update status in database.")
            finally:
                if close_session:
                    try:
                        session.close()
                    except Exception:
                        pass

        # Offline fallback
        rec = self.incidents.get(incident_id.upper())
        if not rec:
            return None

        rec["verification_status"] = req_status
        rec["updated_at"] = now.isoformat()

        if req_status == "COMMUNITY_CORROBORATED":
            rec["data_status"] = "PUBLIC_UNVERIFIED_REPORT"
            rec["report_count"] = rec.get("report_count", 1) + 1
            rec["verification_note"] = update.verification_note or "Community corroborated: additional citizen confirmation received."
        elif req_status == "COMMUNITY_RESOLUTION_OBSERVED":
            rec["data_status"] = "PUBLIC_UNVERIFIED_REPORT"
            rec["verification_note"] = update.verification_note or "Citizen observation: floodwater reported receding or drained (awaiting official municipal confirmation)."
        elif req_status == "VERIFIED_MUNICIPAL" and is_institutional:
            rec["data_status"] = "VERIFIED_MUNICIPAL"
            rec["verified_at"] = now.isoformat()
            rec["verification_note"] = update.verification_note or "Verified by municipal disaster response authorities."
        elif req_status == "RESOLVED" and is_institutional:
            rec["data_status"] = "RESOLVED_INCIDENT"
            rec["verification_note"] = update.verification_note or "Issue resolved and receding (confirmed by emergency services)."
        elif req_status == "REJECTED" and is_institutional:
            rec["data_status"] = "PUBLIC_UNVERIFIED_REPORT"
            rec["verification_note"] = update.verification_note or "Report rejected after physical field verification."

        if update.duplicate_of_id:
            rec["duplicate_of_id"] = update.duplicate_of_id

        self._save_fallback_storage()
        return self._to_response(rec)

    def _to_response(self, record: Dict[str, Any]) -> IncidentResponse:
        """Converts raw storage dictionary into public-facing sanitized IncidentResponse."""
        def parse_dt(v: Any) -> datetime:
            if isinstance(v, datetime):
                return v
            if isinstance(v, str):
                try:
                    return datetime.fromisoformat(v)
                except Exception:
                    pass
            return datetime.now(timezone.utc)

        return IncidentResponse(
            id=record["id"],
            latitude=record["latitude"],
            longitude=record["longitude"],
            address=record.get("address"),
            location_name=record.get("location_name"),
            incident_category=record["incident_category"],
            category=record["incident_category"],
            severity=record["severity"],
            description=record["description"],
            reporter_contact=record.get("reporter_contact", "[REDACTED]"),
            has_image=record.get("has_image", False),
            image_url=record.get("image_url"),
            verification_status=record.get("verification_status", "PENDING_REVIEW"),
            status=record.get("verification_status", "PENDING_REVIEW"),
            data_status=record.get("data_status", "PUBLIC_UNVERIFIED_REPORT"),
            duplicate_of_id=record.get("duplicate_of_id"),
            duplicate_of=record.get("duplicate_of_id"),
            report_count=record.get("report_count", 1),
            created_at=parse_dt(record["created_at"]),
            updated_at=parse_dt(record.get("updated_at", record["created_at"])),
            verified_at=parse_dt(record["verified_at"]) if record.get("verified_at") else None,
            verification_note=record.get("verification_note", "Citizen-submitted public report."),
            reviewer_notes=record.get("verification_note"),
        )


_incident_service_instance: Optional[IncidentService] = None


def get_incident_service() -> IncidentService:
    global _incident_service_instance
    if _incident_service_instance is None:
        _incident_service_instance = IncidentService()
    return _incident_service_instance
