from datetime import datetime, timezone

import httpx
from fastapi import HTTPException

from app.config import settings
from app.schemas.weather import WeatherResponse

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


def fetch_weather(latitude: float, longitude: float) -> WeatherResponse:
    if not settings.weather_api_key:
        raise HTTPException(status_code=500, detail="WEATHER_API_KEY is missing or invalid.")

    try:
        response = httpx.get(
            OPENWEATHER_URL,
            params={"lat": latitude, "lon": longitude, "appid": settings.weather_api_key, "units": "metric"},
            timeout=10,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (401, 403):
            raise HTTPException(status_code=401, detail="Weather API authentication failed.")
        elif e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Weather provider location not found.")
        elif e.response.status_code == 429:
            raise HTTPException(status_code=429, detail="Weather API rate limit exceeded.")
        else:
            raise HTTPException(status_code=502, detail=f"Weather provider error: {e.response.status_code}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Weather provider timeout.")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Weather provider network failure: {e}")

    try:
        payload = response.json()
        rain_data = payload.get("rain", {})
        rainfall = rain_data.get("1h", None)
        if rainfall is not None:
            rainfall = max(0.0, float(rainfall))

        main_data = payload.get("main", {})
        wind_data = payload.get("wind", {})
        weather_list = payload.get("weather", [{}])[0]
        condition = weather_list.get("main", "Unknown")
        description = weather_list.get("description", "Unknown")

        return WeatherResponse(
            latitude=latitude,
            longitude=longitude,
            temperature=float(main_data["temp"]),
            humidity=float(main_data["humidity"]),
            rainfall=rainfall,
            wind_speed=max(0.0, float(wind_data.get("speed", 0.0))),
            weather_condition=condition,
            weather_description=description,
            pressure=float(main_data.get("pressure")) if main_data.get("pressure") is not None else None,
            source="OPENWEATHER",
            timestamp=datetime.now(timezone.utc),
            forecast_available=False,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=502, detail=f"Unexpected provider response: {error}")
