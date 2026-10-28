import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_assistant_status_endpoint():
    """Verify /assistant/status exposes active provider, supported languages, and safety invariants."""
    response = client.get("/assistant/status")
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "ready"
    assert data["service"] == "safemap-ai-safety-assistant"
    assert "SAFETY_DECISION_ENGINE_FALLBACK" in data["active_provider"] or data["active_provider"] in ["GEMINI", "OPENAI"]
    assert set(data["supported_languages"]) == {"en", "te", "hi"}
    assert data["safety_invariants"]["emergency_priority"] is True
    assert data["safety_invariants"]["no_fabricated_data"] is True
    assert data["safety_invariants"]["no_automatic_sos"] is True
    assert data["safety_invariants"]["honest_no_safe_route"] is True


def test_immediate_danger_questions():
    """Verify immediate danger questions prioritize life safety and provide 112 / GHMC contacts first."""
    queries = [
        "I am near the Musi River and water is rising. What should I do?",
        "What should I do if floodwater enters my house?",
        "Water level is rising rapidly and I am trapped on the ground floor!"
    ]
    for q in queries:
        response = client.post("/assistant/query", json={"message": q})
        assert response.status_code == 200
        data = response.json()
        
        assert data["is_emergency"] is True
        reply = data["reply"]
        assert "112" in reply
        assert "040-21111111" in reply
        assert any(term in reply.lower() for term in ["never walk", "moving water", "don't drown", "turn off", "circuit breaker", "utilities"])
        assert any("112" in action for action in data["suggested_actions"])


def test_musi_river_inundation_protocol():
    """Verify Musi River queries explain upstream reservoir releases and causeway hazards."""
    response = client.post("/assistant/query", json={"message": "What is the danger near Musi River Chaderghat bridge?"})
    assert response.status_code == 200
    data = response.json()
    
    reply = data["reply"]
    assert any(term in reply.lower() for term in ["musi", "causeway", "chaderghat", "reservoir", "osman sagar", "himayat sagar"])
    assert data["follow_up_question"] is not None


def test_mapped_flood_prone_zone_with_and_without_location():
    """Verify zone inquiry uses real hazard service when location is present, or asks follow-up when missing."""
    # 1. With location inside Musi River corridor (HYD-FZ-001)
    loc_payload = {
        "message": "Is this location in a mapped flood-prone zone?",
        "context": {
            "location": {"latitude": 17.3820, "longitude": 78.4910}
        }
    }
    res1 = client.post("/assistant/query", json=loc_payload)
    assert res1.status_code == 200
    d1 = res1.json()
    assert "HYD-FZ-001" in d1["reply"] or "Musi River" in d1["reply"]
    assert "HIGH" in d1["reply"]
    assert "municipal" in d1["reply"].lower()

    # 2. Without location
    res2 = client.post("/assistant/query", json={"message": "Is this location in a mapped flood-prone zone?"})
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2["follow_up_question"] is not None
    assert "map" in d2["follow_up_question"].lower() or "coordinates" in d2["follow_up_question"].lower()


def test_no_safe_route_honesty():
    """Verify NO_SAFE_ROUTE warns against travel, directs to vertical shelter, and does not fabricate a route."""
    response = client.post("/assistant/query", json={"message": "The route says NO_SAFE_ROUTE. What should I do?"})
    assert response.status_code == 200
    data = response.json()
    
    assert data["is_emergency"] is True
    reply = data["reply"]
    assert "NO_SAFE_ROUTE" in reply
    assert any(term in reply.lower() for term in ["do not attempt road travel", "severed", "vertical shelter", "highest floor", "rooftop"])
    assert "040-21111111" in reply or "112" in reply


def test_model_unsupported_and_insufficient_local_data():
    """Verify MODEL_UNSUPPORTED explains the 50km safeguard and 71.8km distance to nearest gauge."""
    response = client.post("/assistant/query", json={"message": "What does MODEL_UNSUPPORTED mean?"})
    assert response.status_code == 200
    data = response.json()
    
    reply = data["reply"]
    assert "50.0 km" in reply or "50 km" in reply or "50km" in reply
    assert "71.8 km" in reply or "gauge-916" in reply or "Manjra" in reply
    assert "INDOFLOODS" in reply
    assert "fabrication" in reply.lower() or "suppressed" in reply.lower()


