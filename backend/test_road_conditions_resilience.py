import pytest
from datetime import datetime
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app
from app.config import settings
from app.database import get_db
from app.models.resources import RoadCondition
from app.schemas.assistant import AssistantQueryRequest, AssistantContext
from app.services.assistant import assistant_service

client = TestClient(app)


def test_road_conditions_healthy_db_structured():
    """Verify GET /road-conditions returns structured response with data_status AVAILABLE when DB is online."""
    mock_road = RoadCondition(
        id=1,
        road_name="NH 65 Moosarambagh Link",
        latitude=17.3850,
        longitude=78.4867,
        status="PASSABLE",
        notes="Minor surface water",
        last_updated=datetime.utcnow()
    )
    mock_db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_road]
    mock_db.scalars.return_value = mock_scalars

    def override_get_db():
        yield mock_db

    orig_demo = settings.demo_mode
    settings.demo_mode = False
    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/road-conditions")
        assert response.status_code == 200
        data = response.json()
        assert data["data_status"] == "AVAILABLE"
        assert data["total"] == 1
        assert len(data["roads"]) == 1
        assert data["roads"][0]["road_name"] == "NH 65 Moosarambagh Link"
        assert response.headers.get("x-data-status") == "AVAILABLE"
    finally:
        app.dependency_overrides.pop(get_db, None)
        settings.demo_mode = orig_demo


def test_road_conditions_healthy_db_legacy_list_format():
    """Verify GET /road-conditions?format=list returns a flat list when DB is online."""
    mock_road = RoadCondition(
        id=1,
        road_name="NH 65 Moosarambagh Link",
        latitude=17.3850,
        longitude=78.4867,
        status="PASSABLE",
        notes="Minor surface water",
        last_updated=datetime.utcnow()
    )
    mock_db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_road]
    mock_db.scalars.return_value = mock_scalars

    def override_get_db():
        yield mock_db

    orig_demo = settings.demo_mode
    settings.demo_mode = False
    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/road-conditions?format=list")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["road_name"] == "NH 65 Moosarambagh Link"
        assert response.headers.get("x-data-status") == "AVAILABLE"
    finally:
        app.dependency_overrides.pop(get_db, None)
        settings.demo_mode = orig_demo


def test_road_conditions_db_failure_structured_resilience():
    """
    Verify that when the database suffers an infrastructure/connection failure,
    the endpoint does NOT crash or silently return unflagged empty data.
    Instead, it returns data_status='UNAVAILABLE' with header and sanitized warning.
    """
    mock_db = MagicMock()
    mock_db.scalars.side_effect = OperationalError("connection refused", params=None, orig=Exception("could not connect to server"))

    def override_get_db():
        yield mock_db

    orig_demo = settings.demo_mode
    settings.demo_mode = False
    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/road-conditions")
        assert response.status_code == 200
        data = response.json()
        assert data["data_status"] == "UNAVAILABLE"
        assert data["roads"] == []
        assert data["total"] == 0
        assert "warning" in data
        assert "unavailable" in data["warning"].lower()
        # Ensure no internal SQL/connection tracebacks or credentials are leaked
        assert "could not connect" not in data["warning"].lower()
        assert "connection refused" not in data["warning"].lower()
        assert response.headers.get("x-data-status") == "UNAVAILABLE"
    finally:
        app.dependency_overrides.pop(get_db, None)
        settings.demo_mode = orig_demo


def test_road_conditions_db_failure_legacy_list_format():
    """Verify legacy list format with failing DB returns [] and header UNAVAILABLE."""
    mock_db = MagicMock()
    mock_db.scalars.side_effect = OperationalError("connection refused", params=None, orig=Exception("could not connect to server"))

    def override_get_db():
        yield mock_db

    orig_demo = settings.demo_mode
    settings.demo_mode = False
    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/road-conditions?format=list")
        assert response.status_code == 200
        data = response.json()
        assert data == []
        assert response.headers.get("x-data-status") == "UNAVAILABLE"
    finally:
        app.dependency_overrides.pop(get_db, None)
        settings.demo_mode = orig_demo


def test_road_conditions_demo_mode():
    """Verify demo mode returns DEMO status and header."""
    orig_demo = settings.demo_mode
    settings.demo_mode = True
    try:
        response = client.get("/road-conditions")
        assert response.status_code == 200
        data = response.json()
        assert data["data_status"] == "DEMO"
        assert response.headers.get("x-data-status") == "DEMO"
        assert len(data["roads"]) > 0
    finally:
        settings.demo_mode = orig_demo


def test_assistant_coverage_explanation_en():
    """Verify assistant explains outside coverage and never claims flood-free or low-risk in English."""
    req = AssistantQueryRequest(
        message="Why is my location model unsupported coverage?",
        language="en",
        context=AssistantContext(latitude=17.385, longitude=78.4867, language="en")
    )
    res = assistant_service.process_query(req)
    assert res is not None
    reply = res.reply
    assert "outside the model's supported coverage" in reply
    assert "not claim or imply that the location is flood-free or low risk" in reply
    assert "MODEL_UNSUPPORTED" in reply


def test_assistant_coverage_explanation_te():
    """Verify assistant explains outside coverage and never claims flood-free in Telugu."""
    req = AssistantQueryRequest(
        message="ఈ లొకేషన్ కవరేజ్ ఎందుకు సపోర్ట్ లేదు?",
        language="te",
        context=AssistantContext(latitude=17.385, longitude=78.4867, language="te")
    )
    res = assistant_service.process_query(req)
    assert res is not None
    reply = res.reply
    assert "గేజ్ పరిధికి వెలుపల" in reply
    assert "వరద-రహితం లేదా తక్కువ ప్రమాదం అని కాదు" in reply


def test_assistant_coverage_explanation_hi():
    """Verify assistant explains outside coverage and never claims flood-free in Hindi."""
    req = AssistantQueryRequest(
        message="यह स्थान कवरेज से बाहर क्यों है?",
        language="hi",
        context=AssistantContext(latitude=17.385, longitude=78.4867, language="hi")
    )
    res = assistant_service.process_query(req)
    assert res is not None
    reply = res.reply
    assert "कवरेज से बाहर" in reply
    assert "बाढ़-मुक्त या कम जोखिम वाला है" in reply
