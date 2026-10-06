from typing import List
from app.services.integration import IntegrationService
from app.schemas.risk_map import GeographicRiskResponse, DataSourceInfo, ModelInfo, GaugePoint
from datetime import datetime, timezone
import pandas as pd

class RiskMapService:
    def __init__(self):
        # We reuse the IntegrationService which already enforces the 118 feature rules
        # and has the gauge lookup functionality
        self.integration_service = IntegrationService(data_dir=None)
        
    def get_risk_for_location(self, latitude: float, longitude: float) -> GeographicRiskResponse:
        max_distance = 50.0
        gauge_res = self.integration_service.gauge_service.get_nearest_gauge(
            latitude, longitude, max_dist_km=max_distance
        )
        
        ref_gauge_id = gauge_res.reference_gauge.gauge_id if gauge_res.reference_gauge else None
        dist_km = round(gauge_res.distance_km, 2) if gauge_res.distance_km is not None else None
        now = datetime.now(timezone.utc)
        
        if not gauge_res.within_model_coverage:
            return GeographicRiskResponse(
                latitude=latitude,
                longitude=longitude,
                gauge_id=ref_gauge_id,
                distance_km=dist_km,
                coverage_status="MODEL_UNSUPPORTED",
                prediction_available=False,
                timestamp=now
            )
            
        # Model Supported flow
        # Construct exact 118 raw features using integration service
        # target_date as today for real-time risk map
        vector = self.integration_service.build_feature_vector(
            latitude=latitude,
            longitude=longitude,
            target_date=now.date(),
            max_dist_km=max_distance
        )
        
        df = pd.DataFrame([vector])[self.integration_service.num_cols + self.integration_service.cat_cols]
        
        pred = self.integration_service.pipeline.predict(df)[0]
        prob = self.integration_service.pipeline.predict_proba(df)[0]
        
        classes = self.integration_service.pipeline.named_steps['model'].classes_
        if 1 in classes:
            idx = list(classes).index(1)
            failure_prob = float(prob[idx])
        else:
            failure_prob = float(prob[1]) if len(prob) > 1 else float(prob[0])
            
        risk_level = "HIGH" if failure_prob >= 0.7 else ("MEDIUM" if failure_prob >= 0.4 else "LOW")
        
        return GeographicRiskResponse(
            latitude=latitude,
            longitude=longitude,
            gauge_id=ref_gauge_id,
            distance_km=dist_km,
            coverage_status="MODEL_SUPPORTED",
            prediction_available=True,
            predicted_class=int(pred),
            risk_level=risk_level,
            predicted_severe_flood_probability=failure_prob,
            data_sources=DataSourceInfo(
                rainfall="Open-Meteo Historical API",
                environmental="INDOFLOODS"
            ),
            model_info=ModelInfo(
                name="INDOFLOODS flood severity model",
                raw_features=len(self.integration_service.expected_features),
                processed_features=self.integration_service.pipeline.named_steps['model'].n_features_in_
            ),
            timestamp=now
        )
        
    def get_all_gauges(self) -> List[GaugePoint]:
        gauge_df = self.integration_service.gauge_service.merged_df
        gauges = []
        if gauge_df is not None and not gauge_df.empty:
            for _, row in gauge_df.iterrows():
                gauges.append(GaugePoint(
                    gauge_id=str(row['GaugeID']),
                    latitude=float(row['Latitude']),
                    longitude=float(row['Longitude'])
                ))
        return gauges

_risk_map_service = None

def get_risk_map_service() -> RiskMapService:
    global _risk_map_service
    if _risk_map_service is None:
        _risk_map_service = RiskMapService()
    return _risk_map_service
