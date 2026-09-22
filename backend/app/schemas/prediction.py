from datetime import datetime

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    latitude: float
    longitude: float
    rainfall: float
    temperature: float
    humidity: float
    river_discharge: float
    water_level: float
    elevation: float
    land_cover: str
    soil_type: str
    population_density: float
    infrastructure: float
    historical_floods: float

class PredictionResponse(BaseModel):
    prediction: int
    flood_probability: float
    risk_level: str
    source: str
