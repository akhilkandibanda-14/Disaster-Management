from fastapi import APIRouter, HTTPException, Depends, Query
from app.schemas.risk_map import GeographicRiskResponse, GaugesResponse
from app.services.risk_map import get_risk_map_service, RiskMapService

router = APIRouter(tags=["risk"])

@router.get("/risk-map", response_model=GeographicRiskResponse)
def risk_map(
    latitude: float = Query(..., description="Latitude of the requested location"),
    longitude: float = Query(..., description="Longitude of the requested location"),
    service: RiskMapService = Depends(get_risk_map_service)
) -> GeographicRiskResponse:
    """
    Get the predicted flood risk for a specific geographic coordinate.
    Prediction is only available if the coordinate is within 50km of an official INDOFLOODS gauge.
    """
    try:
        return service.get_risk_for_location(latitude, longitude)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Error generating geographic risk: {str(error)}")

@router.get("/risk-map/gauges", response_model=GaugesResponse)
def get_gauges(service: RiskMapService = Depends(get_risk_map_service)) -> GaugesResponse:
    """
    Get all official INDOFLOODS gauge coordinates.
    """
    try:
        return GaugesResponse(gauges=service.get_all_gauges())
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Error fetching gauges: {str(error)}")
