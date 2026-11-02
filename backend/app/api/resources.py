import logging
from math import cos, radians
from typing import Optional, Union

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import is_in_hyderabad, settings
from app.database import get_db
from app.models.resources import Alert, RoadCondition
from app.schemas.resources import AlertResponse, RoadConditionResponse, RoadConditionListResponse
from app.services.demo_data import demo_alerts, demo_roads

logger = logging.getLogger(__name__)

router = APIRouter(tags=["resources"])


@router.get("/road-conditions", response_model=Union[RoadConditionListResponse, list[RoadConditionResponse]])
def road_conditions(
    response: Response,
    db: Session = Depends(get_db),
    format: Optional[str] = Query(None, description="Optional 'list' for legacy flat list array format")
) -> Union[RoadConditionListResponse, list[RoadConditionResponse]]:
    """
    Returns verified road condition observations across Hyderabad.
    Handles infrastructure/database disconnects gracefully by returning
    an explicit UNAVAILABLE data_status without leaking internal tracebacks.
    """
    if settings.demo_mode:
        roads = demo_roads()
        response.headers["X-Data-Status"] = "DEMO"
        if format == "list":
            return roads
        return RoadConditionListResponse(
            roads=roads,
            total=len(roads),
            data_status="DEMO",
            warning="[DEMO] Synthetic road blockage demonstration records."
        )

    try:
        raw_roads = list(db.scalars(select(RoadCondition).order_by(RoadCondition.last_updated.desc())).all())
        roads = [road for road in raw_roads if is_in_hyderabad(road.latitude, road.longitude)]
        response.headers["X-Data-Status"] = "AVAILABLE"
        if format == "list":
            return roads
        return RoadConditionListResponse(
            roads=roads,
            total=len(roads),
            data_status="AVAILABLE",
            warning=None
        )
    except Exception as exc:
        logger.warning("Road conditions database unavailable: %s", type(exc).__name__)
        response.headers["X-Data-Status"] = "UNAVAILABLE"
        if format == "list":
            return []
        return RoadConditionListResponse(
            roads=[],
            total=0,
            data_status="UNAVAILABLE",
            warning="Road conditions database service is currently unavailable. Live road obstruction records cannot be retrieved."
        )


@router.get("/disaster-alerts", response_model=list[AlertResponse])
def disaster_alerts(db: Session = Depends(get_db)) -> list[AlertResponse]:
    """
    Returns active official emergency flood alerts.
    Strictly filters for flood-management alerts, excluding non-flood disasters.
    """
    try:
        if settings.demo_mode:
            alerts = demo_alerts()
        else:
            alerts = list(db.scalars(select(Alert).order_by(Alert.issued_at.desc())).all())
    except Exception:
        alerts = demo_alerts() if settings.demo_mode else []

    allowed = {
        "FLOOD",
        "FLASH_FLOOD",
        "URBAN_INUNDATION",
        "WATERLOGGING",
        "RIVER_OVERFLOW",
        "FLOOD_RELATED_HEAVY_RAINFALL",
    }
    return [a for a in alerts if getattr(a, "disaster_type", "").upper() in allowed]
