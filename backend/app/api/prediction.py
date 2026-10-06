from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.config import is_in_hyderabad
from app.schemas.prediction import PredictionRequest, PredictionResponse, IndofloodsModelInput
from app.services.prediction import predict

router = APIRouter(tags=["prediction"])


@router.post("/predict", response_model=PredictionResponse)
def predict_flood_risk(request: PredictionRequest) -> PredictionResponse:
    # We do NOT fabricate inputs. Since the frontend provides PredictionRequest,
    # which lacks T1d-T10d and real catchment features, we cannot make a valid
    # scientific prediction using the INDOFLOODS ML model.
    
    return PredictionResponse(
        prediction=None,
        flood_probability=None,
        risk_level="UNKNOWN",
        source="INDOFLOODS_ML_MODEL",
        message="Additional real environmental inputs (T1d-T10d, catchment data) are required for valid scientific prediction.",
        severe_flood_probability=None,
        model_name="INDOFLOODS Severity Model",
        model_version_status="V1 (Requires full catchment/precipitation schema)"
    )

@router.post("/predict/internal", response_model=PredictionResponse)
def predict_internal(request: IndofloodsModelInput) -> PredictionResponse:
    features = request.model_dump()
    try:
        result = predict(features)
        return PredictionResponse(
            prediction=result.get("predicted_severity"),
            flood_probability=result.get("flood_probability"),
            severe_flood_probability=result.get("severe_flood_probability"),
            risk_level="HIGH" if result.get("severe_flood_probability", 0) >= 0.7 else ("MEDIUM" if result.get("severe_flood_probability", 0) >= 0.4 else "LOW"),
            source="INDOFLOODS_ML_MODEL",
            model_name=result.get("model_name"),
            model_version_status=result.get("model_version_status")
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail="Model file not found. Please train and save the model.") from error
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=400, detail=f"Invalid input or model error: {error}") from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Prediction error: {error}") from error

from app.schemas.prediction import IntegratedPredictionRequest, IntegratedPredictionResponse, LocationResponse, ReferenceGaugeResponse, RainfallResponse, DataSourcesResponse, ModelInfoResponse
from app.services.integration import IntegrationService, ValidationError
import pandas as pd

integration_service = None

@router.post("/predict/integrated", response_model=IntegratedPredictionResponse)
def predict_integrated(request: IntegratedPredictionRequest) -> IntegratedPredictionResponse:
    global integration_service
    if integration_service is None:
        try:
            integration_service = IntegrationService(data_dir=None)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Failed to load integration service or model artifact: {e}")

    try:
        max_distance = 50.0
        # Get gauge metadata first to determine coverage
        gauge_res = integration_service.gauge_service.get_nearest_gauge(
            request.latitude, request.longitude, max_dist_km=max_distance
        )
        
        from app.schemas.prediction import CoverageStatusResponse
        
        ref_gauge_id = gauge_res.reference_gauge.gauge_id if gauge_res.reference_gauge else None
        dist_km = round(gauge_res.distance_km, 2) if gauge_res.distance_km is not None else None

        if not gauge_res.within_model_coverage:
            # Model Unsupported flow
            return IntegratedPredictionResponse(
                prediction_available=False,
                coverage_status="MODEL_UNSUPPORTED",
                nearest_gauge=ref_gauge_id,
                gauge_distance_km=dist_km,
                maximum_supported_distance_km=max_distance,
                coverage=CoverageStatusResponse(
                    status="MODEL_UNSUPPORTED",
                    reference_gauge=ref_gauge_id,
                    distance_km=dist_km,
                    maximum_distance_km=max_distance
                ),
                message="The current INDOFLOODS model does not provide validated coverage for this location.",
                location=LocationResponse(latitude=request.latitude, longitude=request.longitude),
                target_date=request.target_date,
                prediction=None,
                risk_level=None
            )
            
        # Model Supported flow
        # Construct exact 118 raw features
        vector = integration_service.build_feature_vector(
            latitude=request.latitude,
            longitude=request.longitude,
            target_date=request.target_date,
            max_dist_km=max_distance
        )
        
        # Prepare for prediction
        df = pd.DataFrame([vector])[integration_service.num_cols + integration_service.cat_cols]
        
        # Predict using pipeline
        pred = integration_service.pipeline.predict(df)[0]
        prob = integration_service.pipeline.predict_proba(df)[0]
        
        # Determine severe flood probability
        classes = integration_service.pipeline.named_steps['model'].classes_
        if 1 in classes:
            idx = list(classes).index(1)
            failure_prob = float(prob[idx])
        else:
            failure_prob = float(prob[1]) if len(prob) > 1 else float(prob[0])
            
        risk_level = "HIGH" if failure_prob >= 0.7 else ("MEDIUM" if failure_prob >= 0.4 else "LOW")
        
        return IntegratedPredictionResponse(
            prediction_available=True,
            coverage_status="MODEL_SUPPORTED",
            nearest_gauge=ref_gauge_id,
            maximum_supported_distance_km=max_distance,
            coverage=CoverageStatusResponse(
                status="MODEL_SUPPORTED",
                reference_gauge=ref_gauge_id,
                distance_km=dist_km,
                maximum_distance_km=max_distance
            ),
            prediction=int(pred),
            risk_level=risk_level,
            failure_probability=failure_prob,
            confidence=max(float(prob[0]), float(prob[1])),
            location=LocationResponse(latitude=request.latitude, longitude=request.longitude),
            reference_gauge=ReferenceGaugeResponse(
                gauge_id=gauge_res.reference_gauge.gauge_id,
                latitude=gauge_res.reference_gauge.latitude,
                longitude=gauge_res.reference_gauge.longitude
            ),
            gauge_distance_km=dist_km,
            target_date=request.target_date,
            rainfall=RainfallResponse(
                T1d=vector['T1d'], T2d=vector['T2d'], T3d=vector['T3d'], T4d=vector['T4d'], T5d=vector['T5d'],
                T6d=vector['T6d'], T7d=vector['T7d'], T8d=vector['T8d'], T9d=vector['T9d'], T10d=vector['T10d']
            ),
            data_sources=DataSourcesResponse(
                rainfall="Open-Meteo Historical API",
                environmental="INDOFLOODS"
            ),
            model=ModelInfoResponse(
                name="INDOFLOODS flood severity model",
                raw_features=len(integration_service.expected_features),
                processed_features=integration_service.pipeline.named_steps['model'].n_features_in_
            )
        )
    except ValidationError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Prediction flow error: {error}")
