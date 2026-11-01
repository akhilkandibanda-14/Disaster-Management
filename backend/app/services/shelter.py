import os
import math
import pandas as pd
from typing import List, Optional
from app.schemas.shelter import Shelter

class ShelterService:
    def __init__(self):
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        self.csv_path = os.path.join(base_path, 'data', 'raw', 'shelters', 'hyderabad_shelters.csv')
        self.df = None
        self._load_data()
        
    def _load_data(self):
        self.invalid_record_count = 0
        if os.path.exists(self.csv_path):
            self.df = pd.read_csv(self.csv_path)
            # Replace NaNs with None to make JSON serialization valid
            self.df = self.df.where(pd.notnull(self.df), None)
        else:
            self.df = pd.DataFrame()
        self.data_status = "AVAILABLE" if not self.df.empty else "UNAVAILABLE"

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a)) 
        r = 6371 # Radius of earth in kilometers
        return c * r

    def get_shelters(self, latitude: Optional[float] = None, longitude: Optional[float] = None, radius_km: Optional[float] = None) -> List[Shelter]:
        self.invalid_record_count = 0
        if self.df is None or self.df.empty:
            self.data_status = "UNAVAILABLE"
            return []
            
        if radius_km is not None and (latitude is None or longitude is None):
            raise ValueError("Latitude and longitude must be provided when radius_km is specified.")
        if latitude is not None or longitude is not None:
            try:
                if (
                    latitude is None
                    or longitude is None
                    or not math.isfinite(float(latitude))
                    or not math.isfinite(float(longitude))
                    or not -90 <= float(latitude) <= 90
                    or not -180 <= float(longitude) <= 180
                ):
                    raise ValueError
            except (TypeError, ValueError):
                raise ValueError("Latitude and longitude must be finite values within valid coordinate bounds.")
        if radius_km is not None and (
            not math.isfinite(float(radius_km)) or float(radius_km) <= 0
        ):
            raise ValueError("Radius must be a finite positive value.")
            
        results = []
        for _, row in self.df.iterrows():
            try:
                row_latitude = float(row["latitude"])
                row_longitude = float(row["longitude"])
                if (
                    not math.isfinite(row_latitude)
                    or not math.isfinite(row_longitude)
                    or not -90 <= row_latitude <= 90
                    or not -180 <= row_longitude <= 180
                ):
                    raise ValueError("invalid shelter coordinates")
            except (KeyError, TypeError, ValueError):
                self.invalid_record_count += 1
                continue

            dist = None
            if latitude is not None and longitude is not None:
                dist = self._haversine(latitude, longitude, row_latitude, row_longitude)
                
            if radius_km is not None and dist > radius_km:
                continue
                
            shelter_dict = row.to_dict()
            shelter_dict['distance_km'] = dist
            
            # Ensure proper handling of numpy floats and nan
            for k, v in shelter_dict.items():
                if pd.isna(v):
                    shelter_dict[k] = None
                    
            try:
                results.append(Shelter(**shelter_dict))
            except (TypeError, ValueError):
                self.invalid_record_count += 1

        self.data_status = "AVAILABLE_WITH_INVALID_RECORDS" if self.invalid_record_count else "AVAILABLE"
            
        if latitude is not None and longitude is not None:
            results.sort(key=lambda x: x.distance_km if x.distance_km is not None else float('inf'))
            
        return results

_shelter_service = None

def get_shelter_service() -> ShelterService:
    global _shelter_service
    if _shelter_service is None:
        _shelter_service = ShelterService()
    return _shelter_service
