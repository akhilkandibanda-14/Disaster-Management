import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.incident import IncidentStatusUpdate
from app.services.incident import get_incident_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_incident_service(tmp_path):
    """
    Reset incident service state before each test and isolate persistent storage.
    Ensures that test execution NEVER writes to the git-tracked backend/data/incidents.json file.
    """
    service = get_incident_service()
    original_storage = service.storage_file
    original_incidents = dict(service.incidents)

    # Seed temporary test storage with an isolated copy
    temp_storage = tmp_path / "test_isolated_incidents.json"
    temp_storage.write_text(json.dumps(list(original_incidents.values())), encoding="utf-8")
    service.storage_file = temp_storage
    service.rate_limit_tracker.clear()

    yield

    # Restore pristine state
    service.storage_file = original_storage
    service.incidents = original_incidents
    service.rate_limit_tracker.clear()


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


def test_public_provenance_escalation_rejection_and_community_corroboration():
    """
    Verifies that public web clients CANNOT claim official municipal verification (HTTP 403),
    while explicitly permitted community corroboration is accepted (HTTP 200) without
    converting unverified reports into severe hard-blocks.
    """
    service = get_incident_service()

    # 1. Submit citizen report
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

    # 2. Public attempt to claim official municipal verification MUST be rejected with HTTP 403
    unauthorized_resp = client.patch(
        f"/incidents/{inc_id}/status",
        json={"status": "VERIFIED_MUNICIPAL", "reviewer_notes": "Unauthorized claim of official verification."}
    )
    assert unauthorized_resp.status_code == 403
    assert "unauthorized provenance escalation" in unauthorized_resp.json()["detail"].lower()

    # 3. Public attempt to claim official rejection MUST also be rejected with HTTP 403
    unauthorized_reject = client.patch(
        f"/incidents/{inc_id}/status",
        json={"status": "REJECTED", "reviewer_notes": "Unauthorized claim of official rejection."}
    )
    assert unauthorized_reject.status_code == 403

    # 4. Public attempt to directly close incident to RESOLVED MUST be rejected with HTTP 403
    unauthorized_resolve = client.patch(
        f"/incidents/{inc_id}/status",
        json={"status": "RESOLVED", "reviewer_notes": "Attempting anonymous public closure."}
    )
    assert unauthorized_resolve.status_code == 403
    assert "unauthorized" in unauthorized_resolve.json()["detail"].lower()

    # 5. Public community corroboration MUST succeed with HTTP 200
    corroborate_resp = client.patch(
        f"/incidents/{inc_id}/status",
        json={"status": "COMMUNITY_CORROBORATED", "verification_note": "Corroborated by 3 local residents on site."}
    )
    assert corroborate_resp.status_code == 200
    corroborated_data = corroborate_resp.json()
    assert corroborated_data["verification_status"] == "COMMUNITY_CORROBORATED"
    # Crucial safety check: data_status must remain unverified citizen report, NOT municipal
    assert corroborated_data["data_status"] == "PUBLIC_UNVERIFIED_REPORT"
    assert corroborated_data["report_count"] >= 2

    # 6. Dedicated POST /incidents/{id}/corroborate endpoint succeeds with HTTP 200
    ded_corr = client.post(f"/incidents/{inc_id}/corroborate")
    assert ded_corr.status_code == 200
    assert ded_corr.json()["report_count"] >= 3

    # 7. Public resolution observation succeeds with HTTP 200 without closing incident
    receding_resp = client.patch(
        f"/incidents/{inc_id}/status",
        json={"status": "COMMUNITY_RESOLUTION_OBSERVED", "verification_note": "Observed water receding in lane."}
    )
    assert receding_resp.status_code == 200
    receding_data = receding_resp.json()
    assert receding_data["verification_status"] == "COMMUNITY_RESOLUTION_OBSERVED"
    # Verification safety: data_status is NOT RESOLVED_INCIDENT, still PUBLIC_UNVERIFIED_REPORT
    assert receding_data["data_status"] == "PUBLIC_UNVERIFIED_REPORT"

    # 8. Dedicated POST /incidents/{id}/resolution-observation endpoint succeeds with HTTP 200
    ded_rec = client.post(f"/incidents/{inc_id}/resolution-observation")
    assert ded_rec.status_code == 200
    assert ded_rec.json()["verification_status"] == "COMMUNITY_RESOLUTION_OBSERVED"
    assert ded_rec.json()["data_status"] == "PUBLIC_UNVERIFIED_REPORT"

    # 9. Authoritative institutional verification succeeds via institutional path
    inst_update = IncidentStatusUpdate(
        verification_status="VERIFIED_MUNICIPAL",
        verification_note="Verified on-site by DRF Field Unit 4.",
    )
    inst_result = service.update_status(inc_id, inst_update, is_institutional=True)
    assert inst_result is not None
    assert inst_result.verification_status == "VERIFIED_MUNICIPAL"
    assert inst_result.data_status == "VERIFIED_MUNICIPAL"
    assert inst_result.verified_at is not None

    # 10. Authoritative institutional resolution succeeds via institutional path
    resolve_update = IncidentStatusUpdate(
        verification_status="RESOLVED",
        verification_note="Officially drained and cleared by municipal emergency team.",
    )
    resolve_result = service.update_status(inc_id, resolve_update, is_institutional=True)
    assert resolve_result is not None
    assert resolve_result.verification_status == "RESOLVED"
    assert resolve_result.data_status == "RESOLVED_INCIDENT"


def test_public_callers_strictly_forbidden_from_closing_or_verifying_incidents():
    """
    Explicit regression test proving that anonymous public callers CANNOT:
    - Assert VERIFIED_MUNICIPAL (HTTP 403)
    - Assert RESOLVED (HTTP 403)
    - Assert REJECTED (HTTP 403)
    And can only perform community corroboration and resolution observations.
    """
    create_resp = client.post("/incidents", json={
        "latitude": 17.3850,
        "longitude": 78.4867,
        "category": "WATERLOGGING",
        "severity": "MODERATE",
        "description": "Flooding on roadway under flyover.",
    })
    assert create_resp.status_code == 201
    inc_id = create_resp.json()["id"]

    for forbidden_status in ["RESOLVED", "VERIFIED_MUNICIPAL", "REJECTED"]:
        resp = client.patch(f"/incidents/{inc_id}/status", json={"status": forbidden_status})
        assert resp.status_code == 403, f"Expected 403 for public asserting {forbidden_status}, got {resp.status_code}"
        assert "unauthorized" in resp.json()["detail"].lower()

    # Permitted public actions:
    corr_resp = client.patch(f"/incidents/{inc_id}/status", json={"status": "COMMUNITY_CORROBORATED"})
    assert corr_resp.status_code == 200

    rec_resp = client.patch(f"/incidents/{inc_id}/status", json={"status": "COMMUNITY_RESOLUTION_OBSERVED"})
    assert rec_resp.status_code == 200
    assert rec_resp.json()["data_status"] == "PUBLIC_UNVERIFIED_REPORT"


