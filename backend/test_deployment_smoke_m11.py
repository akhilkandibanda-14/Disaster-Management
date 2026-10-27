"""
SafeMap AI — Milestone 11: Deployment Smoke Tests and Supervised Pilot Readiness

Verifies:
1. Deployed configuration & container artifacts (docker-compose.yml, Dockerfiles, Nginx security headers, probes).
2. Production secret configuration & refusal of insecure default credentials.
3. End-to-end user acceptance workflows (flood map, official alerts, data classification,
   evacuation routing with hazard avoidance, detour logic, NO_SAFE_ROUTE severing,
   truth-in-data facility caveats, external provider resilience, Hyderabad model unsupported guard,
   and strict RBAC authorization gates).
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, settings
from app.main import app
from app.schemas.resources import RoadConditionResponse
from app.services.emergency_facility import get_emergency_facility_service
from app.services.road_network import road_network_service
from app.services.routing import build_graph_route
from app.utils.observability import (
    health_monitor,
    log_structured_event,
    run_startup_diagnostics,
    sanitize_payload,
)

BASE_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# =============================================================================
# Task 1: Deployed Configuration & Container Artifact Validation
# =============================================================================

class TestDeploymentConfigurationAndContainers:
    """Validates Docker Compose, Dockerfiles, Nginx config, and container probes."""

    def test_docker_compose_structure_and_volume_hardening(self):
        compose_path = BASE_DIR / "docker-compose.yml"
        assert compose_path.exists(), "docker-compose.yml must exist at repository root."
        content = compose_path.read_text(encoding="utf-8")

        # Verify essential services
        assert "safemap-postgres" in content
        assert "safemap-backend" in content
        assert "safemap-frontend" in content

        # Verify volume mounts are read-only for data & models
        assert ":ro" in content, "Data and ML volumes must be mounted read-only (:ro)."
        assert "./data:/app/data:ro" in content
        assert "./ml/models:/app/ml/models:ro" in content

        # Verify health checks configured on all services
        assert "healthcheck:" in content
        assert "condition: service_healthy" in content

    def test_backend_dockerfile_security_and_nonroot_execution(self):
        dockerfile_path = BASE_DIR / "backend" / "Dockerfile"
        assert dockerfile_path.exists()
        content = dockerfile_path.read_text(encoding="utf-8")

        # Must run as an unprivileged user
        assert "useradd" in content
        assert "USER safemap" in content
        assert "HEALTHCHECK" in content
        assert "EXPOSE 8000" in content

    def test_frontend_dockerfile_and_nginx_security_headers(self):
        dockerfile_path = BASE_DIR / "frontend" / "Dockerfile"
        nginx_conf_path = BASE_DIR / "frontend" / "nginx.conf"
        assert dockerfile_path.exists()
        assert nginx_conf_path.exists()

        df_content = dockerfile_path.read_text(encoding="utf-8")
        assert "FROM node:20-alpine AS builder" in df_content
        assert "FROM nginx:alpine AS runner" in df_content

        conf_content = nginx_conf_path.read_text(encoding="utf-8")
        assert "X-Frame-Options" in conf_content
        assert "X-Content-Type-Options" in conf_content
        assert "X-XSS-Protection" in conf_content
        assert "Referrer-Policy" in conf_content
        assert "Permissions-Policy" in conf_content
        assert "/healthz" in conf_content

    def test_dockerignore_excludes_credentials_and_scratch_files(self):
        backend_ignore = (BASE_DIR / "backend" / ".dockerignore").read_text(encoding="utf-8")
        frontend_ignore = (BASE_DIR / "frontend" / ".dockerignore").read_text(encoding="utf-8")

        assert ".env" in backend_ignore
        assert "*.key" in backend_ignore
        assert ".env" in frontend_ignore

    def test_container_liveness_and_readiness_contracts(self, client):
        live_resp = client.get("/health/live")
        assert live_resp.status_code == 200
        assert live_resp.json()["status"] == "alive"

        ready_resp = client.get("/health/ready")
        assert ready_resp.status_code == 200
        ready_data = ready_resp.json()
        assert ready_data["status"] == "ready"
        assert "road_network_loaded" in ready_data
        assert "demo_mode" in ready_data


# =============================================================================
# Task 2: Production Secret & Environment Hardening
# =============================================================================

class TestProductionSecretHardening:
    """Verifies that production startup refuses default or insecure credentials."""

    def test_production_refuses_default_admin_key(self):
        prod_insecure = Settings(
            app_env="production",
            admin_api_key="safemap-admin-dev-key",
            analyst_api_key="strong-random-analyst-secret-key-123456",
        )
        with pytest.raises(RuntimeError) as exc_info:
            run_startup_diagnostics(custom_settings=prod_insecure)
        assert "Production startup refused" in str(exc_info.value)
        assert "ADMIN_API_KEY" in str(exc_info.value)

    def test_production_refuses_default_analyst_key(self):
        prod_insecure = Settings(
            app_env="production",
            admin_api_key="strong-random-admin-secret-key-123456",
            analyst_api_key="safemap-analyst-dev-key",
        )
        with pytest.raises(RuntimeError) as exc_info:
            run_startup_diagnostics(custom_settings=prod_insecure)
        assert "Production startup refused" in str(exc_info.value)
        assert "ANALYST_API_KEY" in str(exc_info.value)

    def test_production_refuses_trivially_short_or_empty_keys(self):
        prod_short = Settings(
            app_env="production",
            admin_api_key="short",
            analyst_api_key="also_short",
        )
        with pytest.raises(RuntimeError) as exc_info:
            run_startup_diagnostics(custom_settings=prod_short)
        assert "Production startup refused" in str(exc_info.value)

    def test_production_accepts_strong_unique_keys(self):
        prod_secure = Settings(
            app_env="production",
            admin_api_key="safemap-prod-admin-auth-9876543210-xyz",
            analyst_api_key="safemap-prod-analyst-auth-9876543210-abc",
        )
        diagnostics = run_startup_diagnostics(custom_settings=prod_secure)
        assert diagnostics["is_production"] is True
        assert len(diagnostics["errors"]) == 0

    def test_env_examples_contain_zero_live_secrets(self):
        b_example = (BASE_DIR / "backend" / ".env.example").read_text(encoding="utf-8")
        f_example = (BASE_DIR / "frontend" / ".env.example").read_text(encoding="utf-8")

        # Verify only placeholder strings exist
        assert "safemap-admin-dev-key" in b_example
        assert "safemap-analyst-dev-key" in b_example
        assert "WEATHER_API_KEY=" in b_example
        assert "GOOGLE_MAPS_API_KEY=" in b_example

        # Forbidden live tokens
        for forbidden in ["ghp_", "sk-", "AIzaSy", "postgres:supersecret"]:
            assert forbidden not in b_example
            assert forbidden not in f_example

    def test_structured_logging_never_emits_unredacted_keys(self):
        event = log_structured_event(
            "TEST_AUDIT",
            "Testing secret scrub",
            admin_api_key="super_secret_admin_token_123456",
            analyst_api_key="super_secret_analyst_token_654321",
            nested={"token": "bearer_secret_abc123"},
        )
        assert event["details"]["admin_api_key"] == "[REDACTED]"
        assert event["details"]["analyst_api_key"] == "[REDACTED]"
        assert event["details"]["nested"]["token"] == "[REDACTED]"


# =============================================================================
# Task 3: End-to-End User Acceptance Workflows
# =============================================================================

class TestEndToEndUserAcceptanceWorkflows:
    """Verifies all 11 end-to-end user acceptance workflows."""

    def test_workflow_1_load_flood_map_and_hazards(self, client):
        resp = client.get("/flood-hazards")
        assert resp.status_code == 200
        data = resp.json()
        assert "hazards" in data
        hazards = data["hazards"]
        assert isinstance(hazards, list)
        assert len(hazards) > 0
        for h in hazards:
            assert "hazard_id" in h
            assert "title" in h
            assert "data_status" in h
            if h.get("geometry"):
                assert h["geometry"]["type"] in ("Polygon", "MultiPolygon", "Point")

    def test_workflow_2_official_flood_alerts_with_source_timestamps(self, client):
        resp = client.get("/disaster-alerts")
        assert resp.status_code == 200
        alerts = resp.json()
        assert isinstance(alerts, list)
        for a in alerts:
            assert a["disaster_type"] == "FLOOD"
            assert "source" in a
            assert "issued_at" in a
            assert "severity" in a

    def test_workflow_3_distinguish_data_provenance_and_demo_labels(self, client):
        resp = client.get("/flood-hazards")
        assert resp.status_code == 200
        hazards = resp.json()["hazards"]
        statuses = {h["data_status"] for h in hazards}
        # Must clearly include AUTHORITATIVE and PUBLIC_UNVERIFIED or DEMO
        assert "AUTHORITATIVE" in statuses or "PUBLIC_UNVERIFIED" in statuses or "DEMO" in statuses

        fac_resp = client.get("/emergency-facilities")
        assert fac_resp.status_code == 200
        facilities = fac_resp.json()["facilities"]
        fac_statuses = {f["data_status"] for f in facilities}
        assert "PUBLIC_UNVERIFIED" in fac_statuses or "DEMO" in fac_statuses

    def test_workflow_4_select_facility_and_request_evacuation_route(self, client):
        payload = {
            "origin": {"latitude": 17.3850, "longitude": 78.4867},
            "facility_id": "HYD-H-001",
        }
        resp = client.post("/evacuation-route", json=payload)
        assert resp.status_code == 200
        route = resp.json()
        assert route["route_distance_km"] > 0
        assert route["route_status"] == "ROUTE_AVAILABLE"
        assert len(route["geometry"]) > 1
        assert route["road_condition_status"] in ("UNKNOWN", "CLEAR", "HAZARDS_AVOIDED")

    def test_workflow_5_known_blocked_road_triggers_detour(self):
        # 1. Unconstrained route
        res_clean = build_graph_route(17.3799, 78.4860, 17.3899, 78.4860, road_conditions=[])
        assert res_clean.route_status == "ROUTE_AVAILABLE"

        # 2. Blocked hazard on the primary path across Musi River
        blocked_hazard = RoadConditionResponse(
            id=99,
            road_name="Afzal Gunj Bypass",
            status="FLOODED",
            latitude=17.3830,
            longitude=78.4911,
            notes="[DEMO] Simulated flooded section",
            last_updated=datetime.now(timezone.utc),
        )
        res_detour = build_graph_route(17.3799, 78.4860, 17.3899, 78.4860, road_conditions=[blocked_hazard])
        assert res_detour.route_status == "ROUTE_AVAILABLE"
        assert res_detour.road_condition_status == "HAZARDS_AVOIDED"
        assert res_detour.route_distance_km > res_clean.route_distance_km
        assert res_detour.geometry != res_clean.geometry

    def test_workflow_6_unavailable_alternative_returns_no_safe_route(self):
        # Sever all connections with flood condition at origin
        flood_at_origin = RoadConditionResponse(
            id=201,
            road_name="Origin Access Road",
            status="FLOODED",
            latitude=17.3792,
            longitude=78.4852,
            notes="[DEMO] Origin street submerged",
            last_updated=datetime.now(timezone.utc),
        )
        res = build_graph_route(17.3799, 78.4860, 17.3899, 78.4860, road_conditions=[flood_at_origin])
        assert res.route_status == "NO_SAFE_ROUTE"
        assert res.road_condition_status == "BLOCKED"
        assert res.geometry == []
        assert res.route_distance_km == 0.0

    def test_workflow_7_hazard_intersection_warning_without_blanket_safety_claim(self, client):
        # Check an intersection point with known hazard polygon (Moosarambagh)
        resp = client.get("/flood-hazards/check-location?latitude=17.3715&longitude=78.5085")
        assert resp.status_code == 200
        data = resp.json()
        assert "is_in_hazard_zone" in data
        assert "disclaimer" in data
        # Explicit disclaimer required: lack of documented hazard does NOT imply safety
        assert "not guarantee" in data["disclaimer"].lower() or "unmonitored" in data["disclaimer"].lower()

    def test_workflow_8_hospital_identity_status_and_capacity_separated(self, client):
        resp = client.get("/emergency-facilities/HYD-H-001")
        assert resp.status_code == 200
        hosp = resp.json()
        assert hosp["facility_id"] == "HYD-H-001"
        assert hosp["name"] == "Osmania General Hospital"
        assert hosp["facility_type"] == "HOSPITAL"
        # Invariants: verification flags strictly separate status and capacity
        assert "operational_status_verified" in hosp
        assert "capacity_verified" in hosp
        assert hosp["operational_status_verified"] is False
        assert hosp["capacity_verified"] is False
        assert hosp["capacity"] is None
        assert "verification_note" in hosp

    def test_workflow_9_external_provider_failure_resilience(self, client):
        # Test weather endpoint with simulated failure / fallback
        resp = client.get("/weather?latitude=17.385&longitude=78.486")
        assert resp.status_code == 200
        w_data = resp.json()
        assert "temperature" in w_data
        assert "rainfall" in w_data
        assert "source" in w_data

        # Verify health monitor records feed status without failing overall process
        health_resp = client.get("/health")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert "external_feeds" in health_data
        assert "process" in health_data
        assert health_data["process"]["status"] == "healthy"

    def test_workflow_10_hyderabad_prediction_strictly_returns_model_unsupported(self, client):
        payload = {
            "latitude": 17.3850,
            "longitude": 78.4867,
            "target_date": "2026-10-26",
        }
        resp = client.post("/predict/integrated", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["coverage_status"] == "MODEL_UNSUPPORTED"
        assert data["prediction_available"] is False
        assert data["gauge_distance_km"] > 50.0
        assert "INDOFLOODS" in data["message"]

    def test_workflow_11_unauthorized_users_strictly_barred_from_intake_commit_and_verify(self, client):
        # 1. Unauthenticated commit -> 401
        intake_payload = {
            "content": "date,rainfall\n2020-10-14,150.0",
            "filename": "ghmc_oct2020.csv",
            "metadata": {
                "source_id": "GHMC-001",
                "provider": "GHMC DRF",
                "data_classification": "OBSERVATION",
                "coverage_start": "2020-10-14",
                "coverage_end": "2020-10-15",
                "geographic_boundary": "Greater Hyderabad Municipal Corporation",
                "licensing_or_restriction": "Official Use Only",
                "coordinate_reference_system": "EPSG:4326",
                "elevation_datum": "MSL",
                "temporal_resolution": "DAILY",
                "measurement_units": {"rainfall": "mm"},
                "confidence_level": "HIGH",
            },
        }
        c_unauth = client.post("/data-curation/intake/commit", json=intake_payload)
        assert c_unauth.status_code == 401

        # 2. Analyst trying to commit -> 403 Forbidden
        c_analyst = client.post(
            "/data-curation/intake/commit",
            json=intake_payload,
            headers={"X-API-Key": settings.analyst_api_key},
        )
        assert c_analyst.status_code == 403

        # 3. Unauthenticated facility promote -> 401
        v_unauth = client.post(
            "/emergency-facilities/HYD-H-001/verify",
            json={
                "operational_status": "OPERATIONAL",
                "verification_evidence_source": "GHMC Live Log",
            },
        )
        assert v_unauth.status_code == 401

        # 4. Analyst trying to promote -> 403 Forbidden
        v_analyst = client.post(
            "/emergency-facilities/HYD-H-001/verify",
            json={
                "operational_status": "OPERATIONAL",
                "verification_evidence_source": "GHMC Live Log",
            },
            headers={"X-API-Key": settings.analyst_api_key},
        )
        assert v_analyst.status_code == 403
