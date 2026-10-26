from datetime import datetime, timezone

import httpx
from fastapi import HTTPException

from app.config import settings
from app.schemas.weather import WeatherResponse
from app.utils.observability import health_monitor, log_structured_event

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_demo_weather(latitude: float, longitude: float) -> WeatherResponse:
    now = datetime.now(timezone.utc)
    condition = "Simulated Overcast (Demo)"
    health_monitor.record_weather_observation(
        provider="DEMO_SIMULATOR",
        is_stale=False,
        is_simulated=True,
        warning="Simulated demo data. Real OpenWeather API key is not configured.",
    )
    return WeatherResponse(
        latitude=latitude,
        longitude=longitude,
        temperature=27.5,
        humidity=74.0,
        rainfall=5.2,
        wind_speed=3.8,
        weather_condition=condition,
        weather_description="Demonstration weather conditions (simulated data).",
        condition=condition,
        pressure=1008.0,
        source="DEMO / SIMULATED DATA",
        timestamp=now,
        observation_time=now,
        is_stale=False,
        forecast_available=False,
        warning="Simulated demo data. Real OpenWeather API key is not configured.",
    )


def fetch_weather(latitude: float, longitude: float) -> WeatherResponse:
    now = datetime.now(timezone.utc)
    if not settings.weather_api_key:
        if settings.demo_mode:
            return get_demo_weather(latitude, longitude)
        health_monitor.record_weather_observation(
            provider="OPENWEATHER",
            is_stale=True,
            is_simulated=False,
            warning="WEATHER_API_KEY is missing or invalid.",
        )
        raise HTTPException(status_code=500, detail="WEATHER_API_KEY is missing or invalid.")

    try:
        response = httpx.get(
            OPENWEATHER_URL,
            params={"lat": latitude, "lon": longitude, "appid": settings.weather_api_key, "units": "metric"},
            timeout=5.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        err_msg = f"Weather provider error: {status_code}"
        health_monitor.record_weather_observation(
            provider="OPENWEATHER",
            is_stale=True,
            is_simulated=False,
            warning=err_msg,
        )
        if status_code in (401, 403):
            raise HTTPException(status_code=401, detail="Weather API authentication failed.")
        elif status_code == 404:
            raise HTTPException(status_code=404, detail="Weather provider location not found.")
        elif status_code == 429:
            raise HTTPException(status_code=429, detail="Weather API rate limit exceeded.")
        else:
            raise HTTPException(status_code=502, detail=err_msg)
    except httpx.TimeoutException:
        err_msg = "Weather provider timeout: request timed out."
        health_monitor.record_weather_observation(
            provider="OPENWEATHER",
            is_stale=True,
            is_simulated=False,
            warning=err_msg,
        )
        raise HTTPException(status_code=504, detail=err_msg)
    except httpx.RequestError as e:
        sanitized_e = str(e)
        if settings.weather_api_key and settings.weather_api_key in sanitized_e:
            sanitized_e = sanitized_e.replace(settings.weather_api_key, "[REDACTED]")
        err_msg = f"Weather provider network failure: {sanitized_e}"
        health_monitor.record_weather_observation(
            provider="OPENWEATHER",
            is_stale=True,
            is_simulated=False,
            warning=err_msg,
        )
        raise HTTPException(status_code=502, detail=err_msg)

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

        # Parse observation timestamp from provider (dt unix timestamp)
        dt_val = payload.get("dt")
        obs_time = datetime.fromtimestamp(dt_val, tz=timezone.utc) if dt_val is not None else now
        is_stale = (now - obs_time).total_seconds() > (3 * 3600)  # > 3 hours old
        warning = "Weather observation is older than 3 hours (stale observation)." if is_stale else None

        return WeatherResponse(
            latitude=latitude,
            longitude=longitude,
            temperature=float(main_data["temp"]),
            humidity=float(main_data["humidity"]),
            rainfall=rainfall,
            wind_speed=max(0.0, float(wind_data.get("speed", 0.0))),
            weather_condition=condition,
            weather_description=description,
            condition=condition,
            pressure=float(main_data.get("pressure")) if main_data.get("pressure") is not None else None,
            source="OPENWEATHER",
            timestamp=now,
            observation_time=obs_time,
            is_stale=is_stale,
            forecast_available=False,
            warning=warning,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=502, detail=f"Unexpected provider response: {error}")
