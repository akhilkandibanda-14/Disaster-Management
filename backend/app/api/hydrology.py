from fastapi import APIRouter, HTTPException, Depends
from app.schemas.hydrology import WaterLevelResponse
from app.services.hydrology import HydrologyProvider, get_hydrology_provider

router = APIRouter(prefix="/hydrology", tags=["hydrology"])

@router.get("/water-level", response_model=WaterLevelResponse)
def get_water_level(
    latitude: float,
    longitude: float,
    provider: HydrologyProvider = Depends(get_hydrology_provider)
):
    """
    Get water level and discharge for a specific location.
    Currently returns explicitly labelled DEMO data.
    """
    result = provider.get_water_level(latitude, longitude)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="No hydrological station found near the requested coordinates."
        )
    return result
