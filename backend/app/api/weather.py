from fastapi import APIRouter, Query

from app.schemas.weather import WeatherResponse
from app.services.weather import fetch_weather

router = APIRouter(tags=["weather"])


@router.get("/weather", response_model=WeatherResponse)
def current_weather(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
) -> WeatherResponse:
    return fetch_weather(latitude, longitude)
