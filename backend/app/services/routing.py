from app.schemas.resources import RoadConditionResponse, ShelterResponse
from app.schemas.route import EvacuationRouteResponse
from app.services.recommendation import BAD_ROAD_STATUSES, distance_km


_DETOUR_LATITUDE = 0.012


def _point_distance(latitude: float, longitude: float, point: list[float]) -> float:
    return distance_km(latitude, longitude, point[1], point[0])


def build_demo_route(
    user_latitude: float,
    user_longitude: float,
    shelter: ShelterResponse,
    roads: list[RoadConditionResponse],
) -> EvacuationRouteResponse:
    midpoint = [(user_longitude + shelter.longitude) / 2, (user_latitude + shelter.latitude) / 2]
    route_points = [[user_longitude, user_latitude], midpoint, [shelter.longitude, shelter.latitude]]
    hazardous_roads = [road for road in roads if road.status in BAD_ROAD_STATUSES]
    avoided_roads: list[int] = []
    warnings: list[str] = []

    for road in hazardous_roads:
        if _point_distance(road.latitude, road.longitude, midpoint) < 2.0:
            avoided_roads.append(road.id)
            warnings.append(f"Avoided {road.road_name} ({road.status.lower()}).")

    if avoided_roads:
        route_points.insert(1, [midpoint[0], midpoint[1] + _DETOUR_LATITUDE])
        route_risk = "MEDIUM"
        warnings.append("Route uses a simulated safety detour; verify conditions with authorities.")
    else:
        route_risk = "LOW"

    distance = sum(_point_distance(point[1], point[0], route_points[index + 1]) for index, point in enumerate(route_points[:-1]))
    return EvacuationRouteResponse(
        shelter_id=shelter.id,
        shelter_name=shelter.name,
        geometry=route_points,
        distance_km=round(distance, 2),
        duration_minutes=max(1, round(distance / 0.45)),
        route_risk=route_risk,
        warnings=warnings,
        source="DEMO / SIMULATED ROUTING",
        avoided_road_ids=avoided_roads,
    )
