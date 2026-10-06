from datetime import date
from typing import Dict, Any
import pandas as pd
import joblib

from app.services.gauge_reference import GaugeReferenceService
from app.services.rainfall import calculate_antecedent_rainfall
from app.services.prediction import load_model

class ValidationError(Exception):
    pass

class IntegrationService:
    def __init__(self, data_dir: str = None):
        self.gauge_service = GaugeReferenceService(data_dir=data_dir)
        self.pipeline = load_model()
        
        # Get raw feature names (114 numeric + 4 categorical = 118)
        self.num_cols = list(self.pipeline.named_steps['preprocessor'].transformers_[0][2])
        self.cat_cols = list(self.pipeline.named_steps['preprocessor'].transformers_[1][2])
        self.expected_features = set(self.num_cols + self.cat_cols)

    def build_feature_vector(self, latitude: float, longitude: float, target_date: date, max_dist_km: float = 50.0) -> Dict[str, Any]:
        # A. Find nearest gauge
        gauge_res = self.gauge_service.get_nearest_gauge(latitude, longitude, max_dist_km=max_dist_km)
        
        # B. Verify distance
        if not gauge_res.within_model_coverage:
            raise ValidationError(f"Location is outside the model coverage. {gauge_res.message}")

        # C. Retrieve gauge static features
        static_features = gauge_res.gauge_features

        # D. Call rainfall service
        try:
            rain_res = calculate_antecedent_rainfall(latitude, longitude, target_date)
        except Exception as e:
            raise ValidationError(f"Failed to fetch rainfall data: {e}")

        # E. Calculate start_month
        start_month = target_date.month

        # F. Combine all features
        vector = dict(static_features)
        vector['T1d'] = rain_res.T1d
        vector['T2d'] = rain_res.T2d
        vector['T3d'] = rain_res.T3d
        vector['T4d'] = rain_res.T4d
        vector['T5d'] = rain_res.T5d
        vector['T6d'] = rain_res.T6d
        vector['T7d'] = rain_res.T7d
        vector['T8d'] = rain_res.T8d
        vector['T9d'] = rain_res.T9d
        vector['T10d'] = rain_res.T10d
        vector['start_month'] = start_month

        # Feature accounting
        if len(vector) != len(self.expected_features):
            raise ValidationError(f"Feature count mismatch: Expected {len(self.expected_features)}, got {len(vector)}")

        for col in self.expected_features:
            if col not in vector:
                raise ValidationError(f"Missing required feature: {col}")
            # The ML pipeline has a SimpleImputer, so NaN is actually allowed and expected for some gauges.
            # if pd.isna(vector[col]):
            #    raise ValidationError(f"Missing value (NaN) for feature: {col}")

        # Unseen categorical check
        # The pipeline OneHotEncoder might be set to handle_unknown='ignore', 
        # but the prompt requires us to validate if the category was in the trained vocabulary.
        ohe = self.pipeline.named_steps['preprocessor'].transformers_[1][1].named_steps['encoder']
        for i, cat_col in enumerate(self.cat_cols):
            val = vector[cat_col]
            known_categories = ohe.categories_[i]
            if val not in known_categories:
                raise ValidationError(f"Unseen categorical value '{val}' for feature '{cat_col}'.")

        return vector

    def validate_preprocessing(self, vector: Dict[str, Any]) -> int:
        """
        Passes the 118-feature vector through the preprocessor to ensure it outputs 124 features.
        Returns the number of processed features.
        """
        df = pd.DataFrame([vector])[self.num_cols + self.cat_cols]
        processed = self.pipeline.named_steps['preprocessor'].transform(df)
        return processed.shape[1]

    def test_prediction(self, vector: Dict[str, Any]) -> Dict[str, Any]:
        """INTEGRATION TEST ONLY"""
        df = pd.DataFrame([vector])[self.num_cols + self.cat_cols]
        pred = self.pipeline.predict(df)[0]
        prob = self.pipeline.predict_proba(df)[0]
        return {
            "prediction": int(pred),
            "probability_flood": float(prob[0]),
            "probability_severe": float(prob[1])
        }
