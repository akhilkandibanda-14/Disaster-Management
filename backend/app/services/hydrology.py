from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime, timezone
import math

from app.schemas.hydrology import WaterLevelResponse

class HydrologyProvider(ABC):
    """Abstract provider for hydrological data."""
    @abstractmethod
    def get_water_level(self, latitude: float, longitude: float) -> Optional[WaterLevelResponse]:
        pass

class DemoHydrologyProvider(HydrologyProvider):
    """Demo provider for hydrological data used during development/demonstration."""
    def __init__(self):
        # Deterministic demo dataset
        self.demo_stations = [
            {
                "station_id": "DEMO-HYD-001",
                "station_name": "DEMO REFERENCE STATION - HYDERABAD",
                "latitude": 17.3850,
                "longitude": 78.4867,
                "water_level": 508.5,
                "discharge": 12.4
            },
            {
                "station_id": "DEMO-MUM-002",
                "station_name": "DEMO REFERENCE STATION - MUMBAI",
                "latitude": 19.0760,
                "longitude": 72.8777,
                "water_level": 5.2,
                "discharge": 45.1
            }
        ]

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371.0 # Earth radius in km
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * \
            math.sin(delta_lambda / 2.0) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def get_water_level(self, latitude: float, longitude: float) -> Optional[WaterLevelResponse]:
        # Find nearest demo station
        nearest_station = None
        min_dist = float('inf')
        for station in self.demo_stations:
            dist = self._haversine(latitude, longitude, station['latitude'], station['longitude'])
            if dist < min_dist:
                min_dist = dist
                nearest_station = station
        
        # If no station within 100km, return None
        if nearest_station is None or min_dist > 100:
            return None

        # Return explicit DEMO data
        return WaterLevelResponse(
            data_status="DEMO",
            data_source="SafeMap AI Demo Hydrological Dataset",
            station_id=nearest_station["station_id"],
            station_name=nearest_station["station_name"],
            latitude=nearest_station["latitude"],
            longitude=nearest_station["longitude"],
            timestamp=datetime.now(timezone.utc),
            water_level=nearest_station["water_level"],
            water_level_unit="m",
            discharge=nearest_station["discharge"],
            discharge_unit="m3/s"
        )

# Singleton instance of the provider
_provider = DemoHydrologyProvider()

def get_hydrology_provider() -> HydrologyProvider:
    """Dependency injection for the hydrology provider."""
    return _provider
