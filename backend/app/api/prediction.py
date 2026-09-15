from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.schemas.prediction import PredictionRequest, PredictionResponse
from app.services.prediction import predict

router = APIRouter(tags=["prediction"])


@router.post("/predict", response_model=PredictionResponse)
def predict_flood_risk(request: PredictionRequest) -> PredictionResponse:
    features = request.model_dump()
    try:
        probability, risk_level = predict(features)
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=503, detail=f"Flood model is unavailable: {error}") from error

    return PredictionResponse(
        **request.model_dump(),
        flood_probability=round(probability, 6),
        risk_level=risk_level,
        source="PREDICTED / TRAINED MODEL",
        timestamp=datetime.now(timezone.utc),
    )
