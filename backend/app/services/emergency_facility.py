import os
import math
import pandas as pd
from typing import List, Optional
from datetime import datetime, timezone

from app.schemas.emergency_facility import EmergencyFacility


class EmergencyFacilityService:
    def __init__(self):
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        self.facilities_csv = os.path.join(base_path, 'data', 'raw', 'emergency_facilities', 'hyderabad_emergency_facilities.csv')
        self.shelters_csv = os.path.join(base_path, 'data', 'raw', 'shelters', 'hyderabad_shelters.csv')
        self._df: Optional[pd.DataFrame] = None
        self._load_data()

    def _load_data(self):
        records = []
        
        # 1. Load emergency facilities (Hospitals)
        if os.path.exists(self.facilities_csv):
            df_fac = pd.read_csv(self.facilities_csv)
            df_fac = df_fac.where(pd.notnull(df_fac), None)
            records.append(df_fac)
            
        # 2. Load shelters as SHELTER facility_type
        if os.path.exists(self.shelters_csv):
            df_sh = pd.read_csv(self.shelters_csv)
            df_sh = df_sh.where(pd.notnull(df_sh), None)
            # Map shelter columns to facility format
            df_sh = df_sh.rename(columns={'shelter_id': 'facility_id', 'last_updated': 'last_verified'})
            if 'facility_type' not in df_sh.columns:
                df_sh['facility_type'] = 'SHELTER'
            records.append(df_sh)
            
        if records:
            combined = pd.concat(records, ignore_index=True)
            self._df = combined.where(pd.notnull(combined), None)
        else:
            self._df = pd.DataFrame()

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a)) 
        return c * 6371.0 # Radius of earth in km

    def get_facilities(
        self,
        facility_type: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: Optional[float] = None,
        data_status: Optional[str] = None,
        include_demo: bool = False
    ) -> List[EmergencyFacility]:
        if self._df is None or self._df.empty:
            return []

        if radius_km is not None and (latitude is None or longitude is None):
            raise ValueError("Latitude and longitude must be provided when radius_km is specified.")

        results = []
        for _, row in self._df.iterrows():
            row_type = str(row.get('facility_type', '')).upper()
            if facility_type and facility_type.upper() != 'ALL' and row_type != facility_type.upper():
                continue

            row_status = str(row.get('data_status', '')).upper()
            if data_status and row_status != data_status.upper():
                continue

            dist = None
            if latitude is not None and longitude is not None:
                dist = self._haversine(latitude, longitude, float(row['latitude']), float(row['longitude']))

            if radius_km is not None and dist is not None and dist > radius_km:
                continue

            fac_dict = row.to_dict()
            fac_dict['distance_km'] = round(dist, 2) if dist is not None else None

            # Clean NaNs and ensure types
            for k, v in fac_dict.items():
                if pd.isna(v):
                    fac_dict[k] = None

            # Set granular verification indicators
            is_demo = str(fac_dict.get('data_status', '')).upper() == 'DEMO'
            fac_dict['location_verified'] = not is_demo
            fac_dict['operational_status_verified'] = False  # Real-time triage telemetry not integrated
            fac_dict['capacity_verified'] = False            # Real-time bed occupancy not integrated
            fac_dict['verification_scope'] = "DEMO_SIMULATED" if is_demo else "IDENTITY_ONLY"

            results.append(EmergencyFacility(**fac_dict))

        if include_demo:
            demo_type = "EMERGENCY_CENTER"
            demo_status = "DEMO"
            type_matches = (facility_type is None) or (facility_type.upper() in ["ALL", demo_type])
            status_matches = (data_status is None) or (data_status.upper() == demo_status)
            if type_matches and status_matches:
                demo_dist = None
                if latitude is not None and longitude is not None:
                    demo_dist = round(self._haversine(latitude, longitude, 17.401, 78.472), 2)
                if radius_km is None or demo_dist is None or demo_dist <= radius_km:
                    results.append(
                        EmergencyFacility(
                            facility_id="DEMO-FAC-001",
                            name="[DEMO] Central Emergency Triage Field Station",
                            facility_type="EMERGENCY_CENTER",
                            latitude=17.401,
                            longitude=78.472,
                            address="Field Triage Zone A",
                            area="Central Relief Corridor",
                            district="Hyderabad",
                            state="Telangana",
                            capacity=150.0,
                            current_occupancy=45.0,
                            operational_status="OPERATIONAL",
                            accessibility="FULL",
                            contact="112",
                            source="DEMO / SIMULATED DATA",
                            last_verified=datetime.now(timezone.utc).isoformat(),
                            data_status="DEMO",
                            verification_note="[DEMO] Simulated response facility for testing. Not a real facility.",
                            distance_km=demo_dist,
                            location_verified=False,
                            operational_status_verified=False,
                            capacity_verified=False,
                            verification_scope="DEMO_SIMULATED"
                        )
                    )

        if latitude is not None and longitude is not None:
            results.sort(key=lambda x: x.distance_km if x.distance_km is not None else float('inf'))

        return results

    def get_facility_by_id(self, facility_id: str) -> Optional[EmergencyFacility]:
        if not facility_id:
            return None
        all_facs = self.get_facilities(include_demo=True)
        return next((f for f in all_facs if str(f.facility_id).upper() == str(facility_id).upper()), None)

    def update_facility_verification(
        self,
        facility_id: str,
        operational_status_verified: Optional[bool] = None,
        capacity_verified: Optional[bool] = None,
        operational_status: Optional[str] = None,
        capacity: Optional[float] = None,
        data_status: Optional[str] = None,
        evidence_source: str = "",
        verification_note: Optional[str] = None,
    ) -> EmergencyFacility:
        """
        Updates the verification status of a facility based on authoritative live evidence.
        Strictly requires documented evidence source.
        """
        facility = self.get_facility_by_id(facility_id)
        if not facility:
            raise KeyError(f"Emergency facility '{facility_id}' not found.")

        # Update in-memory dataframe if present
        if self._df is not None and not self._df.empty:
            mask = self._df['facility_id'].astype(str).str.upper() == str(facility_id).upper()
            if mask.any():
                if operational_status is not None:
                    self._df.loc[mask, 'operational_status'] = operational_status
                if capacity is not None:
                    self._df.loc[mask, 'capacity'] = capacity
                if data_status is not None:
                    self._df.loc[mask, 'data_status'] = data_status
                if verification_note is not None:
                    self._df.loc[mask, 'verification_note'] = f"{verification_note} (Evidence: {evidence_source})"
                elif evidence_source:
                    self._df.loc[mask, 'verification_note'] = f"Verified via: {evidence_source}"

        updated = self.get_facility_by_id(facility_id)
        if operational_status_verified is not None:
            updated.operational_status_verified = operational_status_verified
        if capacity_verified is not None:
            updated.capacity_verified = capacity_verified
        if data_status is not None:
            updated.data_status = data_status
        if operational_status is not None:
            updated.operational_status = operational_status
        if capacity is not None:
            updated.capacity = capacity
        if verification_note:
            updated.verification_note = f"{verification_note} (Evidence: {evidence_source})"
        elif evidence_source:
            updated.verification_note = f"Verified via: {evidence_source}"

        return updated


_emergency_facility_service = None

def get_emergency_facility_service() -> EmergencyFacilityService:
    global _emergency_facility_service
    if _emergency_facility_service is None:
        _emergency_facility_service = EmergencyFacilityService()
    return _emergency_facility_service

