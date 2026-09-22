from functools import lru_cache

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
    weather_api_key: str = ""
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    database_pool_size: int = 5
    flood_dataset_path: str = "ml/data/flood_dataset.csv"
    flood_model_path: str = "ml/models/flood_risk_model.joblib"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
