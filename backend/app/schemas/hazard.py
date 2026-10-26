from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from pydantic import BaseModel, Field, field_validator


class GeoJSONGeometry(BaseModel):
    type: Literal["Point", "Polygon", "MultiPolygon", "LineString"]
    coordinates: Any

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, v, info):
        geom_type = info.data.get("type")
        if not v:
            raise ValueError("Coordinates cannot be empty")

        if geom_type == "Point":
            if not isinstance(v, (list, tuple)) or len(v) < 2:
                raise ValueError("Point coordinates must be [longitude, latitude]")
            lon, lat = v[0], v[1]
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                raise ValueError(f"Point coordinates out of bounds: lon={lon}, lat={lat}")

        elif geom_type == "Polygon":
            if not isinstance(v, list) or len(v) == 0:
                raise ValueError("Polygon coordinates must be a list of linear rings")
            for ring in v:
                if not isinstance(ring, list) or len(ring) < 4:
                    raise ValueError("Each polygon ring must have at least 4 coordinates")
                # Ring must be closed
                first, last = ring[0], ring[-1]
                if first[0] != last[0] or first[1] != last[1]:
                    raise ValueError(f"Polygon ring is not closed: first={first}, last={last}")
                for pt in ring:
                    if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                        raise ValueError("Polygon position must be [longitude, latitude]")
                    lon, lat = pt[0], pt[1]
                    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                        raise ValueError(f"Coordinate out of bounds: lon={lon}, lat={lat}")

        elif geom_type == "MultiPolygon":
            if not isinstance(v, list):
                raise ValueError("MultiPolygon coordinates must be a list of Polygons")
            for poly in v:
                for ring in poly:
                    if len(ring) < 4 or ring[0] != ring[-1]:
                        raise ValueError("MultiPolygon ring must be closed with at least 4 coordinates")

        return v


ALLOWED_FLOOD_HAZARD_TYPES = {
    "FLOOD",
    "FLOOD_ZONE",
    "RIVER_OVERFLOW",
    "URBAN_INUNDATION",
    "WATERLOGGING",
    "WATER_STAGNATION",
    "FLASH_FLOOD",
    "FLOOD_RELATED_HEAVY_RAINFALL",
    "SEVERE_WEATHER_ALERT",  # Retained for backwards compatibility with flood-related severe rain advisories
}

DISALLOWED_NON_FLOOD_TYPES = {
    "TSUNAMI",
    "COASTAL_SURGE",
    "STORM_SURGE",
    "EARTHQUAKE",
    "SEISMIC",
    "CYCLONE",
    "HURRICANE",
    "TYPHOON",
    "TORNADO",
    "WILDFIRE",
    "FOREST_FIRE",
    "FIRE",
    "LANDSLIDE",
    "AVALANCHE",
    "MUD_SLIDE",
    "DROUGHT",
    "VOLCANO",
    "VOLCANIC",
    "HEATWAVE",
    "COLD_WAVE",
}


