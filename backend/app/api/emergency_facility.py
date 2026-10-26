from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.auth import require_admin
from app.config import settings
from app.schemas.emergency_facility import EmergencyFacility, EmergencyFacilityListResponse, VerificationPromotionRequest
from app.services.emergency_facility import EmergencyFacilityService, get_emergency_facility_service
from app.utils.observability import health_monitor

router = APIRouter(tags=["emergency-facilities"])


@router.get("/emergency-facilities", response_model=EmergencyFacilityListResponse)
def get_emergency_facilities(
    facility_type: Optional[str] = Query(None, description="Filter by type: HOSPITAL, SHELTER, EMERGENCY_CENTER, or ALL"),
    latitude: Optional[float] = Query(None, ge=-90, le=90, description="Latitude for distance calculation"),
    longitude: Optional[float] = Query(None, ge=-180, le=180, description="Longitude for distance calculation"),
    radius_km: Optional[float] = Query(None, gt=0, description="Radius in km to filter facilities"),
    data_status: Optional[str] = Query(None, description="Filter by data_status: PUBLIC_UNVERIFIED, VERIFIED, DEMO"),
    service: EmergencyFacilityService = Depends(get_emergency_facility_service)
) -> EmergencyFacilityListResponse:
    """
    Retrieve emergency facilities (hospitals, emergency centers, and shelters).
    Preserves truth in data: unverified facilities are explicitly labeled PUBLIC_UNVERIFIED.
    Live capacities and triage status are not fabricated when unknown.
    """
    try:
        facilities = service.get_facilities(
            facility_type=facility_type,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            data_status=data_status,
            include_demo=settings.demo_mode
        )
        loc_ver_count = sum(1 for f in facilities if f.location_verified)
        op_ver_count = sum(1 for f in facilities if f.operational_status_verified)
        cap_ver_count = sum(1 for f in facilities if f.capacity_verified)
        unver_status_count = sum(1 for f in facilities if not f.operational_status_verified or f.operational_status == "UNKNOWN")
        unver_cap_count = sum(1 for f in facilities if not f.capacity_verified or f.capacity is None)

        return EmergencyFacilityListResponse(
            facilities=facilities,
            total=len(facilities),
            location_verified_count=loc_ver_count,
            operational_status_verified_count=op_ver_count,
            capacity_verified_count=cap_ver_count,
            unverified_status_count=unver_status_count,
            unverified_capacity_count=unver_cap_count,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching emergency facilities: {str(e)}")


@router.get("/emergency-facilities/{facility_id}", response_model=EmergencyFacility)
def get_emergency_facility(
    facility_id: str,
    service: EmergencyFacilityService = Depends(get_emergency_facility_service)
) -> EmergencyFacility:
    """
    Retrieve a specific emergency facility by ID.
    """
    facility = service.get_facility_by_id(facility_id)
    if not facility:
        raise HTTPException(status_code=404, detail=f"Emergency facility '{facility_id}' not found.")
    return facility


@router.post("/emergency-facilities/{facility_id}/verify", response_model=EmergencyFacility)
def verify_facility_status(
    facility_id: str,
    payload: VerificationPromotionRequest,
    user_role: str = Depends(require_admin),
    service: EmergencyFacilityService = Depends(get_emergency_facility_service),
) -> EmergencyFacility:
    """
    Promotes or updates the verification status of an emergency facility based on authoritative live evidence.
    Strictly restricted to authorized administrators (HTTP 401/403 enforced).
    Rejects unverified promotion attempts lacking legitimate evidence documentation.
    """
    if not payload.verification_evidence_source or len(payload.verification_evidence_source.strip()) < 5:
        raise HTTPException(
            status_code=400,
            detail="Legitimate verification promotion requires an authoritative evidence source citation (minimum 5 characters)."
        )

    try:
        updated = service.update_facility_verification(
            facility_id=facility_id,
            operational_status_verified=payload.operational_status_verified,
            capacity_verified=payload.capacity_verified,
            operational_status=payload.operational_status,
            capacity=payload.capacity,
            data_status=payload.data_status,
            evidence_source=payload.verification_evidence_source.strip(),
            verification_note=payload.verification_note,
        )
        health_monitor.record_verification_promotion(
            facility_id=facility_id,
            admin_actor=user_role,
            evidence_source=payload.verification_evidence_source,
            updated_fields=payload.model_dump(exclude_unset=True),
        )
        return updated
    except KeyError as ke:
        raise HTTPException(status_code=404, detail=str(ke))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error promoting facility verification status: {str(e)}")

