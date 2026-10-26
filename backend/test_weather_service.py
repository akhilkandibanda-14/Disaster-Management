from unittest.mock import MagicMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.services.weather import fetch_weather, get_demo_weather
from app.schemas.weather import WeatherResponse
from fastapi import HTTPException

client = TestClient(app)


def test_get_demo_weather_payload_structure():
    demo = get_demo_weather(17.3850, 78.4867)
    assert isinstance(demo, WeatherResponse)
    assert demo.latitude == 17.3850
    assert demo.longitude == 78.4867
    assert demo.source == "DEMO / SIMULATED DATA"
    assert "Simulated demo data" in demo.warning
    assert "Demo" in demo.weather_condition
    assert demo.condition == demo.weather_condition
    assert demo.temperature is not None
    assert demo.humidity >= 0 and demo.humidity <= 100
    assert demo.wind_speed >= 0
    assert demo.forecast_available is False


def test_fetch_weather_demo_mode_fallback_without_api_key():
    with patch.object(settings, "weather_api_key", ""), patch.object(settings, "demo_mode", True):
        res = fetch_weather(17.3850, 78.4867)
        assert res.source == "DEMO / SIMULATED DATA"
        assert "Simulated demo data" in res.warning
        assert res.weather_condition is not None
        assert res.temperature == 27.5


def test_fetch_weather_missing_key_in_production_raises_500():
    with patch.object(settings, "weather_api_key", ""), patch.object(settings, "demo_mode", False):
        with pytest.raises(HTTPException) as exc_info:
            fetch_weather(17.3850, 78.4867)
        assert exc_info.value.status_code == 500
        assert "WEATHER_API_KEY is missing or invalid" in exc_info.value.detail


def test_api_weather_endpoint_returns_demo_in_demo_mode():
    with patch.object(settings, "weather_api_key", ""), patch.object(settings, "demo_mode", True):
        response = client.get("/weather?latitude=17.3850&longitude=78.4867")
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "DEMO / SIMULATED DATA"
        assert "Simulated demo data" in data["warning"]
        assert data["temperature"] == 27.5
        assert data["weather_condition"] == "Simulated Overcast (Demo)"
        assert data["condition"] == "Simulated Overcast (Demo)"


def test_api_weather_endpoint_returns_500_when_key_missing_in_prod():
    with patch.object(settings, "weather_api_key", ""), patch.object(settings, "demo_mode", False):
        response = client.get("/weather?latitude=17.3850&longitude=78.4867")
        assert response.status_code == 500
        assert "WEATHER_API_KEY is missing or invalid" in response.json()["detail"]


def test_weather_configured_api_success():
    mock_payload = {
        "main": {"temp": 31.2, "humidity": 60.0, "pressure": 1013},
        "wind": {"speed": 4.5},
        "rain": {"1h": 12.4},
        "weather": [{"main": "Rain", "description": "heavy intensity rain"}],
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_payload
    mock_response.raise_for_status.return_value = None

    with patch.object(settings, "weather_api_key", "valid-test-key"):
        with patch("httpx.get", return_value=mock_response):
            res = fetch_weather(17.3850, 78.4867)
            assert res.source == "OPENWEATHER"
            assert res.temperature == 31.2
            assert res.rainfall == 12.4
            assert res.humidity == 60.0
            assert res.weather_condition == "Rain"
            assert res.condition == "Rain"
            assert res.warning is None


def test_weather_configured_api_auth_failure():
    mock_response = MagicMock()
    mock_response.status_code = 401
    err = httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=mock_response)

    with patch.object(settings, "weather_api_key", "invalid-key"):
        with patch("httpx.get", side_effect=err):
            with pytest.raises(HTTPException) as exc_info:
                fetch_weather(17.3850, 78.4867)
            assert exc_info.value.status_code == 401
            assert "Weather API authentication failed" in exc_info.value.detail


def test_weather_configured_api_location_not_found():
    mock_response = MagicMock()
    mock_response.status_code = 404
    err = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=mock_response)

    with patch.object(settings, "weather_api_key", "test-key"):
        with patch("httpx.get", side_effect=err):
            with pytest.raises(HTTPException) as exc_info:
                fetch_weather(17.3850, 78.4867)
            assert exc_info.value.status_code == 404
            assert "Weather provider location not found" in exc_info.value.detail


def test_weather_configured_api_rate_limit():
    mock_response = MagicMock()
    mock_response.status_code = 429
    err = httpx.HTTPStatusError("Too Many Requests", request=MagicMock(), response=mock_response)

    with patch.object(settings, "weather_api_key", "test-key"):
        with patch("httpx.get", side_effect=err):
            with pytest.raises(HTTPException) as exc_info:
                fetch_weather(17.3850, 78.4867)
            assert exc_info.value.status_code == 429
            assert "Weather API rate limit exceeded" in exc_info.value.detail


def test_weather_configured_api_timeout():
    err = httpx.TimeoutException("Connection timed out")

    with patch.object(settings, "weather_api_key", "test-key"):
        with patch("httpx.get", side_effect=err):
            with pytest.raises(HTTPException) as exc_info:
                fetch_weather(17.3850, 78.4867)
            assert exc_info.value.status_code == 504
            assert "Weather provider timeout" in exc_info.value.detail


def test_weather_configured_api_network_failure():
    err = httpx.RequestError("Network is down")

    with patch.object(settings, "weather_api_key", "test-key"):
        with patch("httpx.get", side_effect=err):
            with pytest.raises(HTTPException) as exc_info:
                fetch_weather(17.3850, 78.4867)
            assert exc_info.value.status_code == 502
            assert "Weather provider network failure" in exc_info.value.detail


def test_weather_configured_api_network_failure_redacts_secret():
    secret_key = "super-secret-openweather-key-999"
    err = httpx.RequestError(f"Connection failed for https://api.openweathermap.org/data/2.5/weather?appid={secret_key}")

    with patch.object(settings, "weather_api_key", secret_key):
        with patch("httpx.get", side_effect=err):
            with pytest.raises(HTTPException) as exc_info:
                fetch_weather(17.3850, 78.4867)
            assert exc_info.value.status_code == 502
            # The actual secret key must NEVER appear in the exception or log
            assert secret_key not in exc_info.value.detail
            assert "[REDACTED]" in exc_info.value.detail


def test_settings_weather_api_key_alias_and_sanitization():
    from app.config import Settings
    
    # 1. Accepts standard WEATHER_API_KEY
    cfg1 = Settings(WEATHER_API_KEY="test_key_standard")
    assert cfg1.weather_api_key == "test_key_standard"

    # 2. Accepts OPENWEATHER_API_KEY alias
    cfg2 = Settings(OPENWEATHER_API_KEY="test_key_alias")
    assert cfg2.weather_api_key == "test_key_alias"

    # 3. Strips whitespace and quotes
    cfg3 = Settings(WEATHER_API_KEY="  'quoted_key'  ")
    assert cfg3.weather_api_key == "quoted_key"

    # 4. Cleans placeholder strings
    cfg4 = Settings(WEATHER_API_KEY="placeholder")
    assert cfg4.weather_api_key == ""

    cfg5 = Settings(WEATHER_API_KEY="none")
    assert cfg5.weather_api_key == ""

