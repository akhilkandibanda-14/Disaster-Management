import os
import re
import json
import math
import time
import logging
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import httpx

from app.schemas.hospital_discovery import NearbyHospitalCandidate, NearbyHospitalDiscoveryResponse
from app.schemas.emergency_facility import EmergencyFacility

logger = logging.getLogger(__name__)

# Bounding box for Hyderabad operational region
HYD_LAT_MIN = 17.20
HYD_LAT_MAX = 17.60
HYD_LON_MIN = 78.20
HYD_LON_MAX = 78.70

DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
CACHE_TTL_SECONDS = 300  # 5 minutes

FACILITY_STOPWORDS = {
    "hospital", "hospitals", "clinic", "clinics", "centre", "center",
    "care", "health", "healthcare", "medical", "nursing", "home", "unit",
    "hyderabad", "telangana", "road", "street"
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on the earth in kilometers."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return 6371.0 * c


def normalize_facility_name(name: str) -> str:
    """Normalize facility name for deduplication (lowercase, strip punctuation)."""
    if not name:
        return ""
    clean = re.sub(r"[^\w\s]", "", name.lower())
    return " ".join(clean.split())


class HospitalDiscoveryService:
    def __init__(self, data_file: Optional[str] = None):
        base_path = Path(__file__).resolve().parents[3]
        if data_file:
            self.data_file = Path(data_file)
        else:
            self.data_file = base_path / "data" / "raw" / "emergency_facilities" / "osm_hyderabad_hospitals.json"
        
        self.overpass_url = os.environ.get("OVERPASS_URL", DEFAULT_OVERPASS_URL)
        self.nominatim_url = os.environ.get("NOMINATIM_URL", DEFAULT_NOMINATIM_URL)
        self._cache: Dict[Tuple[float, float, float], Tuple[float, List[NearbyHospitalCandidate]]] = {}
        self._discovered_registry: Dict[str, EmergencyFacility] = {}
        self._offline_records: List[Dict[str, Any]] = []
        self._load_offline_dataset()

    def _load_offline_dataset(self):
        """Loads the pre-curated genuine OpenStreetMap hospital dataset for Hyderabad."""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self._offline_records = json.load(f)
                    logger.info("Loaded %d genuine OSM hospital records from %s", len(self._offline_records), self.data_file)
            except Exception as e:
                logger.error("Failed to load OSM hospital dataset: %s", e)
                self._offline_records = []
        else:
            logger.warning("OSM hospital dataset file not found at %s", self.data_file)
            self._offline_records = []

    def validate_coordinates(self, latitude: float, longitude: float):
        """Validates coordinate ranges and enforces Hyderabad regional coverage."""
        if not (-90 <= latitude <= 90):
            raise ValueError(f"Latitude {latitude} is out of valid range [-90, 90].")
        if not (-180 <= longitude <= 180):
            raise ValueError(f"Longitude {longitude} is out of valid range [-180, 180].")
        if not (HYD_LAT_MIN <= latitude <= HYD_LAT_MAX and HYD_LON_MIN <= longitude <= HYD_LON_MAX):
            raise ValueError("Nearby hospital discovery currently supports Hyderabad coordinates only.")

    def _query_overpass(self, latitude: float, longitude: float, radius_km: float) -> List[Dict[str, Any]]:
        """Queries Overpass API for healthcare facilities around latitude, longitude."""
        radius_meters = int(radius_km * 1000)
        query = f"""
        [out:json][timeout:4];
        (
          node["amenity"="hospital"](around:{radius_meters},{latitude},{longitude});
          way["amenity"="hospital"](around:{radius_meters},{latitude},{longitude});
          node["healthcare"="hospital"](around:{radius_meters},{latitude},{longitude});
          way["healthcare"="hospital"](around:{radius_meters},{latitude},{longitude});
        );
        out center tags;
        """
        headers = {
            "User-Agent": "SafeMapAI/1.0 (academic disaster response prototype; contact: research@cbit.ac.in)",
            "Accept": "application/json"
        }
        resp = httpx.post(self.overpass_url, data={"data": query}, headers=headers, timeout=4.0)
        resp.raise_for_status()
        data = resp.json()
        return data.get("elements", [])

    def _query_nominatim(self, latitude: float, longitude: float, radius_km: float) -> List[Dict[str, Any]]:
        """Queries OpenStreetMap Nominatim for healthcare facilities within a bounding box."""
        delta_lat = (radius_km + 0.3) / 111.0
        delta_lon = (radius_km + 0.3) / 105.0
        viewbox = f"{longitude - delta_lon:.4f},{latitude + delta_lat:.4f},{longitude + delta_lon:.4f},{latitude - delta_lat:.4f}"
        
        headers = {
            "User-Agent": "SafeMapAI/1.0 (academic disaster response prototype; contact: research@cbit.ac.in)",
            "Accept": "application/json"
        }
        resp = httpx.get(
            self.nominatim_url,
            params={
                "q": "hospital",
                "format": "json",
                "viewbox": viewbox,
                "bounded": 1,
                "limit": 25
            },
            headers=headers,
            timeout=3.5
        )
        resp.raise_for_status()
        items = resp.json()
        elements = []
        for it in items:
            try:
                lat = float(it.get("lat"))
                lon = float(it.get("lon"))
            except (ValueError, TypeError):
                continue
            osm_type = str(it.get("osm_type", "node")).lower()
            osm_id = it.get("osm_id")
            display_name = it.get("display_name", "")
            name_parts = [p.strip() for p in display_name.split(",")]
            primary_name = name_parts[0] if name_parts else "Hospital"
            street = name_parts[1] if len(name_parts) > 1 else None
            elements.append({
                "type": osm_type,
                "id": osm_id,
                "lat": lat,
                "lon": lon,
                "tags": {
                    "name": primary_name,
                    "amenity": "clinic" if it.get("type") == "clinic" else "hospital",
                    "addr:full": display_name,
                    "addr:street": street
                }
            })
        return elements

    def discover_nearby_hospitals(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        limit: int = 15,
        force_refresh: bool = False
    ) -> NearbyHospitalDiscoveryResponse:
        """
        Discovers genuine hospital candidates near the specified coordinates within radius_km.
        Deduplicates results, sorts by straight-line distance, and preserves truth-in-data disclosures.
        """
        self.validate_coordinates(latitude, longitude)
        if radius_km <= 0 or radius_km > 30.0:
            raise ValueError("Search radius must be greater than 0 and at most 30 km.")
        if limit <= 0:
            limit = 15

        # Check in-memory cache
        cache_key = (round(latitude, 3), round(longitude, 3), round(radius_km, 1))
        now = time.time()
        if not force_refresh and cache_key in self._cache:
            cache_time, cached_items = self._cache[cache_key]
            if now - cache_time < CACHE_TTL_SECONDS:
                # Recalculate distance from the exact requested origin
                recomputed = []
                for item in cached_items:
                    item_dict = item.model_dump()
                    item_dict["distance_km"] = round(haversine_km(latitude, longitude, item.latitude, item.longitude), 2)
                    recomputed.append(NearbyHospitalCandidate(**item_dict))
                recomputed.sort(key=lambda x: x.distance_km)
                sliced = recomputed[:limit]
                return NearbyHospitalDiscoveryResponse(
                    hospitals=sliced,
                    total=len(recomputed),
                    origin_latitude=latitude,
                    origin_longitude=longitude,
                    radius_km=radius_km,
                    source="OpenStreetMap (Cached)",
                    data_status="PUBLIC_UNVERIFIED",
                    warning=None
                )

        raw_elements = []
        source_used = "OpenStreetMap (Overpass API)"
        warning_msg = None

        try:
            raw_elements = self._query_overpass(latitude, longitude, radius_km)
            if not raw_elements:
                # If Overpass returns empty, fall back to verified offline records
                raw_elements = self._get_offline_elements(latitude, longitude, radius_km)
                source_used = "OpenStreetMap (OSM POI Registry)"
        except Exception as e:
            logger.warning("Overpass API query failed or timed out (%s). Falling back to OSM POI registry.", e)
            raw_elements = self._get_offline_elements(latitude, longitude, radius_km)
            source_used = "OpenStreetMap (OSM POI Registry)"
            warning_msg = "Live Overpass API query timed out; using verified OpenStreetMap Hyderabad POI registry."

        candidates = self._process_elements(raw_elements, latitude, longitude, radius_km)

        # Cache results
        self._cache[cache_key] = (now, candidates)

        # Register discovered candidates in memory for route resolution
        for cand in candidates:
            self._register_as_facility(cand)

        sliced_candidates = candidates[:limit]

        return NearbyHospitalDiscoveryResponse(
            hospitals=sliced_candidates,
            total=len(candidates),
            origin_latitude=latitude,
            origin_longitude=longitude,
            radius_km=radius_km,
            source=source_used,
            data_status="PUBLIC_UNVERIFIED",
            warning=warning_msg
        )

    def _get_offline_elements(self, latitude: float, longitude: float, radius_km: float) -> List[Dict[str, Any]]:
        """Filters the offline genuine OSM hospital dataset within the search radius."""
        elements = []
        for rec in self._offline_records:
            lat = float(rec.get("latitude", 0))
            lon = float(rec.get("longitude", 0))
            dist = haversine_km(latitude, longitude, lat, lon)
            if dist <= radius_km:
                elements.append({
                    "type": rec.get("osm_type", "node"),
                    "id": rec.get("osm_id", rec.get("id")),
                    "lat": lat,
                    "lon": lon,
                    "tags": {
                        "name": rec.get("name"),
                        "amenity": "hospital",
                        "phone": rec.get("phone"),
                        "addr:street": rec.get("address"),
                        "area": rec.get("area"),
                    }
                })
        return elements

    def _process_elements(
        self,
        elements: List[Dict[str, Any]],
        origin_lat: float,
        origin_lon: float,
        radius_km: float
    ) -> List[NearbyHospitalCandidate]:
        """Validates coordinates, normalizes names, deduplicates, and sorts by distance."""
        parsed: List[NearbyHospitalCandidate] = []
        seen_keys = set()

        for el in elements:
            # Extract coordinates
            lat = el.get("lat") or el.get("center", {}).get("lat")
            lon = el.get("lon") or el.get("center", {}).get("lon")
            if lat is None or lon is None:
                continue
            try:
                lat = float(lat)
                lon = float(lon)
            except (ValueError, TypeError):
                continue

            # Validate coordinate range
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue

            dist = haversine_km(origin_lat, origin_lon, lat, lon)
            if dist > radius_km:
                continue

            tags = el.get("tags") or {}
            raw_name = tags.get("name") or tags.get("name:en") or tags.get("official_name")
            if not raw_name or not str(raw_name).strip():
                name = "Unnamed Medical Facility (OSM)"
            else:
                name = str(raw_name).strip()

            norm_name = normalize_facility_name(name)
            words_a = set(w for w in norm_name.split() if len(w) > 3)

            is_duplicate = False
            for existing in parsed:
                dist_between_km = haversine_km(existing.latitude, existing.longitude, lat, lon)
                if dist_between_km <= 0.25:  # Within 250 meters
                    existing_norm = normalize_facility_name(existing.name)
                    words_b = set(w for w in existing_norm.split() if len(w) > 3)
                    common_words = words_a & words_b
                    has_name_overlap = bool(common_words) or (norm_name in existing_norm) or (existing_norm in norm_name)
                    if has_name_overlap or dist_between_km < 0.035:
                        is_duplicate = True
                        break
            if is_duplicate:
                continue

            osm_id = el.get("id") or "0"
            osm_type = str(el.get("type", "node")).lower()
            facility_id = f"OSM-{osm_type.upper()}-{osm_id}"

            facility_type = "CLINIC" if tags.get("amenity") == "clinic" else "HOSPITAL"
            address = tags.get("addr:street") or tags.get("addr:full") or tags.get("address")
            area = tags.get("area") or tags.get("addr:suburb") or tags.get("addr:district")
            phone = tags.get("phone") or tags.get("contact:phone")

            candidate = NearbyHospitalCandidate(
                facility_id=facility_id,
                name=name,
                latitude=round(lat, 6),
                longitude=round(lon, 6),
                distance_km=round(dist, 2),
                source="OpenStreetMap (OSM POI)",
                facility_type=facility_type,
                data_status="PUBLIC_UNVERIFIED",
                verification_status="UNVERIFIED",
                operational_status="UNKNOWN",
                capacity=None,
                operational_status_verified=False,
                capacity_verified=False,
                verification_note="OpenStreetMap candidate. Not verified for live casualty intake, open status, or bed capacity. Confirm before travel.",
                address=address,
                area=area,
                phone=phone
            )
            parsed.append(candidate)

        # Sort strictly ascending by straight-line distance
        parsed.sort(key=lambda x: x.distance_km)
        return parsed

    def _register_as_facility(self, candidate: NearbyHospitalCandidate) -> EmergencyFacility:
        """Stores candidate in registry so it can be resolved as an EmergencyFacility by ID."""
        fac = EmergencyFacility(
            facility_id=candidate.facility_id,
            name=candidate.name,
            facility_type=candidate.facility_type,
            latitude=candidate.latitude,
            longitude=candidate.longitude,
            address=candidate.address,
            area=candidate.area,
            district="Hyderabad",
            state="Telangana",
            capacity=None,
            current_occupancy=None,
            operational_status="UNKNOWN",
            contact=candidate.phone or "108 / 112",
            source=candidate.source,
            data_status="PUBLIC_UNVERIFIED",
            verification_note=candidate.verification_note,
            distance_km=candidate.distance_km,
            location_verified=True,
            operational_status_verified=False,
            capacity_verified=False,
            verification_scope="IDENTITY_ONLY"
        )
        self._discovered_registry[candidate.facility_id.upper()] = fac
        return fac

    def get_hospital_by_id(self, facility_id: str) -> Optional[EmergencyFacility]:
        """Resolves an OSM hospital candidate by ID."""
        if not facility_id:
            return None
        upper_id = facility_id.upper()
        if upper_id in self._discovered_registry:
            return self._discovered_registry[upper_id]
        
        # Check offline dataset for direct match
        for rec in self._offline_records:
            rec_id = f"OSM-{rec.get('osm_type', 'node').upper()}-{rec.get('osm_id', rec.get('id'))}".upper()
            if rec_id == upper_id or str(rec.get("id")).upper() == upper_id:
                cand = NearbyHospitalCandidate(
                    facility_id=rec_id,
                    name=rec.get("name", "Unnamed Hospital"),
                    latitude=float(rec.get("latitude")),
                    longitude=float(rec.get("longitude")),
                    distance_km=0.0,
                    source="OpenStreetMap (OSM POI)",
                    facility_type=rec.get("facility_type", "HOSPITAL"),
                    data_status="PUBLIC_UNVERIFIED",
                    verification_status="UNVERIFIED",
                    operational_status="UNKNOWN",
                    address=rec.get("address"),
                    area=rec.get("area"),
                    phone=rec.get("phone")
                )
                return self._register_as_facility(cand)

        return None


_hospital_discovery_service: Optional[HospitalDiscoveryService] = None


def get_hospital_discovery_service() -> HospitalDiscoveryService:
    global _hospital_discovery_service
    if _hospital_discovery_service is None:
        _hospital_discovery_service = HospitalDiscoveryService()
    return _hospital_discovery_service

