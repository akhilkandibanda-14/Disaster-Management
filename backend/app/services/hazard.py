import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET
import httpx

from app.schemas.hazard import (
    GeoJSONGeometry,
    HazardRecord,
    HazardListResponse,
    LocationHazardWarning,
)

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {
    "EXTREME": 5,
    "SEVERE": 4,
    "HIGH": 3,
    "MODERATE": 2,
    "LOW": 1,
    "UNKNOWN": 0,
    "NONE": -1,
}


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two decimal coordinates in kilometers."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def point_in_polygon(lon: float, lat: float, ring: List[List[float]]) -> bool:
    """
    Standard ray-casting algorithm to determine if a point (lon, lat) is inside a polygon ring.
    Coordinates in the ring are in [longitude, latitude] GeoJSON standard format.
    """
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def classify_flood_alert(
    headline: str,
    description: str = "",
    category: str = "",
    event_code: str = "",
) -> Optional[Tuple[str, str]]:
    """
    Evaluates whether an official CAP or RSS emergency alert is relevant to flood management.
    Returns (flood_hazard_type, severity) if flood-related, or None if unrelated or ambiguous.

    Flood-related categories:
    - Direct river floods, reservoir releases, dam gate discharges: RIVER_OVERFLOW
    - Urban waterlogging, nala overflows, low-lying street inundations: WATERLOGGING / URBAN_INUNDATION
    - Flash floods: FLASH_FLOOD
    - General flood warnings: FLOOD
    - Heavy/extreme rainfall alerts that threaten flooding: FLOOD_RELATED_HEAVY_RAINFALL

    Strict non-flood exclusions:
    - Tsunamis, coastal/marine storm surges
    - Earthquakes, seismic tremors
    - Cyclones, hurricanes, typhoons
    - Tornadoes, gales, dust storms
    - Wildfires, forest fires
    - Landslides, mudslides, avalanches
    - Droughts, heatwaves, cold waves
    - Thunderstorm/lightning without heavy rain or flood warnings
    - Ambiguous or general weather updates
    """
    text = f"{headline} {description} {category} {event_code}".upper()

    # 1. Non-flood disaster keywords
    non_flood_disasters = [
        "TSUNAMI", "COASTAL SURGE", "STORM SURGE", "HIGH TIDE", "MARINE", "SEA ROUGH",
        "EARTHQUAKE", "SEISMIC", "TREMOR", "EPICENTER",
        "CYCLONE", "HURRICANE", "TYPHOON", "CYCLONIC",
        "TORNADO", "GALE", "DUST STORM", "HAILSTORM", "SANDSTORM",
        "WILDFIRE", "FOREST FIRE", "BUSHFIRE", "FIRE",
        "LANDSLIDE", "AVALANCHE", "MUDSLIDE", "ROCKFALL",
        "HEATWAVE", "HEAT WAVE", "COLD WAVE", "FROST",
        "DROUGHT", "WATER SCARCITY",
        "VOLCANO", "VOLCANIC", "ASH FALL",
    ]
    headline_and_cat = f"{headline} {category} {event_code}".upper()
    has_non_flood_disaster_title = any(k in headline_and_cat for k in non_flood_disasters)
    has_non_flood_disaster_anywhere = any(k in text for k in non_flood_disasters)

    # 2. Explicit flood-related indicators
    direct_river_flood_terms = [
        "RIVER OVERFLOW", "RIVER FLOOD", "RIVER SPILL", "MUSI RIVER", "RIVER WATER LEVEL",
        "DAM RELEASE", "RESERVOIR RELEASE", "GATE OPENING", "SLUICE GATE",
        "OSMAN SAGAR", "HIMAYAT SAGAR", "SINGUR DAM", "CAUSEWAY SUBMERGENCE",
    ]
    urban_flood_terms = [
        "WATERLOGGING", "WATER-LOGGING", "URBAN INUNDATION", "INUNDATION OF LOW LYING",
        "DRAINAGE OVERFLOW", "NALA OVERFLOW", "STREET FLOODING", "SUBMERGED ROADS",
    ]
    flash_flood_terms = [
        "FLASH FLOOD", "FLASH INUNDATION", "TORRENTIAL FLOOD",
    ]
    flood_rainfall_terms = [
        "FLOOD-RELATED HEAVY RAINFALL", "FLOOD RELATED HEAVY RAINFALL",
        "EXTREMELY HEAVY RAIN", "VERY HEAVY RAIN", "HEAVY TO VERY HEAVY RAINFALL",
        "HEAVY RAINFALL FLOOD WARNING", "RED ALERT RAINFALL", "FLASH FLOOD RISK",
        "HEAVY DOWNPOUR CAUSING FLOOD", "INUNDATION DUE TO HEAVY RAIN",
    ]
    general_flood_terms = [
        "FLOOD WARNING", "FLOOD ALERT", "FLOOD SITUATION", "FLOODING", "INUNDATION",
    ]

    has_flood_term = (
        any(k in text for k in direct_river_flood_terms) or
        any(k in text for k in urban_flood_terms) or
        any(k in text for k in flash_flood_terms) or
        any(k in text for k in flood_rainfall_terms) or
        any(k in text for k in general_flood_terms)
    )

    # If title/category specifies a non-flood disaster (e.g. Cyclone alert, Tsunami warning), reject immediately
    if has_non_flood_disaster_title:
        return None

    # If non-flood disaster keyword is present in text AND no explicit flood term is present, reject
    if has_non_flood_disaster_anywhere and not has_flood_term:
        return None

    if not has_flood_term:
        # Ambiguous weather alerts (e.g. "Thunderstorm and lightning", "Wind warning", "Moderate showers")
        # Do not classify ordinary rainfall or general weather as floods!
        return None

    # Deduce flood hazard type
    if any(k in text for k in direct_river_flood_terms):
        hazard_type = "RIVER_OVERFLOW"
    elif any(k in text for k in flash_flood_terms):
        hazard_type = "FLASH_FLOOD"
    elif any(k in text for k in urban_flood_terms):
        hazard_type = "URBAN_INUNDATION"
    elif any(k in text for k in flood_rainfall_terms):
        hazard_type = "FLOOD_RELATED_HEAVY_RAINFALL"
    elif any(k in text for k in general_flood_terms):
        hazard_type = "FLOOD"
    else:
        return None

    # Deduce severity from official terms
    if "EXTREME" in text or "EXTREMELY HEAVY" in text or "RED ALERT" in text:
        sev = "EXTREME"
    elif "SEVERE" in text or "VERY HEAVY" in text or "ORANGE ALERT" in text:
        sev = "SEVERE"
    elif "WARNING" in text or "HEAVY" in text or "HIGH" in text:
        sev = "HIGH"
    elif "ALERT" in text or "MODERATE" in text:
        sev = "MODERATE"
    elif "LOW" in text or "ADVISORY" in text:
        sev = "LOW"
    else:
        sev = "UNKNOWN"

    return hazard_type, sev


