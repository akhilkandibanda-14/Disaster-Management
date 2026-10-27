from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request

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
    service: IncidentService = Depends(get_incident_service),
) -> IncidentResponse:
    """
    Submits a new citizen flood incident report within Greater Hyderabad.
    Enforces geographic boundary checks, rate-limiting, and privacy protection.
    Reports are initially labeled PUBLIC_UNVERIFIED_REPORT until verified by disaster teams.
    """
    client_ip = get_client_ip(request)
    try:
        return service.create_incident(incident, client_ip=client_ip)
    except PermissionError as pe:
        raise HTTPException(status_code=429, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit incident report: {str(e)}")


@router.get("", response_model=IncidentListResponse)
def list_incident_reports(
    category: Optional[str] = Query(None, description="Filter by flood category"),
    status: Optional[str] = Query(None, description="Filter by verification status (PENDING_REVIEW, VERIFIED_MUNICIPAL, REJECTED, RESOLVED)"),
    severity: Optional[str] = Query(None, description="Filter by severity (LOW, MODERATE, HIGH, CRITICAL)"),
    limit: int = Query(50, ge=1, le=200, description="Max reports to return"),
    service: IncidentService = Depends(get_incident_service),
) -> IncidentListResponse:
    """
    Returns sanitized list of citizen flood incident reports.
    Reporter private information (names, contact numbers) is strictly stripped.
    """
    return service.list_incidents(
        category=category,
        status=status,
        severity=severity,
        limit=limit,
    )


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident_by_id(
    incident_id: str,
    service: IncidentService = Depends(get_incident_service),
) -> IncidentResponse:
    """Retrieves a single incident report by ID."""
    report = service.get_incident(incident_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Incident report '{incident_id}' not found.")
    return report


@router.patch("/{incident_id}/status", response_model=IncidentResponse)
def update_incident_verification_status(
    incident_id: str,
    status_update: IncidentStatusUpdate,
    service: IncidentService = Depends(get_incident_service),
) -> IncidentResponse:
    """
    Updates operational verification status of a flood incident report.
    Allows disaster authorities to confirm, reject, or mark reports as resolved.
    """
    updated = service.update_status(incident_id, status_update)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Incident report '{incident_id}' not found.")
    return updated
