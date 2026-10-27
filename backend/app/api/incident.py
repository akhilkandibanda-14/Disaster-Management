from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.incident import (
    IncidentCreate,
    IncidentListResponse,
    IncidentResponse,
    IncidentStatusUpdate,
)
from app.services.incident import IncidentService, get_incident_service

router = APIRouter(prefix="/incidents", tags=["incidents"])


def get_client_ip(request: Request) -> str:
    """Extracts client IP address safely considering reverse proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


@router.post("", response_model=IncidentResponse, status_code=201)
def submit_incident_report(
    incident: IncidentCreate,
    request: Request,
    db: Session = Depends(get_db),
    service: IncidentService = Depends(get_incident_service),
) -> IncidentResponse:
    """
    Submits a new citizen flood incident report within Greater Hyderabad.
    Enforces geographic boundary checks, rate-limiting, and privacy protection.
    Reports are initially labeled PUBLIC_UNVERIFIED_REPORT until verified by disaster teams.
    """
    client_ip = get_client_ip(request)
    try:
        return service.create_incident(incident, client_ip=client_ip, db=db)
    except PermissionError as pe:
        raise HTTPException(status_code=429, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while processing the incident report.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit incident report: {str(e)}")


@router.get("", response_model=IncidentListResponse)
def list_incident_reports(
    category: Optional[str] = Query(None, description="Filter by flood category"),
    status: Optional[str] = Query(None, description="Filter by verification status (PENDING_REVIEW, VERIFIED_MUNICIPAL, REJECTED, RESOLVED)"),
    severity: Optional[str] = Query(None, description="Filter by severity (LOW, MODERATE, HIGH, CRITICAL)"),
    limit: int = Query(50, ge=1, le=200, description="Max reports to return"),
    db: Session = Depends(get_db),
    service: IncidentService = Depends(get_incident_service),
) -> IncidentListResponse:
    """
    Returns sanitized list of citizen flood incident reports.
    Reporter private information (names, contact numbers) is strictly stripped.
    """
    try:
        return service.list_incidents(
            category=category,
            status=status,
            severity=severity,
            limit=limit,
            db=db,
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while retrieving incident reports.",
        )


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident_by_id(
    incident_id: str,
    db: Session = Depends(get_db),
    service: IncidentService = Depends(get_incident_service),
) -> IncidentResponse:
    """Retrieves a single incident report by ID."""
    try:
        report = service.get_incident(incident_id, db=db)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while retrieving the incident report.",
        )
    if not report:
        raise HTTPException(status_code=404, detail=f"Incident report '{incident_id}' not found.")
    return report


@router.patch("/{incident_id}/status", response_model=IncidentResponse)
def update_incident_verification_status(
    incident_id: str,
    status_update: IncidentStatusUpdate,
    db: Session = Depends(get_db),
    service: IncidentService = Depends(get_incident_service),
) -> IncidentResponse:
    """
    Updates community verification status of a citizen flood report.
    Permits public community corroboration ('COMMUNITY_CORROBORATED') and public resolution observation ('COMMUNITY_RESOLUTION_OBSERVED').
    Rejects unauthorized claims of official municipal verification ('VERIFIED_MUNICIPAL', 'REJECTED') or verified closure ('RESOLVED') with HTTP 403.
    """
    requested_status = status_update.verification_status.upper()
    if requested_status in ("VERIFIED_MUNICIPAL", "RESOLVED", "REJECTED"):
        raise HTTPException(
            status_code=403,
            detail=(
                f"Unauthorized provenance escalation / status transition: Public web requests cannot assert '{requested_status}'. "
                "Official incident resolution ('RESOLVED') and municipal verification ('VERIFIED_MUNICIPAL') "
                "require authoritative institutional telemetry or emergency dispatch intake. "
                "Permitted public community actions are: COMMUNITY_CORROBORATED, COMMUNITY_RESOLUTION_OBSERVED."
            ),
        )

    try:
        updated = service.update_status(incident_id, status_update, db=db, is_institutional=False)
    except PermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while updating the incident status.",
        )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Incident report '{incident_id}' not found.")
    return updated


@router.post("/{incident_id}/corroborate", response_model=IncidentResponse)
def corroborate_incident(
    incident_id: str,
    db: Session = Depends(get_db),
    service: IncidentService = Depends(get_incident_service),
) -> IncidentResponse:
    """
    Public community action: Corroborates an active citizen flood report.
    Increments corroboration count without escalating to municipal verification.
    """
    status_update = IncidentStatusUpdate(
        verification_status="COMMUNITY_CORROBORATED",
        verification_note="Community corroboration: additional citizen observed active flooding.",
    )
    try:
        updated = service.update_status(incident_id, status_update, db=db, is_institutional=False)
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error recording community corroboration.")
    if not updated:
        raise HTTPException(status_code=404, detail=f"Incident report '{incident_id}' not found.")
    return updated


@router.post("/{incident_id}/resolution-observation", response_model=IncidentResponse)
def report_resolution_observation(
    incident_id: str,
    db: Session = Depends(get_db),
    service: IncidentService = Depends(get_incident_service),
) -> IncidentResponse:
    """
    Public community action: Submits a citizen observation that floodwaters are receding or cleared.
    Records community observation note without treating it as verified municipal closure.
    """
    status_update = IncidentStatusUpdate(
        verification_status="COMMUNITY_RESOLUTION_OBSERVED",
        verification_note="Citizen observation: floodwater observed receding or cleared (awaiting municipal confirmation).",
    )
    try:
        updated = service.update_status(incident_id, status_update, db=db, is_institutional=False)
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error recording resolution observation.")
    if not updated:
        raise HTTPException(status_code=404, detail=f"Incident report '{incident_id}' not found.")
    return updated

