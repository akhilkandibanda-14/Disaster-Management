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
