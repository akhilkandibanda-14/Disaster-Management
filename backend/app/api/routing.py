from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import is_in_hyderabad, settings
from app.database import get_db
from app.models.resources import Shelter, RoadCondition
from app.schemas.route import EvacuationRouteRequest, EvacuationRouteResponse
from app.services.demo_data import demo_shelters, demo_roads
from app.services.recommendation import recommend_shelter
from app.services.routing import build_graph_route

router = APIRouter(tags=["routing"])

@router.post("/evacuation-route", response_model=EvacuationRouteResponse)
def evacuation_route(request: EvacuationRouteRequest, db: Session = Depends(get_db)) -> EvacuationRouteResponse:
    if not is_in_hyderabad(request.origin.latitude, request.origin.longitude):
        raise HTTPException(status_code=422, detail="This service currently supports Hyderabad coordinates only.")
    
    shelters = demo_shelters() if settings.demo_mode else list(db.scalars(select(Shelter)).all())
    roads = demo_roads() if settings.demo_mode else list(db.scalars(select(RoadCondition)).all())
    
    shelter = None
    dest_lat = None
    dest_lon = None
    
    if request.destination:
        dest_lat = request.destination.latitude
        dest_lon = request.destination.longitude
    elif request.shelter_id is not None:
        shelter = next((item for item in shelters if item.id == request.shelter_id), None)
        if shelter is None:
            raise HTTPException(status_code=404, detail="Shelter was not found.")
        dest_lat = shelter.latitude
        dest_lon = shelter.longitude
    else:
        # recommend a shelter if no destination is provided
        recommendation = recommend_shelter(request.origin.latitude, request.origin.longitude, shelters, roads).recommendation
        if recommendation is None:
            raise HTTPException(status_code=404, detail="No safe reachable shelter is currently available.")
        shelter = recommendation.shelter
        dest_lat = shelter.latitude
        dest_lon = shelter.longitude

    if shelter is not None and (shelter.status != "OPEN" or shelter.available_capacity <= 0 or shelter.risk_level == "HIGH"):
        # Note: this logic remains to preserve API functionality, but routing won't claim safety.
        raise HTTPException(status_code=409, detail="The requested shelter is not currently a safe destination.")

    return build_graph_route(
        request.origin.latitude, 
        request.origin.longitude, 
        dest_lat, 
        dest_lon, 
        shelter
    )
