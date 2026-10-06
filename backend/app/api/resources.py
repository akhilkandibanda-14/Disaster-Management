from math import cos, radians

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import is_in_hyderabad, settings
from app.database import get_db
from app.models.resources import Alert, RoadCondition
from app.schemas.resources import AlertResponse, RoadConditionResponse
from app.services.demo_data import demo_alerts, demo_roads

router = APIRouter(tags=["resources"])


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
