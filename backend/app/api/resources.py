from math import cos, radians

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import is_in_hyderabad, settings
from app.database import get_db
from app.models.resources import Alert, RoadCondition, Shelter
from app.schemas.resources import AlertResponse, RoadConditionResponse, ShelterResponse
from app.schemas.recommendation import RecommendationResponse
from app.services.demo_data import demo_alerts, demo_roads, demo_shelters
from app.services.recommendation import recommend_shelter

router = APIRouter(tags=["resources"])


@router.get("/shelters", response_model=list[ShelterResponse])
def list_shelters(db: Session = Depends(get_db)) -> list[ShelterResponse]:
    if settings.demo_mode:
        return demo_shelters()
    shelters = list(db.scalars(select(Shelter).order_by(Shelter.name)).all())
    return [shelter for shelter in shelters if is_in_hyderabad(shelter.latitude, shelter.longitude)]


@router.get("/shelters/nearby", response_model=list[ShelterResponse])
def nearby_shelters(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    radius_km: float = Query(default=10, gt=0, le=100),
    db: Session = Depends(get_db),
) -> list[ShelterResponse]:
    if not is_in_hyderabad(latitude, longitude):
        raise HTTPException(status_code=422, detail="This service currently supports Hyderabad coordinates only.")
    shelters = demo_shelters() if settings.demo_mode else list(db.scalars(select(Shelter)).all())
    latitude_delta = radius_km / 111
    longitude_delta = radius_km / (111 * max(0.1, cos(radians(latitude))))
    return [shelter for shelter in shelters if abs(shelter.latitude - latitude) <= latitude_delta and abs(shelter.longitude - longitude) <= longitude_delta]


@router.get("/shelters/recommended", response_model=RecommendationResponse)
def recommended_shelter(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    if not is_in_hyderabad(latitude, longitude):
        raise HTTPException(status_code=422, detail="This service currently supports Hyderabad coordinates only.")
    shelters = demo_shelters() if settings.demo_mode else list(db.scalars(select(Shelter)).all())
    roads = demo_roads() if settings.demo_mode else list(db.scalars(select(RoadCondition)).all())
    return recommend_shelter(latitude, longitude, shelters, roads)


@router.get("/road-conditions", response_model=list[RoadConditionResponse])
def road_conditions(db: Session = Depends(get_db)) -> list[RoadConditionResponse]:
    if settings.demo_mode:
        return demo_roads()
    roads = list(db.scalars(select(RoadCondition).order_by(RoadCondition.last_updated.desc())).all())
    return [road for road in roads if is_in_hyderabad(road.latitude, road.longitude)]


@router.get("/disaster-alerts", response_model=list[AlertResponse])
def disaster_alerts(db: Session = Depends(get_db)) -> list[AlertResponse]:
    if settings.demo_mode:
        return demo_alerts()
    return list(db.scalars(select(Alert).order_by(Alert.issued_at.desc())).all())
