"""
Base class and utilities for SafeMap AI reproducible data importers.
Handles cryptographic hashing (SHA-256), timestamp normalization, coordinate
validation, unit standardization, deduplication, and malformed row detection.
"""

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


def compute_sha256(file_path: Path) -> str:
    """Computes SHA-256 checksum of a file."""
    if not file_path.exists():
        return ""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def normalize_iso_timestamp(date_val: Any, default_time: str = "00:00:00Z") -> Optional[str]:
    """
    Normalizes diverse date inputs (YYYY, YYYY-MM-DD, or full timestamps)
    into a standardized ISO-8601 UTC string.
    """
    if date_val is None:
        return None
    
    val_str = str(date_val).strip()
    if not val_str or val_str.lower() in ("nan", "none", "null"):
        return None

    # Handle YYYY
    if len(val_str) == 4 and val_str.isdigit():
        return f"{val_str}-01-01T00:00:00Z"

    # Handle YYYY-MM-DD
    if len(val_str) == 10 and val_str.count("-") == 2:
        return f"{val_str}T{default_time}"

    # Try common formats
    for fmt in (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
    ):
        try:
            dt = datetime.strptime(val_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue

    return None



def validate_coordinates(lat: Any, lon: Any) -> Tuple[bool, Optional[float], Optional[float], str]:
    """
    Validates WGS84 coordinates.
    Returns: (is_valid, float_lat, float_lon, error_msg)
    """
    if lat is None or lon is None:
        return False, None, None, "Missing latitude or longitude"

    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (ValueError, TypeError):
        return False, None, None, f"Non-numeric coordinates: lat={lat}, lon={lon}"

    if not (-90.0 <= lat_f <= 90.0):
        return False, None, None, f"Latitude {lat_f} out of bounds [-90, 90]"
    if not (-180.0 <= lon_f <= 180.0):
        return False, None, None, f"Longitude {lon_f} out of bounds [-180, 180]"

    return True, round(lat_f, 6), round(lon_f, 6), ""


VALID_DATA_CLASSIFICATIONS = {
    "OBSERVATION",
    "HISTORICAL_RECORD",
    "OFFICIAL_ALERT",
    "HISTORICAL_INUNDATION",
    "HISTORICAL_VULNERABILITY",
    "MODELLED",
    "MODEL_FORECAST",
    "PUBLIC_UNVERIFIED",
    "DEMO",
}

VALID_MEASUREMENT_TYPES = {
    "OBSERVED",
    "SECONDARY_REPORTED",
    "MODELLED",
    "ESTIMATED",
    "UNVERIFIED",
    "UNKNOWN",
}

VALID_VERIFICATION_STATES = {
    "VERIFIED",
    "PARTIALLY_VERIFIED",
    "UNVERIFIED",
}


def validate_data_classification(classification: Any) -> Tuple[bool, str]:
    """Validates that a classification tag matches approved SafeMap provenance values."""
    if not classification:
        return False, "Missing data classification"
    val = str(classification).strip().upper()
    if val in VALID_DATA_CLASSIFICATIONS:
        return True, val
    return False, f"Invalid classification '{classification}'. Allowed: {sorted(list(VALID_DATA_CLASSIFICATIONS))}"


def validate_measurement_type(m_type: Any) -> Tuple[bool, str]:
    """Validates measurement classification type (OBSERVED, SECONDARY_REPORTED, MODELLED, ESTIMATED, UNVERIFIED, UNKNOWN)."""
    if not m_type:
        return True, "UNKNOWN"
    val = str(m_type).strip().upper()
    if val in VALID_MEASUREMENT_TYPES:
        return True, val
    return False, f"Invalid measurement type '{m_type}'. Allowed: {sorted(list(VALID_MEASUREMENT_TYPES))}"


def validate_verification_state(v_state: Any) -> Tuple[bool, str]:
    """Validates verification state (VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED)."""
    if not v_state:
        return True, "UNVERIFIED"
    val = str(v_state).strip().upper()
    if val in VALID_VERIFICATION_STATES:
        return True, val
    return False, f"Invalid verification state '{v_state}'. Allowed: {sorted(list(VALID_VERIFICATION_STATES))}"



def validate_geojson_geometry(geom: Any) -> Tuple[bool, str]:
    """
    Validates a GeoJSON geometry dictionary (Polygon, MultiPolygon, Point).
    Checks coordinate bounds, closed rings for Polygons, and structure.
    """
    if not isinstance(geom, dict):
        return False, "Geometry must be a dictionary"
    
    geom_type = geom.get("type")
    coords = geom.get("coordinates")
    if not geom_type or coords is None:
        return False, "Missing geometry type or coordinates"

    if geom_type == "Point":
        if not isinstance(coords, (list, tuple)) or len(coords) < 2:
            return False, "Point coordinates must be [lon, lat]"
        lon, lat = coords[0], coords[1]
        valid, _, _, err = validate_coordinates(lat, lon)
        if not valid:
            return False, f"Invalid Point: {err}"
        return True, ""

    elif geom_type == "Polygon":
        if not isinstance(coords, list) or len(coords) == 0:
            return False, "Polygon coordinates must be a non-empty list of linear rings"
        for ring_idx, ring in enumerate(coords):
            if not isinstance(ring, list) or len(ring) < 4:
                return False, f"Linear ring {ring_idx} must have >= 4 coordinates"
            # Check closure: first coordinate must equal last coordinate
            first_pt, last_pt = ring[0], ring[-1]
            if first_pt != last_pt:
                return False, f"Linear ring {ring_idx} is not closed: {first_pt} != {last_pt}"
            for pt in ring:
                if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                    return False, f"Invalid coordinate in ring {ring_idx}: {pt}"
                lon, lat = pt[0], pt[1]
                valid, _, _, err = validate_coordinates(lat, lon)
                if not valid:
                    return False, f"Coordinate in ring {ring_idx} invalid: {err}"
        return True, ""

    elif geom_type == "MultiPolygon":
        if not isinstance(coords, list) or len(coords) == 0:
            return False, "MultiPolygon coordinates must be non-empty list"
        for poly_idx, poly in enumerate(coords):
            valid, err = validate_geojson_geometry({"type": "Polygon", "coordinates": poly})
            if not valid:
                return False, f"Polygon {poly_idx} inside MultiPolygon invalid: {err}"
        return True, ""

    return False, f"Unsupported geometry type: {geom_type}"


class BaseDataImporter(ABC):
    """Abstract base class for all SafeMap AI local dataset importers."""

    def __init__(self, raw_data_path: Path, curated_data_path: Path):
        self.raw_data_path = Path(raw_data_path)
        self.curated_data_path = Path(curated_data_path)
        self.curated_data_path.parent.mkdir(parents=True, exist_ok=True)
        self.seen_keys: Set[Any] = set()

    @abstractmethod
    def import_and_curate(self) -> Dict[str, Any]:
        """
        Executes idempotent data import, validation, cleaning, and curation.
        Returns execution summary dictionary.
        """
        pass

