from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.config import is_in_hyderabad
from app.schemas.prediction import PredictionRequest, PredictionResponse
from app.services.prediction import predict

router = APIRouter(tags=["prediction"])


@router.post("/predict", response_model=PredictionResponse)
def predict_flood_risk(request: PredictionRequest) -> PredictionResponse:
    features = request.model_dump()
    try:
        result = predict(features)
        return PredictionResponse(**result)
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail="Model file not found. Please train and save the model.") from error
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=400, detail=f"Invalid input or model error: {error}") from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Prediction error: {error}") from error
