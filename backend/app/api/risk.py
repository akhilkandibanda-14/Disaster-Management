from fastapi import APIRouter, HTTPException, Query

from app.config import HYDERABAD_BOUNDS, settings
from app.schemas.risk import RiskMapResponse
from app.services.risk import generate_risk_map

router = APIRouter(tags=["risk"])


def _get_risk_map() -> RiskMapResponse:
    try:
        result = generate_risk_map(**HYDERABAD_BOUNDS)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if not settings.demo_mode:
        raise HTTPException(status_code=503, detail="Trained geographic risk generation is unavailable until the supplied dataset is trained and the spatial feature source is configured.")
    return result


@router.get("/risk-map", response_model=RiskMapResponse)
def risk_map(
) -> RiskMapResponse:
    return _get_risk_map()


@router.get("/danger-zones", response_model=RiskMapResponse)
def danger_zones(
) -> RiskMapResponse:
    result = _get_risk_map()
    result.zones = [zone for zone in result.zones if zone.risk_level == "HIGH"]
    return result


@router.get("/safe-zones", response_model=RiskMapResponse)
def safe_zones(
) -> RiskMapResponse:
    result = _get_risk_map()
    result.zones = [zone for zone in result.zones if zone.risk_level == "LOW"]
    return result
