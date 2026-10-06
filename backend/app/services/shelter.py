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
        if os.path.exists(self.csv_path):
            self.df = pd.read_csv(self.csv_path)
            # Replace NaNs with None to make JSON serialization valid
            self.df = self.df.where(pd.notnull(self.df), None)
        else:
            self.df = pd.DataFrame()

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a)) 
        r = 6371 # Radius of earth in kilometers
        return c * r

    def get_shelters(self, latitude: Optional[float] = None, longitude: Optional[float] = None, radius_km: Optional[float] = None) -> List[Shelter]:
        if self.df is None or self.df.empty:
            return []
            
        if radius_km is not None and (latitude is None or longitude is None):
            raise ValueError("Latitude and longitude must be provided when radius_km is specified.")
            
        results = []
        for _, row in self.df.iterrows():
            dist = None
            if latitude is not None and longitude is not None:
                dist = self._haversine(latitude, longitude, float(row['latitude']), float(row['longitude']))
                
            if radius_km is not None and dist > radius_km:
                continue
                
            shelter_dict = row.to_dict()
            shelter_dict['distance_km'] = dist
            
            # Ensure proper handling of numpy floats and nan
            for k, v in shelter_dict.items():
                if pd.isna(v):
                    shelter_dict[k] = None
                    
            results.append(Shelter(**shelter_dict))
            
        if latitude is not None and longitude is not None:
            results.sort(key=lambda x: x.distance_km if x.distance_km is not None else float('inf'))
            
        return results

_shelter_service = None

def get_shelter_service() -> ShelterService:
    global _shelter_service
    if _shelter_service is None:
        _shelter_service = ShelterService()
    return _shelter_service
