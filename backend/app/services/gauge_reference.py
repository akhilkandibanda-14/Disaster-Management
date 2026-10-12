import os
import math
import pandas as pd
from typing import Optional
from app.schemas.gauge import NearestGaugeResponse, Coordinates, ReferenceGauge

from pathlib import Path

class GaugeReferenceService:
    def __init__(self, data_dir: str = None):
        base_path = Path(__file__).resolve().parents[3]
        if data_dir is None:
            self.data_dir = str(base_path / 'data' / 'raw' / 'indofloods')
        else:
            candidate = Path(data_dir)
            if candidate.is_absolute() and candidate.exists():
                self.data_dir = str(candidate)
            elif candidate.exists():
                self.data_dir = str(candidate.resolve())
            elif (base_path / candidate).exists():
                self.data_dir = str((base_path / candidate).resolve())
            else:
                clean_parts = [part for part in candidate.parts if part != '..']
                if clean_parts and (base_path / Path(*clean_parts)).exists():
                    self.data_dir = str((base_path / Path(*clean_parts)).resolve())
                else:
                    self.data_dir = str(candidate)
        
        self.max_allowed_distance_km = 50.0
        self.gauges_df = None
        self.coords_df = None
        self.merged_df = None
        
        self._load_data()

    def _load_data(self):
        catchment_path = os.path.join(self.data_dir, 'catchment_characteristics_indofloods.csv')
        coords_path = os.path.join(self.data_dir, 'gauge_coordinates.csv')
        
        if os.path.exists(catchment_path) and os.path.exists(coords_path):
            self.gauges_df = pd.read_csv(catchment_path)
            self.coords_df = pd.read_csv(coords_path)
            # Merge on GaugeID
            if 'GaugeID' in self.gauges_df.columns and 'GaugeID' in self.coords_df.columns:
                self.merged_df = pd.merge(self.gauges_df, self.coords_df, on='GaugeID', how='inner')
        else:
            self.merged_df = pd.DataFrame()

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance in kilometers between two points 
        on the earth (specified in decimal degrees)
        """
        # Convert decimal degrees to radians 
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        # Haversine formula 
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a)) 
        r = 6371 # Radius of earth in kilometers
        return c * r

    def get_nearest_gauge(self, latitude: float, longitude: float, max_dist_km: float = 50.0) -> NearestGaugeResponse:
        user_loc = Coordinates(latitude=latitude, longitude=longitude)
        
        if self.merged_df is None or self.merged_df.empty:
            return NearestGaugeResponse(
                user_location=user_loc,
                reference_gauge=None,
                distance_km=None,
                max_allowed_distance_km=max_dist_km,
                within_model_coverage=False,
                message="Gauge reference data is missing or empty."
            )
            
        # Ensure latitude and longitude exist
        if 'Latitude' not in self.merged_df.columns or 'Longitude' not in self.merged_df.columns:
             return NearestGaugeResponse(
                user_location=user_loc,
                reference_gauge=None,
                distance_km=None,
                max_allowed_distance_km=max_dist_km,
                within_model_coverage=False,
                message="Gauge coordinate data is missing."
            )
            
        # Calculate distances
        distances = self.merged_df.apply(
            lambda row: self._haversine(latitude, longitude, row['Latitude'], row['Longitude']), 
            axis=1
        )
        
        min_idx = distances.idxmin()
        min_dist = distances.loc[min_idx]
        nearest_gauge_row = self.merged_df.loc[min_idx]
        
        gauge_id = str(nearest_gauge_row['GaugeID'])
        gauge_lat = float(nearest_gauge_row['Latitude'])
        gauge_lon = float(nearest_gauge_row['Longitude'])
        
        ref_gauge = ReferenceGauge(gauge_id=gauge_id, latitude=gauge_lat, longitude=gauge_lon)
        
        if min_dist > max_dist_km:
            return NearestGaugeResponse(
                user_location=user_loc,
                reference_gauge=ref_gauge,
                distance_km=min_dist,
                max_allowed_distance_km=max_dist_km,
                within_model_coverage=False,
                message="Location is outside the geographic coverage of the current INDOFLOODS gauge model."
            )
            
        # Extract gauge features (all columns except GaugeID, Latitude, Longitude)
        features = nearest_gauge_row.drop(['GaugeID', 'Latitude', 'Longitude']).to_dict()
        
        return NearestGaugeResponse(
            user_location=user_loc,
            reference_gauge=ref_gauge,
            distance_km=min_dist,
            max_allowed_distance_km=max_dist_km,
            within_model_coverage=True,
            gauge_features=features
        )

    def get_all_gauges(self):
        if self.merged_df is None or self.merged_df.empty:
            return []
        
        gauges = []
        for _, row in self.merged_df.iterrows():
            gauges.append({
                "gauge_id": str(row['GaugeID']),
                "latitude": float(row['Latitude']),
                "longitude": float(row['Longitude'])
            })
        return gauges
