from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt

from app.schemas.recommendation import RecommendationResponse, SafetyBreakdown, ShelterRecommendation
from app.schemas.resources import RoadConditionResponse, ShelterResponse

BAD_ROAD_STATUSES = {"BLOCKED", "FLOODED", "DANGEROUS"}
ACCESSIBILITY_SCORES = {"FULL": 100.0, "STANDARD": 70.0, "LIMITED": 35.0}


def distance_km(latitude_one: float, longitude_one: float, latitude_two: float, longitude_two: float) -> float:
    earth_radius_km = 6371.0
    latitude_delta = radians(latitude_two - latitude_one)
    longitude_delta = radians(longitude_two - longitude_one)
    value = sin(latitude_delta / 2) ** 2 + cos(radians(latitude_one)) * cos(radians(latitude_two)) * sin(longitude_delta / 2) ** 2
    return earth_radius_km * 2 * asin(sqrt(value))


def _road_safety(user_latitude: float, user_longitude: float, shelter: ShelterResponse, roads: list[RoadConditionResponse]) -> float:
    if not roads:
        return 85.0
    route_hazard_distance = min(
        (distance_km(user_latitude, user_longitude, road.latitude, road.longitude) for road in roads if road.status in BAD_ROAD_STATUSES),
        default=10.0,
    )
    if route_hazard_distance < 1.0:
        return 35.0
    if route_hazard_distance < 2.5:
        return 60.0
    return 95.0


def _make_recommendation(user_latitude: float, user_longitude: float, shelter: ShelterResponse, roads: list[RoadConditionResponse]) -> ShelterRecommendation:
    distance = distance_km(user_latitude, user_longitude, shelter.latitude, shelter.longitude)
    disaster_safety = {"LOW": 100.0, "MEDIUM": 55.0, "HIGH": 0.0}.get(shelter.risk_level, 25.0)
    road_safety = _road_safety(user_latitude, user_longitude, shelter, roads)
    availability = min(100.0, (shelter.available_capacity / max(1, shelter.capacity)) * 100)
    accessibility = ACCESSIBILITY_SCORES.get(shelter.accessibility, 50.0)
    distance_score = max(0.0, 100.0 - distance * 10)
    breakdown = SafetyBreakdown(disaster_safety=disaster_safety, road_safety=road_safety, availability=availability, accessibility=accessibility, distance=distance_score)
    score = round(0.40 * disaster_safety + 0.25 * road_safety + 0.15 * availability + 0.10 * accessibility + 0.10 * distance_score, 2)
    return ShelterRecommendation(
        shelter=shelter,
        safety_score=score,
        distance_km=round(distance, 2),
        estimated_travel_minutes=max(1, round(distance / 0.45)),
        breakdown=breakdown,
        reason=f"{shelter.risk_level} disaster risk, {shelter.available_capacity} spaces available, and a {round(road_safety)}% road-safety score.",
        source="DEMO / SIMULATED DATA",
    )


def recommend_shelter(user_latitude: float, user_longitude: float, shelters: list[ShelterResponse], roads: list[RoadConditionResponse]) -> RecommendationResponse:
    eligible = [shelter for shelter in shelters if shelter.status == "OPEN" and shelter.available_capacity > 0 and shelter.risk_level != "HIGH"]
    scored = sorted((_make_recommendation(user_latitude, user_longitude, shelter, roads) for shelter in eligible), key=lambda item: item.safety_score, reverse=True)
    return RecommendationResponse(
        user_latitude=user_latitude,
        user_longitude=user_longitude,
        recommendation=scored[0] if scored else None,
        alternatives=scored[1:],
        generated_at=datetime.now(timezone.utc),
        source="DEMO / SIMULATED DATA",
        warning=None if scored else "No open, available, low-risk shelter is currently known.",
    )
