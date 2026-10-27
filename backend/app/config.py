from functools import lru_cache
import os

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

HYDERABAD_BOUNDS = {
    "south": 17.20,
    "west": 78.20,
    "north": 17.60,
    "east": 78.70,
}


def is_in_hyderabad(latitude: float, longitude: float) -> bool:
    return (
        HYDERABAD_BOUNDS["south"] <= latitude <= HYDERABAD_BOUNDS["north"]
        and HYDERABAD_BOUNDS["west"] <= longitude <= HYDERABAD_BOUNDS["east"]
    )


class Settings(BaseSettings):
    app_env: str = "development"
    demo_mode: bool = True
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/disaster_management"
    google_maps_api_key: str = ""
    weather_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "weather_api_key",
            "WEATHER_API_KEY",
            "openweather_api_key",
            "OPENWEATHER_API_KEY",
        ),
    )
    admin_api_key: str = "safemap-admin-dev-key"
    analyst_api_key: str = "safemap-analyst-dev-key"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    database_pool_size: int = 5
    flood_dataset_path: str = "ml/data/flood_dataset.csv"
    flood_model_path: str = "ml/models/flood_risk_model.joblib"
    log_level: str = "INFO"
    log_format: str = "text"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def is_production(self) -> bool:
        return self.app_env.lower() in ("production", "prod")

    def get_safe_db_summary(self) -> str:
        """Returns sanitized database URL with masked credentials for logging and diagnostics."""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(self.database_url)
            host = parsed.hostname or "localhost"
            port = f":{parsed.port}" if parsed.port else ""
            db_name = parsed.path.lstrip("/") or "disaster_management"
            scheme = parsed.scheme or "postgresql"
            return f"{scheme}://***:***@{host}{port}/{db_name}"
        except Exception:
            return "postgresql://***:***@localhost/disaster_management"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            v_trimmed = v.strip()
            if v_trimmed.startswith("[") and v_trimmed.endswith("]"):
                import json
                try:
                    return json.loads(v_trimmed)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("weather_api_key", mode="before")
    @classmethod
    def clean_weather_api_key(cls, v):
        if isinstance(v, str):
            v_clean = v.strip().strip("'\"")
            if v_clean.lower() in ("none", "null", "placeholder", "your_api_key_here"):
                return ""
            return v_clean
        return "" if v is None else str(v)

    def __init__(self, **values):
        for alias in ("WEATHER_API_KEY", "openweather_api_key", "OPENWEATHER_API_KEY"):
            if alias in values and "weather_api_key" not in values:
                values["weather_api_key"] = values.pop(alias)
        super().__init__(**values)
        if self.app_env.lower() in ("production", "prod", "staging"):
            if "demo_mode" not in values and "DEMO_MODE" not in os.environ:
                self.demo_mode = False

    @model_validator(mode="after")
    def validate_environment(self) -> "Settings":
        env_lower = self.app_env.lower()
        if env_lower in ("production", "prod", "staging"):
            if "demo_mode" not in self.model_fields_set and "DEMO_MODE" not in os.environ:
                self.demo_mode = False
        if "weather_api_key" not in self.model_fields_set and not self.weather_api_key:
            env_key = os.environ.get("WEATHER_API_KEY") or os.environ.get("OPENWEATHER_API_KEY")
            if env_key:
                clean_key = env_key.strip().strip("'\"")
                if clean_key.lower() not in ("none", "null", "placeholder", "your_api_key_here"):
                    self.weather_api_key = clean_key
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