class HazardRecord(BaseModel):
    hazard_id: str = Field(..., description="Unique hazard identifier")
    hazard_type: str = Field(
        ..., 
        description="Type of flood hazard (FLOOD, RIVER_OVERFLOW, URBAN_INUNDATION, WATERLOGGING, WATER_STAGNATION, FLASH_FLOOD, FLOOD_RELATED_HEAVY_RAINFALL)"
    )
    title: str = Field(..., description="Descriptive title of the hazard")
    description: str = Field(..., description="Detailed situation description")
    severity: Literal["UNKNOWN", "LOW", "MODERATE", "HIGH", "SEVERE", "EXTREME"] = Field(
        default="UNKNOWN", 
        description="Assessed severity level. Defaults to UNKNOWN if not provided by source."
    )
    
    # Spatial definitions
    latitude: Optional[float] = Field(None, description="Centroid or representative latitude (-90 to 90)")
    longitude: Optional[float] = Field(None, description="Centroid or representative longitude (-180 to 180)")
    geometry: Optional[GeoJSONGeometry] = Field(None, description="Validated GeoJSON geometry object")
    
    # Source attribution & provenance
    source_name: str = Field(..., description="Publishing organization or system")
    source_url: Optional[str] = Field(None, description="Direct URL to source data or portal")
    source_type: Literal[
        "OFFICIAL_ALERT", 
        "MODEL_FORECAST", 
        "OBSERVATION", 
        "HISTORICAL_VULNERABILITY", 
        "PUBLIC_UNVERIFIED", 
        "DEMO", 
        "UNAVAILABLE"
    ] = Field(
        default="PUBLIC_UNVERIFIED",
        description="Explicit provenance classification distinguishing alerts, model forecasts, physical observations, and unverified data"
    )
    
    # Detailed measurement / forecast provenance
    requested_coordinates: Optional[Tuple[float, float]] = Field(None, description="Original query coordinates (lat, lon)")
    returned_coordinates: Optional[Tuple[float, float]] = Field(None, description="Actual provider grid/station coordinates (lat, lon)")
    measurement_unit: Optional[str] = Field(None, description="Physical or modeled measurement unit (e.g. m³/s, mm, m)")
    forecast_date: Optional[str] = Field(None, description="Forecast target date string (e.g. YYYY-MM-DD)")
    raw_value: Optional[float] = Field(None, description="Unscaled continuous value from source feed (e.g. discharge rate)")
    catchment_context: Optional[str] = Field(None, description="Hydrological basin or watershed attribution")
    administrative_area: Optional[str] = Field(None, description="District, mandal, or municipal zone covered")
    geographic_uncertainty: Optional[str] = Field(None, description="Explicit statement of spatial resolution or boundary precision limitations")
    
    # Timestamps & validity
    publication_time: Optional[datetime] = Field(None, description="When the record was issued by the publisher")
    last_retrieved: datetime = Field(..., description="Timestamp when record was retrieved by SafeMap AI")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp if applicable")
    is_active: bool = Field(True, description="Whether hazard is actively in effect")
    is_stale: bool = Field(False, description="Whether data has expired or is beyond freshness window")
    
    # Data status & verification
    data_status: Literal["AUTHORITATIVE", "PUBLIC_UNVERIFIED", "STALE", "DEMO"] = Field(
        ..., 
        description="Truthfulness label: AUTHORITATIVE (official live feed), PUBLIC_UNVERIFIED (historical/static public data), STALE (expired), DEMO (simulated)"
    )
    verification_note: str = Field(
        ..., 
        description="Explicit notice explaining the data source limitations and verification status"
    )

    @field_validator("hazard_type")
    @classmethod
    def validate_hazard_type(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("hazard_type must be a non-empty string")
        norm = v.strip().upper()
        if norm in DISALLOWED_NON_FLOOD_TYPES:
            raise ValueError(
                f"Unsupported non-flood disaster hazard type: '{v}'. "
                f"SafeMap AI is restricted exclusively to flood-management hazards."
            )
        if norm not in ALLOWED_FLOOD_HAZARD_TYPES:
            raise ValueError(
                f"Invalid hazard type '{v}'. Supported flood hazard types are: "
                f"{', '.join(sorted(ALLOWED_FLOOD_HAZARD_TYPES))}."
            )
        return norm

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v):
        if v is not None and not (-90.0 <= v <= 90.0):
            raise ValueError(f"Latitude out of bounds: {v}")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v):
        if v is not None and not (-180.0 <= v <= 180.0):
            raise ValueError(f"Longitude out of bounds: {v}")
        return v


class LocationHazardWarning(BaseModel):
    is_in_hazard_zone: bool = Field(..., description="True if coordinates intersect a known hazard zone or point proximity")
    hazard_count: int = Field(0, description="Number of intersected hazards")
    highest_severity: str = Field("NONE", description="Highest severity among intersected hazards")
    intersected_hazards: List[HazardRecord] = Field(default_factory=list, description="List of intersecting hazards")
    spatial_rule: str = Field(
        default="Ray-casting Point-in-Polygon (PIP) for zone boundaries; 150m Haversine radius for point hazards.",
        description="Documented spatial intersection method"
    )
    disclaimer: str = Field(
        default="Absence of an alert does NOT guarantee that the area is safe. Urban flash floods, blocked drains, and unmonitored sectors may pose extreme danger without recorded alerts. Always obey official civil defense directives.",
        description="Mandatory safety disclaimer: missing data never implies safety"
    )


class HazardListResponse(BaseModel):
    total: int = Field(..., description="Total hazards matching request")
    hazards: List[HazardRecord] = Field(default_factory=list)
    authoritative_count: int = Field(0, description="Count of authoritative live alerts")
    unverified_count: int = Field(0, description="Count of public unverified records")
    demo_count: int = Field(0, description="Count of simulated demo records")
    stale_count: int = Field(0, description="Count of stale/expired records")
    retrieved_at: datetime = Field(..., description="Timestamp of API response generation")
    provider_warnings: List[str] = Field(
        default_factory=list,
        description="Warnings if any external provider was unavailable, timed out, or returned stale records"
    )
    data_disclaimer: str = Field(
        default="Flood hazard layers represent a synthesis of authoritative alerts, public surveys, and hydrological forecasts. Simulated records are labeled [DEMO]. Safety is not guaranteed.",
        description="Truth in data notice"
    )
