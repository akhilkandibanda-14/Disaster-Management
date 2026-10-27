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

from app.config import is_in_hyderabad, settings
from app.schemas.incident import (
    IncidentCreate,
    IncidentListResponse,
    IncidentResponse,
    IncidentStatusUpdate,
)

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
    """

    def __init__(self, storage_path: Optional[str] = None):
        base_dir = Path(__file__).resolve().parents[2]
        self.data_dir = base_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.storage_file = Path(storage_path) if storage_path else self.data_dir / "incidents.json"
        self.rate_limit_tracker: Dict[str, deque] = {}
        self.incidents: Dict[str, Dict[str, Any]] = {}
        self._load_storage()

    def _load_storage(self) -> None:
        """Loads incidents from persistent storage or initializes default seed reports."""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.incidents = {item["id"]: item for item in data}
                    logger.info(f"Loaded {len(self.incidents)} incident report(s) from {self.storage_file}")
                    return
            except Exception as e:
                logger.error(f"Failed to load incidents file {self.storage_file}: {e}")

        # Initialize realistic seed reports for Hyderabad flood management
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
                "created_at": (now - timedelta(minutes=40)).isoformat(),
                "updated_at": (now - timedelta(minutes=40)).isoformat(),
                "verification_note": "Citizen-submitted public report. Has not yet been physically verified by emergency services.",
                "reporter_name": "[CONFIDENTIAL]",
                "reporter_contact": "[REDACTED]"
            },
            {
                "id": "INC-2026-003",
                "latitude": 17.4412,
                "longitude": 78.4719,
                "address": "Begumpet Railway Bridge Underpass",
                "incident_category": "ROAD_SUBMERGED",
                "severity": "HIGH",
                "description": "Underpass flooded with approx 2.5 feet water. Two cars stalled; traffic being diverted via Prakash Nagar.",
                "has_image": True,
                "image_url": None,
                "verification_status": "VERIFIED_MUNICIPAL",
                "data_status": "VERIFIED_MUNICIPAL",
                "duplicate_of_id": None,
                "report_count": 5,
                "created_at": (now - timedelta(hours=1, minutes=10)).isoformat(),
                "updated_at": (now - timedelta(minutes=25)).isoformat(),
                "verification_note": "Verified by Hyderabad Traffic Police & GHMC Monsoon Emergency Team. Dewatering pumps active.",
                "reporter_name": "[CONFIDENTIAL]",
                "reporter_contact": "[REDACTED]"
            }
        ]
        self.incidents = {item["id"]: item for item in seeds}
        self._save_storage()

    def _save_storage(self) -> None:
        """Persists incidents in JSON file format."""
        try:
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(list(self.incidents.values()), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save incidents storage: {e}")

    def check_rate_limit(self, client_ip: str) -> bool:
        """
        Sliding-window rate limiter ensuring at most MAX_SUBMISSIONS_PER_MINUTE
        requests per 60 seconds from any single client IP address.
        Returns True if allowed, False if rate-limited.
        """
        now = datetime.now(timezone.utc)
        if client_ip not in self.rate_limit_tracker:
            self.rate_limit_tracker[client_ip] = deque()

        queue = self.rate_limit_tracker[client_ip]
        cutoff = now - timedelta(seconds=60)
        while queue and queue[0] < cutoff:
            queue.popleft()

        if len(queue) >= MAX_SUBMISSIONS_PER_MINUTE:
            return False

        queue.append(now)
        return True

    def find_duplicate(
        self, 
        latitude: float, 
        longitude: float, 
        category: str, 
        now: datetime
    ) -> Optional[str]:
        """
        Detects if a recent similar flood report exists within DUPLICATE_RADIUS_KM (150m)
        in the past DUPLICATE_WINDOW_HOURS. Returns parent incident ID if found.
        """
        cutoff = now - timedelta(hours=DUPLICATE_WINDOW_HOURS)
        for inc_id, inc in self.incidents.items():
            if inc.get("verification_status") == "REJECTED":
                continue

            try:
                created_dt = datetime.fromisoformat(inc["created_at"])
            except Exception:
                continue

            if created_dt < cutoff:
                continue

            # Check spatial distance
            dist = haversine_distance_km(latitude, longitude, inc["latitude"], inc["longitude"])
            if dist <= DUPLICATE_RADIUS_KM:
                # Same or related category
                if inc["incident_category"] == category or category in ("OTHER_FLOOD", "WATERLOGGING"):
                    return inc_id

        return None

    def validate_image_data(self, image_data: Optional[str]) -> bool:
        """
        Validates optional base64 image data:
        Ensures max 5 MB and valid MIME type (PNG, JPEG, WebP).
        """
        if not image_data:
            return True

        if len(image_data) > 7_000_000:  # ~5MB binary base64 encoded
            return False

        if image_data.startswith("data:image/"):
            valid_mimes = ("data:image/jpeg", "data:image/png", "data:image/webp", "data:image/jpg")
            return any(image_data.startswith(m) for m in valid_mimes)

        return False

    def create_incident(self, data: IncidentCreate, client_ip: str) -> IncidentResponse:
        """
        Creates, validates, and stores a citizen flood incident report.
        Enforces geographic boundary checks, rate-limiting, privacy masking,
        and automatic duplicate correlation.
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

        now = datetime.now(timezone.utc)
        duplicate_id = self.find_duplicate(data.latitude, data.longitude, data.incident_category, now)

        # Generate unique ID
        year = now.strftime("%Y")
        seq = len(self.incidents) + 1
        new_id = f"INC-{year}-{seq:03d}"

        # If duplicate detected, increment report count on original
        if duplicate_id and duplicate_id in self.incidents:
            self.incidents[duplicate_id]["report_count"] = self.incidents[duplicate_id].get("report_count", 1) + 1
            self.incidents[duplicate_id]["updated_at"] = now.isoformat()

        # Privacy protection: sanitize phone and email occurrences
        clean_desc = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[REDACTED_EMAIL]', data.description)
        clean_desc = re.sub(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+?\d{10,13}', '[REDACTED_PHONE]', clean_desc)

        clean_contact = "[REDACTED]"
        if data.reporter_contact:
            clean_contact = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[REDACTED_EMAIL]', data.reporter_contact)
            clean_contact = re.sub(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+?\d{10,13}', '[REDACTED_PHONE]', clean_contact)

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
            "image_url": None,  # Stored internally or served via dedicated blob
            "verification_status": "PENDING_REVIEW",
            "data_status": "PUBLIC_UNVERIFIED_REPORT",
            "duplicate_of_id": duplicate_id,
            "report_count": 1,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "verified_at": None,
            "verification_note": "Citizen-submitted public report. Has not yet been physically verified by emergency services.",
            # Privacy protection: reporter identity is never returned in public APIs
            "reporter_name": data.reporter_name or "[ANONYMOUS]",
            "reporter_contact": clean_contact,
            "client_ip": client_ip,
        }

        self.incidents[new_id] = record
        self._save_storage()

        return self._to_response(record)

    def list_incidents(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
    ) -> IncidentListResponse:
        """Returns sanitized, privacy-safe list of active incident reports."""
        now = datetime.now(timezone.utc)
        items = list(self.incidents.values())

        # Sort reverse chronological
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)

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

    def get_incident(self, incident_id: str) -> Optional[IncidentResponse]:
        """Retrieves a single sanitized incident report by ID."""
        rec = self.incidents.get(incident_id.upper())
        if not rec:
            return None
        return self._to_response(rec)

    def update_status(
        self, 
        incident_id: str, 
        update: IncidentStatusUpdate
    ) -> Optional[IncidentResponse]:
        """Updates operational review status and notes for an incident."""
        rec = self.incidents.get(incident_id.upper())
        if not rec:
            return None

        now = datetime.now(timezone.utc)
        rec["verification_status"] = update.verification_status
        rec["updated_at"] = now.isoformat()

        if update.verification_status == "VERIFIED_MUNICIPAL":
            rec["data_status"] = "VERIFIED_MUNICIPAL"
            rec["verified_at"] = now.isoformat()
            rec["verification_note"] = update.verification_note or "Verified by municipal disaster response authorities."
        elif update.verification_status == "RESOLVED":
            rec["data_status"] = "RESOLVED_INCIDENT"
            rec["verification_note"] = update.verification_note or "Inundation resolved and cleared by local drainage teams."
        elif update.verification_status == "REJECTED":
            rec["data_status"] = "PUBLIC_UNVERIFIED_REPORT"
            rec["verification_note"] = update.verification_note or "Report rejected after verification inspection."

        if update.duplicate_of_id:
            rec["duplicate_of_id"] = update.duplicate_of_id

        self._save_storage()
        return self._to_response(rec)

    def _to_response(self, record: Dict[str, Any]) -> IncidentResponse:
        """Converts internal record into privacy-sanitized IncidentResponse."""
        verified_at = None
        if record.get("verified_at"):
            try:
                verified_at = datetime.fromisoformat(record["verified_at"])
            except Exception:
                pass

        return IncidentResponse(
            id=record["id"],
            latitude=record["latitude"],
            longitude=record["longitude"],
            address=record.get("address"),
            location_name=record.get("location_name") or record.get("address"),
            incident_category=record["incident_category"],
            severity=record["severity"],
            description=record["description"],
            reporter_contact=record.get("reporter_contact", "[REDACTED]"),
            has_image=record.get("has_image", False),
            image_url=record.get("image_url"),
            verification_status=record["verification_status"],
            data_status=record.get("data_status", "PUBLIC_UNVERIFIED_REPORT"),
            duplicate_of_id=record.get("duplicate_of_id"),
            report_count=record.get("report_count", 1),
            created_at=datetime.fromisoformat(record["created_at"]),
            updated_at=datetime.fromisoformat(record["updated_at"]),
            verified_at=verified_at,
            verification_note=record.get("verification_note", "Citizen-submitted public report."),
            reviewer_notes=record.get("reviewer_notes") or record.get("verification_note"),
        )


_incident_service: Optional[IncidentService] = None


def get_incident_service() -> IncidentService:
    """Singleton accessor for IncidentService."""
    global _incident_service
    if _incident_service is None:
        _incident_service = IncidentService()
    return _incident_service
