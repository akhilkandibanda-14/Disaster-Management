from fastapi import APIRouter, HTTPException, Query

from app.config import is_in_hyderabad
from app.schemas.weather import WeatherResponse
from app.services.weather import fetch_weather

router = APIRouter(tags=["weather"])


@router.get("/weather", response_model=WeatherResponse)
def current_weather(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
) -> WeatherResponse:
    if not is_in_hyderabad(latitude, longitude):
        raise HTTPException(status_code=422, detail="This service currently supports Hyderabad coordinates only.")
    try:
        return fetch_weather(latitude, longitude)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
