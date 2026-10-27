import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.incident import get_incident_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_incident_service():
    """Reset incident service state before each test."""
    service = get_incident_service()
    service.rate_limit_tracker.clear()
    yield


def test_submit_valid_incident():
    payload = {
        "latitude": 17.4350,
        "longitude": 78.4480,
        "category": "WATERLOGGING",
        "severity": "HIGH",
        "description": "Severe road waterlogging near Punjagutta flyover, 2 feet deep water obstructing cars.",
        "location_name": "Punjagutta Junction",
        "reporter_contact": "citizen@example.com"
    }
    response = client.post("/incidents", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["category"] == "WATERLOGGING"
    assert data["severity"] == "HIGH"
    assert data["status"] == "PENDING_REVIEW"
    # Reporter privacy: email must be redacted
    assert "citizen@example.com" not in data["reporter_contact"]
    assert "[REDACTED_EMAIL]" in data["reporter_contact"]
    assert data["latitude"] == 17.4350
    assert data["longitude"] == 78.4480


def test_submit_incident_outside_hyderabad_rejected():
    payload = {
        "latitude": 12.9716,  # Bengaluru
        "longitude": 77.5946,
        "category": "WATERLOGGING",
        "severity": "MODERATE",
        "description": "Road waterlogged outside operational boundaries of Hyderabad SafeMap.",
    }
    response = client.post("/incidents", json=payload)
    assert response.status_code == 422
    assert "Hyderabad" in response.json()["detail"]


def test_submit_non_flood_category_rejected():
    payload = {
        "latitude": 17.4350,
        "longitude": 78.4480,
        "category": "EARTHQUAKE",  # Non-flood category
        "severity": "HIGH",
        "description": "Seismic tremor reported near central city.",
    }
    response = client.post("/incidents", json=payload)
    assert response.status_code == 422


def test_privacy_redaction_phone_and_email():
    payload = {
        "latitude": 17.3950,
        "longitude": 78.4800,
        "category": "DRAIN_OVERFLOW",
        "severity": "MODERATE",
        "description": "Nala overflowing behind Chaderghat bridge, please call +91-9876543210 urgently.",
        "reporter_contact": "+91 9876543210 or resident.aid@gmail.com"
    }
    response = client.post("/incidents", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "9876543210" not in data["description"]
    assert "[REDACTED_PHONE]" in data["description"]
    assert "resident.aid@gmail.com" not in data["reporter_contact"]
    assert "[REDACTED_EMAIL]" in data["reporter_contact"]


def test_duplicate_incident_detection():
    # Submit first report
    p1 = {
        "latitude": 17.4200,
        "longitude": 78.4500,
        "category": "ROAD_SUBMERGED",
        "severity": "HIGH",
        "description": "Road submerged completely near Khairatabad underpass.",
        "location_name": "Khairatabad Underpass"
    }
    r1 = client.post("/incidents", json=p1)
    assert r1.status_code == 201
    id1 = r1.json()["id"]

    # Submit second report within ~50 meters with same category
    p2 = {
        "latitude": 17.4203,
        "longitude": 78.4502,
        "category": "ROAD_SUBMERGED",
        "severity": "HIGH",
        "description": "Water overflowing into underpass, road cannot be traversed.",
        "location_name": "Khairatabad Underpass North"
    }
    r2 = client.post("/incidents", json=p2)
    assert r2.status_code == 201
    d2 = r2.json()
    assert d2["duplicate_of"] is not None


def test_rate_limiting_abuse_protection():
    service = get_incident_service()
    service.rate_limit_tracker.clear()
    
    payload = {
        "latitude": 17.3850,
        "longitude": 78.4867,
        "category": "WATERLOGGING",
        "severity": "LOW",
        "description": "Rapid submission testing for sliding window rate limiter."
    }

    # First 5 should succeed
    for _ in range(5):
        resp = client.post("/incidents", json=payload)
        assert resp.status_code == 201

    # 6th should be 429
    resp6 = client.post("/incidents", json=payload)
    assert resp6.status_code == 429
    assert "rate limit exceeded" in resp6.json()["detail"].lower()


def test_list_and_filter_incidents():
    response = client.get("/incidents")
    assert response.status_code == 200
    data = response.json()
    assert "incidents" in data
    assert "total" in data
    assert isinstance(data["incidents"], list)

    # Filter by category
    filter_resp = client.get("/incidents?category=WATERLOGGING")
    assert filter_resp.status_code == 200
    for inc in filter_resp.json()["incidents"]:
        assert inc["category"] == "WATERLOGGING"


def test_status_transition_verification_workflow():
    # Submit report
    p = {
        "latitude": 17.3616,
        "longitude": 78.4747,
        "category": "FLASH_FLOOD",
        "severity": "CRITICAL",
        "description": "Rapid water level increase in stormwater channel near Old City.",
        "location_name": "Old City Musi Channel"
    }
    create_resp = client.post("/incidents", json=p)
    assert create_resp.status_code == 201
    inc_id = create_resp.json()["id"]

    # Verify report status via DRF Municipal Review
    patch_resp = client.patch(
        f"/incidents/{inc_id}/status",
        json={"status": "VERIFIED_MUNICIPAL", "reviewer_notes": "Verified on-site by DRF Field Unit 4."}
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["status"] == "VERIFIED_MUNICIPAL"
    assert updated["reviewer_notes"] == "Verified on-site by DRF Field Unit 4."
    assert updated["verified_at"] is not None
