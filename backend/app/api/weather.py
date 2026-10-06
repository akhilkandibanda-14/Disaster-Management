from fastapi import APIRouter, Query

from app.schemas.weather import WeatherResponse
from app.services.weather import fetch_weather
from app.schemas.rainfall import AntecedentRainfallResponse
from app.services.rainfall import calculate_antecedent_rainfall
from datetime import date

router = APIRouter(tags=["weather"])


@router.get("/weather", response_model=WeatherResponse)
def current_weather(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
) -> WeatherResponse:
    return fetch_weather(latitude, longitude)

@router.get("/weather/antecedent-rainfall", response_model=AntecedentRainfallResponse)
def antecedent_rainfall(
    target_date: date,
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
) -> AntecedentRainfallResponse:
    """
    Fetch and calculate T1d-T10d antecedent rainfall for a given target date.
    """
    return calculate_antecedent_rainfall(latitude, longitude, target_date)
