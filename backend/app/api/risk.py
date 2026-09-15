from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.schemas.risk import RiskMapResponse
from app.services.risk import generate_risk_map

router = APIRouter(tags=["risk"])


def _get_risk_map(
    south: float = Query(default=17.35, ge=-90, le=90),
    west: float = Query(default=78.45, ge=-180, le=180),
    north: float = Query(default=17.42, ge=-90, le=90),
    east: float = Query(default=78.53, ge=-180, le=180),
) -> RiskMapResponse:
    try:
        result = generate_risk_map(south=south, west=west, north=north, east=east)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if not settings.demo_mode:
        raise HTTPException(status_code=503, detail="Trained geographic risk generation is unavailable until the supplied dataset is trained and the spatial feature source is configured.")
    return result


@router.get("/risk-map", response_model=RiskMapResponse)
def risk_map(
    south: float = Query(default=17.35, ge=-90, le=90),
    west: float = Query(default=78.45, ge=-180, le=180),
    north: float = Query(default=17.42, ge=-90, le=90),
    east: float = Query(default=78.53, ge=-180, le=180),
) -> RiskMapResponse:
    return _get_risk_map(south, west, north, east)


@router.get("/danger-zones", response_model=RiskMapResponse)
def danger_zones(
    south: float = Query(default=17.35, ge=-90, le=90),
    west: float = Query(default=78.45, ge=-180, le=180),
    north: float = Query(default=17.42, ge=-90, le=90),
    east: float = Query(default=78.53, ge=-180, le=180),
) -> RiskMapResponse:
    result = _get_risk_map(south, west, north, east)
    result.zones = [zone for zone in result.zones if zone.risk_level == "HIGH"]
    return result


@router.get("/safe-zones", response_model=RiskMapResponse)
def safe_zones(
    south: float = Query(default=17.35, ge=-90, le=90),
    west: float = Query(default=78.45, ge=-180, le=180),
    north: float = Query(default=17.42, ge=-90, le=90),
    east: float = Query(default=78.53, ge=-180, le=180),
) -> RiskMapResponse:
    result = _get_risk_map(south, west, north, east)
    result.zones = [zone for zone in result.zones if zone.risk_level == "LOW"]
    return result
