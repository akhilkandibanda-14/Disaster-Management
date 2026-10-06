from pydantic import BaseModel, Field
from datetime import datetime

class WaterLevelResponse(BaseModel):
    data_status: str = Field(..., description="Status of the data, e.g. DEMO, OBSERVED")
    data_source: str = Field(..., description="Source of the data")
    station_id: str = Field(..., description="Unique identifier for the station")
    station_name: str = Field(..., description="Name of the station")
    latitude: float
    longitude: float
    timestamp: datetime
    water_level: float
    water_level_unit: str = "m"
    discharge: float
    discharge_unit: str = "m3/s"