class HazardService:
    """
    Comprehensive Flood Hazard Service synthesizing:
    1. Published municipal flood-prone vulnerability polygons (GHMC / MRDCL).
    2. Authoritative live CAP weather and disaster alerts (NDMA SACHET).
    3. Global flood awareness river discharge forecasts (Copernicus / GloFAS).
    4. Explicitly labeled [DEMO] records when requested.
    """

    def __init__(self, data_path: Optional[str] = None):
        base_dir = Path(__file__).resolve().parents[3]
        if data_path:
            self.geojson_file = Path(data_path)
        else:
            self.geojson_file = base_dir / "data" / "raw" / "hazards" / "hyderabad_flood_zones.geojson"
        
        self.cached_public_hazards: List[HazardRecord] = []
        self.last_provider_warnings: List[str] = []
        self._load_local_geojson()

    def _load_local_geojson(self) -> None:
        """Loads and validates published flood-prone zones from GeoJSON file."""
        if not self.geojson_file.exists():
            logger.warning(f"Hazard GeoJSON file not found: {self.geojson_file}")
            self.cached_public_hazards = []
            return

        try:
            with open(self.geojson_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            now = datetime.now(timezone.utc)
            records = []
            for feat in data.get("features", []):
                props = feat.get("properties", {})
                geom_dict = feat.get("geometry")

                # Validate geometry
                geom = None
                centroid_lat = None
                centroid_lon = None
                if geom_dict and "coordinates" in geom_dict:
                    try:
                        geom = GeoJSONGeometry(**geom_dict)
                        # Compute simple centroid
                        coords = geom_dict["coordinates"]
                        if geom_dict["type"] == "Polygon" and coords and len(coords[0]) > 0:
                            lons = [p[0] for p in coords[0]]
                            lats = [p[1] for p in coords[0]]
                            centroid_lon = sum(lons) / len(lons)
                            centroid_lat = sum(lats) / len(lats)
                    except Exception as ge:
                        logger.warning(f"Invalid geometry in feature {feat.get('id')}: {ge}")
                        continue

                rec = HazardRecord(
                    hazard_id=str(props.get("hazard_id", feat.get("id"))),
                    hazard_type=str(props.get("hazard_type", "FLOOD_ZONE")),
                    title=str(props.get("title", "Published Flood-Prone Zone")),
                    description=str(props.get("description", "Identified historical inundation area.")),
                    severity=props.get("severity", "MODERATE"),
                    latitude=centroid_lat,
                    longitude=centroid_lon,
                    geometry=geom,
                    source_name=str(props.get("source_name", "GHMC Disaster Management / MRDCL")),
                    source_url=props.get("source_url", "https://www.telangana.gov.in"),
                    source_type="HISTORICAL_VULNERABILITY",
                    administrative_area="Hyderabad Municipal Area (GHMC / MRDCL)",
                    geographic_uncertainty="Polygon boundaries reflect indicative municipal inundation surveys; no sensor telemetry or live gauge verification.",
                    publication_time=now,
                    last_retrieved=now,
                    is_active=True,
                    is_stale=False,
                    data_status="PUBLIC_UNVERIFIED",
                    verification_note=str(
                        props.get(
                            "verification_note", 
                            "Historical municipal inundation study. Live water depth is not sensor-verified."
                        )
                    )
                )
                records.append(rec)
            self.cached_public_hazards = records
        except Exception as e:
            logger.error(f"Failed to load hazard GeoJSON: {e}")
            self.cached_public_hazards = []
    def parse_cap_item(
        self,
        item: ET.Element,
        now: Optional[datetime] = None,
        default_url: str = "https://sachet.ndma.gov.in",
        idx: int = 1,
    ) -> Optional[HazardRecord]:
        """
        Parses a single CAP XML item element into a validated HazardRecord if flood-related.
        Returns None if the item describes a non-flood disaster or ambiguous weather.
        """
        now_dt = now or datetime.now(timezone.utc)
        title_elem = item.find("title")
        link_elem = item.find("link")
        pub_date_elem = item.find("pubDate")
        desc_elem = item.find("description")
        category_elem = item.find("category")
        expires_elem = item.find("expires") or item.find("expiry")

        title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
        description = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
        category = category_elem.text.strip() if category_elem is not None and category_elem.text else ""
        link = link_elem.text.strip() if link_elem is not None and link_elem.text else default_url

        classification = classify_flood_alert(headline=title, description=description, category=category)
        if classification is None:
            logger.info(f"Excluding non-flood or ambiguous CAP alert from flood hazard map: '{title}'")
            return None

        flood_hazard_type, sev = classification

        # Parse publication time if possible
        pub_dt = now_dt
        if pub_date_elem is not None and pub_date_elem.text:
            try:
                pub_dt = datetime.strptime(pub_date_elem.text.strip(), "%a, %d %b %Y %H:%M:%S %z")
            except Exception:
                pub_dt = now_dt

        # Parse expiry time if present
        expires_at = None
        is_stale = False
        is_active = True
        data_status = "AUTHORITATIVE"
        if expires_elem is not None and expires_elem.text:
            try:
                expires_at = datetime.strptime(expires_elem.text.strip(), "%a, %d %b %Y %H:%M:%S %z")
                if expires_at < now_dt:
                    is_stale = True
                    is_active = False
                    data_status = "STALE"
            except Exception:
                pass

        # Sachet alert identifier
        identifier = f"TG-SACHET-{idx:03d}"
        if "identifier=" in link:
            identifier = f"TG-SACHET-{link.split('identifier=')[-1]}"

        return HazardRecord(
            hazard_id=identifier,
            hazard_type=flood_hazard_type,
            title=f"NDMA Flood Warning: {title[:100]}" if not title.upper().startswith("NDMA") else title[:120],
            description=description or title,
            severity=sev,
            latitude=17.3850,
            longitude=78.4867,
            geometry=None,
            source_name="NDMA SACHET (Telangana SDMA)",
            source_url=link,
            source_type="OFFICIAL_ALERT",
            administrative_area="Telangana State / Hyderabad District",
            geographic_uncertainty="District-level administrative CAP bulletin; localized street-level inundation boundaries are not provided.",
            publication_time=pub_dt,
            last_retrieved=now_dt,
            expires_at=expires_at,
            is_active=is_active,
            is_stale=is_stale,
            data_status=data_status,
            verification_note="Authoritative Common Alerting Protocol (CAP) flood bulletin published by NDMA / Telangana SDMA."
        )

    def fetch_ndma_sachet_alerts(
        self,
        timeout_sec: float = 4.0,
        feed_content: Optional[str] = None,
    ) -> List[HazardRecord]:
        """
        Retrieves live authoritative CAP alerts from NDMA Sachet RSS feed for Telangana.
        Strictly filters for flood-relevant alerts, excluding earthquakes, tsunamis,
        cyclones, wildfires, and ambiguous weather advisories.
        """
        url = "https://sachet.ndma.gov.in/cap_public_website/rss/rss_telangana.xml"
        now = datetime.now(timezone.utc)
        results = []

        try:
            if feed_content is not None:
                xml_data = feed_content.encode("utf-8") if isinstance(feed_content, str) else feed_content
            else:
                with httpx.Client(timeout=timeout_sec, follow_redirects=True, headers={"User-Agent": "SafeMapAI/1.0"}) as client:
                    resp = client.get(url)
                    if resp.status_code != 200:
                        warn_msg = f"NDMA SACHET live alert service returned HTTP {resp.status_code}."
                        logger.warning(warn_msg)
                        self.last_provider_warnings.append(warn_msg)
                        return []
                    xml_data = resp.content

            root = ET.fromstring(xml_data)
            items = root.findall(".//item")
            for idx, item in enumerate(items[:10]):
                record = self.parse_cap_item(item, now=now, default_url=url, idx=idx + 1)
                if record is not None:
                    results.append(record)
        except Exception as err:
            warn_msg = f"NDMA SACHET live CAP alert feed was unavailable ({type(err).__name__})."
            logger.info(warn_msg)
            self.last_provider_warnings.append(warn_msg)
            return []

        return results

    def fetch_glofas_hydrology(self, latitude: float = 17.385, longitude: float = 78.486, timeout_sec: float = 4.0) -> List[HazardRecord]:
        """
        Retrieves Copernicus GloFAS river discharge forecast via Open-Meteo Flood API.
        Records model grid coordinates, discharge units, forecast date, and uncalibrated severity.
        """
        url = "https://flood-api.open-meteo.com/v1/flood"
        now = datetime.now(timezone.utc)
        
        try:
            with httpx.Client(timeout=timeout_sec, headers={"User-Agent": "SafeMapAI/1.0"}) as client:
                resp = client.get(url, params={"latitude": latitude, "longitude": longitude, "daily": "river_discharge"})
                if resp.status_code != 200:
                    warn_msg = f"Copernicus GloFAS river discharge forecast returned HTTP {resp.status_code}."
                    self.last_provider_warnings.append(warn_msg)
                    return []
                data = resp.json()
                daily = data.get("daily", {})
                times = daily.get("time", [])
                discharges = daily.get("river_discharge", [])
                
                if times and discharges and discharges[0] is not None:
                    current_discharge = float(discharges[0])
                    ret_lat = float(data.get("latitude", latitude))
                    ret_lon = float(data.get("longitude", longitude))
                    forecast_date_str = str(times[0])

                    grid_offset_km = haversine_distance_km(latitude, longitude, ret_lat, ret_lon)
                    relevance_note = "Grid cell aligns with upper Musi River catchment corridor." if grid_offset_km <= 25.0 else f"Grid cell offset ({grid_offset_km:.1f} km) from target location."

                    return [
                        HazardRecord(
                            hazard_id="GLOFAS-MUSI-001",
                            hazard_type="RIVER_OVERFLOW",
                            title=f"Musi River Modelled Discharge ({current_discharge:.1f} m³/s)",
                            description=f"Copernicus Emergency Management Service GloFAS forecast indicates modelled river discharge of {current_discharge:.1f} m³/s in the Musi River basin for {forecast_date_str}.",
                            severity="UNKNOWN",  # Uncalibrated: DO NOT assign arbitrary flood levels without validated rating curves
                            latitude=ret_lat,
                            longitude=ret_lon,
                            geometry=None,
                            source_name="Copernicus EMS / GloFAS (Open-Meteo)",
                            source_url="https://flood-api.open-meteo.com",
                            source_type="MODEL_FORECAST",
                            requested_coordinates=(latitude, longitude),
                            returned_coordinates=(ret_lat, ret_lon),
                            measurement_unit="m³/s",
                            forecast_date=forecast_date_str,
                            raw_value=current_discharge,
                            catchment_context="Musi River Basin (Krishna Catchment)",
                            administrative_area="Hyderabad Urban Catchment",
                            geographic_uncertainty=f"GloFAS 0.05° (~5km) gridded hydrological model cell at ({ret_lat:.3f}, {ret_lon:.3f}), {grid_offset_km:.2f} km from queried coordinates. {relevance_note} Modelled forecast, NOT observed telemetry. Severity is uncalibrated without validated urban hydrodynamic rating curves.",
                            publication_time=now,
                            last_retrieved=now,
                            is_active=True,
                            is_stale=False,
                            data_status="AUTHORITATIVE",
                            verification_note="Modelled river discharge forecast from European Commission Copernicus GloFAS via Open-Meteo API. Model forecasts are NOT observed gauge telemetry; urban flood severity thresholds are uncalibrated for Musi River urban reaches."
                        )
                    ]
        except Exception as err:
            warn_msg = f"Copernicus GloFAS river discharge forecast unavailable ({type(err).__name__})."
            logger.info(warn_msg)
            self.last_provider_warnings.append(warn_msg)
            return []

        return []

    def get_demo_hazard(self) -> HazardRecord:
        """Returns a deterministic simulated hazard polygon for demo/testing."""
        now = datetime.now(timezone.utc)
        return HazardRecord(
            hazard_id="DEMO-HAZ-001",
            hazard_type="FLASH_FLOOD",
            title="[DEMO] Simulated Flash Flood Zone - Lower Begumpet Corridor",
            description="[DEMO] Simulated emergency scenario: heavy 95mm downpour causes flash inundation near Begumpet storm-water canal.",
            severity="HIGH",
            latitude=17.442,
            longitude=78.475,
            geometry=GeoJSONGeometry(
                type="Polygon",
                coordinates=[
                    [
                        [78.4700, 17.4390],
                        [78.4800, 17.4400],
                        [78.4790, 17.4460],
                        [78.4710, 17.4450],
                        [78.4700, 17.4390]
                    ]
                ]
            ),
            source_name="DEMO / SIMULATED DATA",
            source_url="https://safemap.internal/demo",
            source_type="DEMO",
            administrative_area="Begumpet / Rasoolpura Corridor",
            geographic_uncertainty="Simulated bounding polygon for UI and integration demonstration purposes only.",
            publication_time=now,
            last_retrieved=now,
            is_active=True,
            is_stale=False,
            data_status="DEMO",
            verification_note="[DEMO] Simulated hazard scenario for testing and user-interface demonstrations. Not an actual hazard."
        )

    def get_last_provider_warnings(self) -> List[str]:
        """Returns warnings encountered from external live providers during the last query."""
        return list(self.last_provider_warnings)

    def get_hazards(
        self,
        hazard_type: Optional[str] = None,
        severity: Optional[str] = None,
        data_status: Optional[str] = None,
        include_demo: bool = True,
        include_authoritative: bool = True,
    ) -> List[HazardRecord]:
        """
        Compiles all validated flood hazards, categorizing records truthfully.
        """
        self.last_provider_warnings = []
        hazards: List[HazardRecord] = []

        # 1. Published municipal flood zones (PUBLIC_UNVERIFIED)
        hazards.extend(self.cached_public_hazards)

        # 2. Live Authoritative Feeds (NDMA SACHET + GloFAS Hydrology)
        if include_authoritative:
            sachet_alerts = self.fetch_ndma_sachet_alerts()
            hazards.extend(sachet_alerts)
            
            glofas_alerts = self.fetch_glofas_hydrology()
            hazards.extend(glofas_alerts)

        # 3. Simulated Demo Scenario (DEMO)
        if include_demo:
            hazards.append(self.get_demo_hazard())

        # Filtering
        filtered = []
        for h in hazards:
            if hazard_type and h.hazard_type.upper() != hazard_type.upper():
                continue
            if severity and h.severity.upper() != severity.upper():
                continue
            if data_status and h.data_status.upper() != data_status.upper():
                continue
            filtered.append(h)

        return filtered

    def get_hazard_by_id(self, hazard_id: str) -> Optional[HazardRecord]:
        """Retrieves an individual hazard record by its unique ID."""
        if not hazard_id:
            return None
        all_hazards = self.get_hazards(include_demo=True, include_authoritative=True)
        return next((h for h in all_hazards if h.hazard_id.upper() == hazard_id.upper()), None)

    def check_location(
        self, 
        latitude: float, 
        longitude: float, 
        include_demo: bool = True
    ) -> LocationHazardWarning:
        """
        Determines whether a user location intersects any active flood hazard zone.
        Uses Ray-casting Point-in-Polygon (PIP) for polygons and 150m Haversine radius for point hazards.
        """
        active_hazards = self.get_hazards(include_demo=include_demo, include_authoritative=True)
        intersected: List[HazardRecord] = []

        for h in active_hazards:
            hit = False
            # Polygon check
            if h.geometry and h.geometry.type == "Polygon" and h.geometry.coordinates:
                # Exterior ring is coordinates[0]
                exterior_ring = h.geometry.coordinates[0]
                if point_in_polygon(longitude, latitude, exterior_ring):
                    hit = True
            elif h.geometry and h.geometry.type == "MultiPolygon" and h.geometry.coordinates:
                for poly in h.geometry.coordinates:
                    if poly and point_in_polygon(longitude, latitude, poly[0]):
                        hit = True
                        break
            
            # Point proximity fallback (150 meters)
            if not hit and h.latitude is not None and h.longitude is not None:
                dist_km = haversine_distance_km(latitude, longitude, h.latitude, h.longitude)
                if dist_km <= 0.15:  # 150m
                    hit = True

            if hit:
                intersected.append(h)

        # Determine highest severity
        highest_sev = "NONE"
        highest_val = -1
        for h in intersected:
            val = SEVERITY_ORDER.get(h.severity, 0)
            if val > highest_val:
                highest_val = val
                highest_sev = h.severity

        return LocationHazardWarning(
            is_in_hazard_zone=len(intersected) > 0,
            hazard_count=len(intersected),
            highest_severity=highest_sev,
            intersected_hazards=intersected,
            spatial_rule="Ray-casting Point-in-Polygon (PIP) for zone boundaries; 150m Haversine radius for point hazards.",
            disclaimer="Absence of an alert does NOT guarantee that the area is safe. Urban flash floods, blocked drains, and unmonitored sectors may pose extreme danger without recorded alerts. Always obey official civil defense directives."
        )


_hazard_service: Optional[HazardService] = None


def get_hazard_service() -> HazardService:
    """Singleton provider for HazardService."""
    global _hazard_service
    if _hazard_service is None:
        _hazard_service = HazardService()
    return _hazard_service
