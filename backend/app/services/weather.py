from datetime import datetime, timezone

import httpx

from app.config import settings
from app.schemas.weather import WeatherResponse

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


def demo_weather(latitude: float, longitude: float) -> WeatherResponse:
    return WeatherResponse(
        latitude=latitude,
        longitude=longitude,
        rainfall=120.0,
        temperature=28.0,
        humidity=91.0,
        wind_speed=18.0,
        pressure=1004.0,
        condition="Heavy rain simulation",
        source="DEMO / SIMULATED DATA",
        timestamp=datetime.now(timezone.utc),
        forecast_available=False,
        warning="This is simulated development data, not a live emergency observation.",
    )


def fetch_weather(latitude: float, longitude: float) -> WeatherResponse:
    if settings.demo_mode and not settings.weather_api_key:
        return demo_weather(latitude, longitude)
    if not settings.weather_api_key:
        raise RuntimeError("WEATHER_API_KEY is not configured and DEMO_MODE is disabled.")

    try:
        response = httpx.get(
            OPENWEATHER_URL,
            params={"lat": latitude, "lon": longitude, "appid": settings.weather_api_key, "units": "metric"},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        rainfall = float(payload.get("rain", {}).get("1h", 0.0))
        main = payload.get("main", {})
        wind = payload.get("wind", {})
        condition = payload.get("weather", [{}])[0].get("description", "Unknown")
        return WeatherResponse(
            latitude=latitude,
            longitude=longitude,
            rainfall=max(0.0, rainfall),
            temperature=float(main["temp"]),
            humidity=float(main["humidity"]),
            wind_speed=max(0.0, float(wind.get("speed", 0.0))),
            pressure=max(0.0, float(main.get("pressure", 0.0))),
            condition=condition,
            source="LIVE / OPENWEATHER",
            timestamp=datetime.now(timezone.utc),
            forecast_available=False,
        )
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
        raise RuntimeError(f"Weather provider unavailable: {error}") from error
