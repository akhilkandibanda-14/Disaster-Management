from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.hazard import (
    ALLOWED_FLOOD_HAZARD_TYPES,
    DISALLOWED_NON_FLOOD_TYPES,
    HazardListResponse,
    HazardRecord,
    LocationHazardWarning,
)
from app.services.hazard import HazardService, get_hazard_service

router = APIRouter(prefix="/flood-hazards", tags=["flood-hazards"])


@router.get("", response_model=HazardListResponse)
def get_flood_hazards(
    hazard_type: Optional[str] = Query(None, description="Filter by flood hazard type (e.g. FLOOD, FLOOD_ZONE, RIVER_OVERFLOW, WATER_STAGNATION, WATERLOGGING, URBAN_INUNDATION, FLASH_FLOOD, FLOOD_RELATED_HEAVY_RAINFALL)"),
    severity: Optional[str] = Query(None, description="Filter by severity (LOW, MODERATE, HIGH, SEVERE, EXTREME)"),
    data_status: Optional[str] = Query(None, description="Filter by data verification status (AUTHORITATIVE, PUBLIC_UNVERIFIED, STALE, DEMO)"),
    include_demo: bool = Query(True, description="Whether to include simulated demo hazards"),
    include_authoritative: bool = Query(True, description="Whether to include live authoritative alerts"),
    service: HazardService = Depends(get_hazard_service),
) -> HazardListResponse:
    """
    Returns verified and simulated flood hazard records, zone boundaries, and weather alerts for Hyderabad.
    Authoritative, municipal unverified, and demo records are distinctly labeled.
    Non-flood disaster hazard queries are rejected.
    """
    if hazard_type:
        ht_norm = hazard_type.strip().upper()
        if ht_norm in DISALLOWED_NON_FLOOD_TYPES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported non-flood hazard type: '{hazard_type}'. "
                    f"SafeMap AI is restricted exclusively to flood-management hazards."
                ),
            )
        if ht_norm not in ALLOWED_FLOOD_HAZARD_TYPES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid hazard type '{hazard_type}'. Supported flood hazard types are: "
                    f"{', '.join(sorted(ALLOWED_FLOOD_HAZARD_TYPES))}."
                ),
            )

    hazards = service.get_hazards(
        hazard_type=hazard_type,
        severity=severity,
        data_status=data_status,
        include_demo=include_demo,
        include_authoritative=include_authoritative,
    )

    auth_count = sum(1 for h in hazards if h.data_status == "AUTHORITATIVE")
    unverified_count = sum(1 for h in hazards if h.data_status == "PUBLIC_UNVERIFIED")
    demo_count = sum(1 for h in hazards if h.data_status == "DEMO")
    stale_count = sum(1 for h in hazards if h.data_status == "STALE" or h.is_stale)

    return HazardListResponse(
        total=len(hazards),
        hazards=hazards,
        authoritative_count=auth_count,
        unverified_count=unverified_count,
        demo_count=demo_count,
        stale_count=stale_count,
        retrieved_at=datetime.now(timezone.utc),
        provider_warnings=service.get_last_provider_warnings(),
        data_disclaimer=(
            "Flood hazards synthesize authoritative alerts (NDMA/GloFAS), municipal studies (GHMC/MRDCL), "
            "and demonstration scenarios. Never assume an area without reported alerts is safe."
        ),
    )


@router.get("/check-location", response_model=LocationHazardWarning)
def check_location_hazard(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude to inspect"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude to inspect"),
    include_demo: bool = Query(True, description="Whether to include simulated demo hazard zones in check"),
    service: HazardService = Depends(get_hazard_service),
) -> LocationHazardWarning:
    """
    Evaluates whether the given geographic coordinates intersect any known active flood hazard zone.
    Returns explicit warning details, highest severity, and mandatory safety limitations notice.
    """
    return service.check_location(
        latitude=latitude,
        longitude=longitude,
        include_demo=include_demo,
    )


@router.get("/{hazard_id}", response_model=HazardRecord)
def get_hazard_by_id(
    hazard_id: str,
    service: HazardService = Depends(get_hazard_service),
) -> HazardRecord:
    """
    Retrieves a single hazard zone or alert by its ID.
    Returns 404 if not found.
    """
    hazard = service.get_hazard_by_id(hazard_id)
    if not hazard:
        raise HTTPException(status_code=404, detail=f"Flood hazard '{hazard_id}' not found.")
    return hazard
