from datetime import datetime, timezone

from app.schemas.resources import AlertResponse, RoadConditionResponse, ShelterResponse


def demo_shelters() -> list[ShelterResponse]:
    timestamp = datetime.now(timezone.utc)
    return [
        ShelterResponse(id=1, name="Community Relief Center", latitude=17.401, longitude=78.472, capacity=500, available_capacity=320, status="OPEN", accessibility="FULL", contact="112", risk_level="LOW", last_updated=timestamp),
        ShelterResponse(id=2, name="Riverbank School Shelter", latitude=17.377, longitude=78.503, capacity=250, available_capacity=0, status="FULL", accessibility="STANDARD", contact="108", risk_level="MEDIUM", last_updated=timestamp),
        ShelterResponse(id=3, name="East Ward Hall", latitude=17.362, longitude=78.486, capacity=180, available_capacity=90, status="OPEN", accessibility="STANDARD", contact="100", risk_level="HIGH", last_updated=timestamp),
    ]


def demo_roads() -> list[RoadConditionResponse]:
    timestamp = datetime.now(timezone.utc)
    return [
        RoadConditionResponse(id=1, road_name="Musi Riverside Road", status="FLOODED", latitude=17.385, longitude=78.486, notes="Avoid during current flood simulation.", last_updated=timestamp),
        RoadConditionResponse(id=2, road_name="Central Relief Corridor", status="OPEN", latitude=17.397, longitude=78.478, notes="Preferred response corridor.", last_updated=timestamp),
    ]


def demo_alerts() -> list[AlertResponse]:
    return [AlertResponse(id=1, disaster_type="FLOOD", severity="HIGH", affected_area="Musi river corridor", source="DEMO / SIMULATED DATA", description="Water level simulation indicates elevated flood risk. Follow official instructions.", issued_at=datetime.now(timezone.utc))]
