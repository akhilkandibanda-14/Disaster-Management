from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import date
from app.schemas.shelter import ShelterResponse
from app.schemas.shelter_recommendation import ShelterRecommendationResponse
from app.services.shelter import get_shelter_service, ShelterService
from app.services.shelter_recommendation import get_shelter_recommendation_service, ShelterRecommendationService

router = APIRouter(tags=["shelters"])

@router.get("/shelters", response_model=ShelterResponse)
def get_shelters(
    latitude: Optional[float] = Query(None, ge=-90, le=90, description="Latitude for distance calculation"),
    longitude: Optional[float] = Query(None, ge=-180, le=180, description="Longitude for distance calculation"),
    radius_km: Optional[float] = Query(None, gt=0, description="Radius in km to filter shelters (requires lat/lon)"),
    service: ShelterService = Depends(get_shelter_service)
) -> ShelterResponse:
    """
    Get shelter locations. Optionally provide latitude and longitude to calculate distance.
    If radius_km is provided, filters shelters within that radius.
    """
    try:
        shelters = service.get_shelters(latitude=latitude, longitude=longitude, radius_km=radius_km)
        return ShelterResponse(
            shelters=shelters,
            total=len(shelters)
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Error fetching shelters: {str(error)}")

@router.get("/shelters/recommended", response_model=ShelterRecommendationResponse)
def get_recommended_shelters(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude for recommendation"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude for recommendation"),
    radius_km: float = Query(..., gt=0, description="Radius in km to filter shelters"),
    top_n: int = Query(..., ge=1, description="Number of shelters to recommend"),
    target_date: Optional[date] = Query(None, description="Optional date for risk context"),
    service: ShelterRecommendationService = Depends(get_shelter_recommendation_service)
) -> ShelterRecommendationResponse:
    """
    Get recommended candidate shelters for a location, sorted by distance.
    Provides risk context if within supported model area.
    """
    try:
        return service.recommend_shelters(
            latitude=latitude, 
            longitude=longitude, 
            radius_km=radius_km, 
            top_n=top_n, 
            target_date=target_date
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(error)}")