def test_shelters_and_unverified_data():
    """Verify shelter inquiries disclose PUBLIC_UNVERIFIED truth-in-facilities status."""
    response = client.post("/assistant/query", json={"message": "Where is the nearest listed shelter?"})
    assert response.status_code == 200
    data = response.json()
    
    reply = data["reply"]
    assert "PUBLIC_UNVERIFIED" in reply or "municipal survey" in reply.lower() or "unverified" in reply.lower()
    assert "Khairatabad" in reply or "shelter" in reply.lower()


def test_blocked_road_reporting_not_automated():
    """Verify reporting questions explain Report Incident form and confirm chat does not submit reports."""
    response = client.post("/assistant/query", json={"message": "How do I report a blocked road?"})
    assert response.status_code == 200
    data = response.json()
    
    reply = data["reply"]
    assert "Report Incident" in reply
    assert "not automatically" in reply.lower() or "not automated" in reply.lower()
    assert "040-21111111" in reply


def test_telugu_and_hindi_multilingual():
    """Verify assistant auto-detects Telugu and Hindi and responds in the correct script."""
    # 1. Telugu Query
    te_res = client.post("/assistant/query", json={"message": "మూసీ నది వద్ద నీరు పెరుగుతుంది, నేను ఏమి చేయాలి?"})
    assert te_res.status_code == 200
    te_data = te_res.json()
    assert te_data["language"] == "te"
    assert te_data["is_emergency"] is True
    assert "112" in te_data["reply"]
    assert "040-21111111" in te_data["reply"]
    # Verify Telugu script in response
    assert any("\u0c00" <= c <= "\u0c7f" for c in te_data["reply"])

    # 2. Hindi Query
    hi_res = client.post("/assistant/query", json={"message": "मेरे घर में बाढ़ का पानी घुस गया है, मुझे क्या करना चाहिए?"})
    assert hi_res.status_code == 200
    hi_data = hi_res.json()
    assert hi_data["language"] == "hi"
    assert hi_data["is_emergency"] is True
    assert "112" in hi_data["reply"]
    assert "040-21111111" in hi_data["reply"]
    # Verify Devanagari script in response
    assert any("\u0900" <= c <= "\u097f" for c in hi_data["reply"])


def test_simulated_demo_data_distinction():
    """Verify assistant marks simulated demo scenario when is_demo_mode is active."""
    response = client.post("/assistant/query", json={
        "message": "Give me a flood status update.",
        "context": {
            "is_demo_mode": True
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert "DEMO" in data["reply"] or "DEMO" in data["provider"] or "SIMULATION" in data["reply"]


def test_empty_and_malformed_queries():
    """Verify empty or whitespace-only inputs are rejected with 422 Unprocessable Entity."""
    # Empty string
    r1 = client.post("/assistant/query", json={"message": ""})
    assert r1.status_code == 422

    # Whitespace only
    r2 = client.post("/assistant/query", json={"message": "   "})
    assert r2.status_code == 422

    # Missing message
    r3 = client.post("/assistant/query", json={})
    assert r3.status_code == 422


def test_protection_against_accidental_sos_or_incident():
    """Verify querying the assistant does not submit an incident or create an SOS record."""
    incidents_before = client.get("/incidents").json().get("incidents", [])
    
    # Query assistant with emergency and incident phrasing
    client.post("/assistant/query", json={"message": "I want to report an emergency SOS at Musi River!"})
    client.post("/assistant/query", json={"message": "A road is submerged near Begumpet, report this road!"})
    
    incidents_after = client.get("/incidents").json().get("incidents", [])
    assert len(incidents_before) == len(incidents_after), "Assistant queries MUST NOT alter public incidents database"
