from fastapi import APIRouter, HTTPException, Query
from app.schemas.gauge import NearestGaugeResponse
from app.services.gauge_reference import GaugeReferenceService

router = APIRouter()
gauge_service = GaugeReferenceService()

@router.get("/nearest", response_model=NearestGaugeResponse)
def get_nearest_gauge(
    latitude: float = Query(..., description="Latitude of the location"),
    longitude: float = Query(..., description="Longitude of the location"),
    max_distance_km: float = Query(50.0, description="Maximum allowed distance to nearest gauge in km")
):
    """
    Finds the nearest INDOFLOODS gauge to the provided coordinates.
    Returns the gauge ID, distance, and pre-computed static environmental features 
    if within the max_distance_km threshold.
    """
    response = gauge_service.get_nearest_gauge(
        latitude=latitude,
        longitude=longitude,
        max_dist_km=max_distance_km
    )
    
    # We do not raise HTTPException if not in coverage, we just return the response 
    # indicating within_model_coverage=False so the client knows it was rejected gracefully.
    return response
