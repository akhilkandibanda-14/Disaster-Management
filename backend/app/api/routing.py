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

from app.services.emergency_facility import get_emergency_facility_service
from app.services.hazard import HazardService

router = APIRouter(tags=["routing"])
_hazard_service = None

def get_hazard_service() -> HazardService:
    global _hazard_service
    if _hazard_service is None:
        _hazard_service = HazardService()
    return _hazard_service

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
        if request.facility_id:
            shelter = get_emergency_facility_service().get_facility_by_id(request.facility_id)
    elif request.facility_id:
        facility = get_emergency_facility_service().get_facility_by_id(request.facility_id)
        if facility is None:
            raise HTTPException(status_code=404, detail=f"Emergency facility '{request.facility_id}' was not found.")
        dest_lat = facility.latitude
        dest_lon = facility.longitude
        shelter = facility
    elif request.shelter_id is not None:
        shelter = next((item for item in shelters if item.id == request.shelter_id), None)
        if shelter is None:
            shelter = get_emergency_facility_service().get_facility_by_id(str(request.shelter_id))
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

    if shelter is not None:
        # Check standard ShelterResponse fields
        if hasattr(shelter, 'available_capacity') and hasattr(shelter, 'risk_level') and hasattr(shelter, 'status'):
            if shelter.status != "OPEN" or (shelter.available_capacity is not None and shelter.available_capacity <= 0) or shelter.risk_level == "HIGH":
                raise HTTPException(status_code=409, detail="The requested shelter is not currently a safe destination.")
        # Check EmergencyFacility operational status
        elif hasattr(shelter, 'operational_status'):
            if getattr(shelter, 'operational_status', None) in ("CLOSED", "FLOODED", "UNSAFE"):
                raise HTTPException(status_code=409, detail=f"The requested destination '{getattr(shelter, 'name', 'Facility')}' is {shelter.operational_status} and cannot serve as an evacuation refuge.")

    # Location hazard intersection evaluation
    hazard_svc = get_hazard_service()
    origin_hazard = hazard_svc.check_location(
        request.origin.latitude, request.origin.longitude, include_demo=settings.demo_mode
    )
    dest_hazard = hazard_svc.check_location(
        dest_lat, dest_lon, include_demo=settings.demo_mode
    )

    # Active flood hazards evaluated with full polygon and point geometries
    active_hazards = hazard_svc.get_hazards(include_demo=settings.demo_mode, include_authoritative=True)

    route_res = build_graph_route(
        request.origin.latitude, 
        request.origin.longitude, 
        dest_lat, 
        dest_lon, 
        shelter,
        road_conditions=roads,
        hazards=active_hazards,
        compute_alternatives=request.compute_alternatives
    )

    # Attach contextual hazard intersection warnings
    if origin_hazard.is_in_hazard_zone:
        route_res.warnings.insert(
            0,
            f"Origin intersects active flood hazard zone ({origin_hazard.highest_severity} severity). Immediate evacuation required."
        )
    if dest_hazard.is_in_hazard_zone:
        route_res.warnings.append(
            f"Destination intersects documented flood hazard area ({dest_hazard.highest_severity} severity). Exercise extreme caution; local inundation may impede access."
        )

    return route_res


