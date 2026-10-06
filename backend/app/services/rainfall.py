from datetime import date, timedelta
import httpx
from fastapi import HTTPException
from app.schemas.rainfall import AntecedentRainfallResponse

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

def calculate_antecedent_rainfall(
    latitude: float,
    longitude: float,
    target_date: date
) -> AntecedentRainfallResponse:
    # We need the 10 days BEFORE the target date.
    end_date = target_date - timedelta(days=1)
    start_date = target_date - timedelta(days=10)
    
    # Check if target date is in the future.
    # Open-Meteo archive generally only goes up to a few days ago, but we at least
    # prevent future dates where data wouldn't exist.
    if target_date > date.today():
        raise HTTPException(status_code=400, detail="Target date cannot be in the future.")

    try:
        response = httpx.get(
            OPEN_METEO_ARCHIVE_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "daily": "rain_sum",
                "timezone": "Asia/Kolkata"
            },
            timeout=15,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Open-Meteo API error: {e.response.status_code}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Open-Meteo API timeout.")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Open-Meteo network failure: {e}")

    try:
        payload = response.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Invalid JSON response from Open-Meteo.")

    daily = payload.get("daily", {})
    times = daily.get("time", [])
    rain_sums = daily.get("rain_sum", [])

    if not times or not rain_sums or len(times) != 10 or len(rain_sums) != 10:
        raise HTTPException(status_code=404, detail="Insufficient historical rainfall data returned.")

    # rain_sums are chronologically ordered (D-10 to D-1)
    # E.g. times[0] is D-10, times[9] is D-1
    # We will reverse them to make D-1 at index 0, D-2 at index 1, ... D-10 at index 9
    # This makes cumulative calculations more intuitive.
    reversed_rains = list(reversed(rain_sums))
    reversed_times = list(reversed(times))
    
    # Check for missing/null values
    if any(r is None for r in reversed_rains):
        raise HTTPException(status_code=404, detail="Missing or null rainfall values in historical data.")

    daily_values = {t: r for t, r in zip(reversed_times, reversed_rains)}

    cumulative_rains = []
    current_sum = 0.0
    for r in reversed_rains:
        current_sum += float(r)
        cumulative_rains.append(current_sum)
    
    # cumulative_rains[0] = T1d
    # cumulative_rains[1] = T2d
    # ...
    # cumulative_rains[9] = T10d

    return AntecedentRainfallResponse(
        latitude=latitude,
        longitude=longitude,
        target_date=target_date,
        T1d=round(cumulative_rains[0], 2),
        T2d=round(cumulative_rains[1], 2),
        T3d=round(cumulative_rains[2], 2),
        T4d=round(cumulative_rains[3], 2),
        T5d=round(cumulative_rains[4], 2),
        T6d=round(cumulative_rains[5], 2),
        T7d=round(cumulative_rains[6], 2),
        T8d=round(cumulative_rains[7], 2),
        T9d=round(cumulative_rains[8], 2),
        T10d=round(cumulative_rains[9], 2),
        daily_rainfall_values=daily_values
    )
