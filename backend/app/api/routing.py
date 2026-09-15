from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.resources import RoadCondition, Shelter
from app.schemas.route import EvacuationRouteRequest, EvacuationRouteResponse
from app.services.demo_data import demo_roads, demo_shelters
from app.services.recommendation import recommend_shelter
from app.services.routing import build_demo_route

router = APIRouter(tags=["routing"])


@router.post("/evacuation-route", response_model=EvacuationRouteResponse)
def evacuation_route(request: EvacuationRouteRequest, db: Session = Depends(get_db)) -> EvacuationRouteResponse:
    shelters = demo_shelters() if settings.demo_mode else list(db.scalars(select(Shelter)).all())
    roads = demo_roads() if settings.demo_mode else list(db.scalars(select(RoadCondition)).all())

    if request.shelter_id is None:
        recommendation = recommend_shelter(request.user_latitude, request.user_longitude, shelters, roads).recommendation
        if recommendation is None:
            raise HTTPException(status_code=404, detail="No safe reachable shelter is currently available.")
        shelter = recommendation.shelter
    else:
        shelter = next((item for item in shelters if item.id == request.shelter_id), None)
        if shelter is None:
            raise HTTPException(status_code=404, detail="Shelter was not found.")
        if shelter.status != "OPEN" or shelter.available_capacity <= 0 or shelter.risk_level == "HIGH":
            raise HTTPException(status_code=409, detail="The requested shelter is not currently a safe destination.")

    return build_demo_route(request.user_latitude, request.user_longitude, shelter, roads)
