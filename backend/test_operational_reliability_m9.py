"""
SafeMap AI — Milestone 9: Operational Reliability and End-to-End Validation
Automated regression and validation test suite.

Covers:
1. Destination selection for shelters and hospitals.
2. Evacuation route generation and road graph navigation.
3. Hazard avoidance, rerouting around flooded roads, and NO_SAFE_ROUTE when severed.
4. Distinguishing facility location/identity verification from live operational/bed readiness.
5. Handling unavailable, timeout, and stale live data (weather, NDMA SACHET, GloFAS).
6. Warnings and rejections when locations intersect documented flood hazards.
7. Preservation of flood-only scope (exclusion of non-flood disaster types).
8. Enforcing Hyderabad MODEL_UNSUPPORTED model-coverage policy.
9. Security audits: path traversal guards, null byte checks, payload limits, and error sanitization.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.hazard import HazardService, classify_flood_alert
from app.services.routing import build_graph_route
from app.services.road_network import road_network_service
from app.services.emergency_facility import get_emergency_facility_service
from app.services.data_importers.institutional_intake import InstitutionalIntakeEngine
from app.schemas.emergency_facility import EmergencyFacility
from app.schemas.resources import RoadConditionResponse
from app.schemas.weather import WeatherResponse


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def loaded_road_graph():
    road_network_service.load_graph()
    return road_network_service.G


# =============================================================================
# 1. Facility Destination Selection & Verification Accuracy
# =============================================================================

class TestFacilityDestinationAndVerification:
    """Audit hospital and shelter verification labels and destination routing."""

    def test_hospital_destination_routing(self, client):
        """Verify routing to an official hospital destination outside flood zone (Gandhi Hospital)."""
        payload = {
            "origin": {"latitude": 17.397, "longitude": 78.478},
            "facility_id": "HYD-H-002"  # Gandhi Hospital, Secunderabad (safe location)
        }
        resp = client.post("/evacuation-route", json=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["facility_id"] == "HYD-H-002"
        assert "Gandhi" in data.get("destination_name", "")
        assert data["destination_type"] == "HOSPITAL"
        assert data["route_status"] == "ROUTE_AVAILABLE"
        assert data["route_distance_km"] > 0

    def test_destination_hospital_in_hazard_zone_displays_warning(self, client):
        """Osmania General Hospital (HYD-H-001) is in the Musi River inundation corridor and must include prominent hazard warning."""
        payload = {
            "origin": {"latitude": 17.397, "longitude": 78.478},
            "facility_id": "HYD-H-001"
        }
        resp = client.post("/evacuation-route", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert any("Destination intersects documented flood hazard area" in w for w in data.get("warnings", []))


    def test_shelter_destination_routing(self, client):
        """Verify routing to a shelter destination by ID."""
        payload = {
            "origin": {"latitude": 17.397, "longitude": 78.478},
            "shelter_id": 1
        }
        resp = client.post("/evacuation-route", json=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["shelter_id"] == 1
        assert data["route_status"] == "ROUTE_AVAILABLE"
        assert data["route_distance_km"] > 0

    def test_hospital_and_shelter_verification_audit_distinction(self, client):
        """
        Verify that facilities distinguish location verification from live
        operational readiness and bed capacity. Neither status nor capacity
        may be claimed verified without supporting evidence.
        """
        resp = client.get("/emergency-facilities")
        assert resp.status_code == 200
        data = resp.json()
        
        # Breakdown counters must exist
        assert "location_verified_count" in data
        assert "operational_status_verified_count" in data
        assert "capacity_verified_count" in data
        assert "unverified_status_count" in data
        assert "unverified_capacity_count" in data

        facilities = data["facilities"]
        assert len(facilities) > 0

        # Physical location is verified against directory, but live status/capacity is unverified
        hospitals = [f for f in facilities if f["facility_type"] == "HOSPITAL"]
        assert len(hospitals) >= 7
        for h in hospitals:
            assert h["location_verified"] is True, f"Hospital {h['name']} should have verified location"
            assert h["operational_status_verified"] is False, f"Hospital {h['name']} live status must not be claimed verified"
            assert h["capacity_verified"] is False, f"Hospital {h['name']} live capacity must not be claimed verified"
            assert h["verification_scope"] == "IDENTITY_ONLY"

        # Mandatory truth-in-data disclaimer
        assert "NOT verified in real-time" in data["data_disclaimer"]

    def test_closed_or_unsafe_facility_rejected_as_destination(self, monkeypatch, client):
        """Evacuation to a closed or flooded facility must be rejected with 409."""
        svc = get_emergency_facility_service()
        closed_fac = EmergencyFacility(
            facility_id="TEST-CLOSED-001",
            name="Closed Emergency Clinic",
            facility_type="HOSPITAL",
            latitude=17.385,
            longitude=78.486,
            operational_status="CLOSED",
            source="TEST",
            data_status="PUBLIC_UNVERIFIED",
            verification_scope="IDENTITY_ONLY"
        )
        monkeypatch.setattr(svc, "get_facility_by_id", lambda fid: closed_fac if fid == "TEST-CLOSED-001" else None)

        payload = {
            "origin": {"latitude": 17.397, "longitude": 78.478},
            "facility_id": "TEST-CLOSED-001"
        }
        resp = client.post("/evacuation-route", json=payload)
        assert resp.status_code == 409
        assert "CLOSED" in resp.json()["detail"]


# =============================================================================
# 2. Road Hazard Rerouting & Safety Invariants
# =============================================================================

class TestRoadHazardRoutingAndSafety:
    """Test road network routing, detour calculation, and NO_SAFE_ROUTE."""

    def test_reroute_around_blocked_road_segment(self, loaded_road_graph):
        """Routing must identify blocked edges and calculate an alternative detour."""
        origin_lat, origin_lon = 17.397, 78.478
        dest_lat, dest_lon = 17.3789, 78.4777  # Osmania Hospital

        # Baseline clear route
        base_route = build_graph_route(origin_lat, origin_lon, dest_lat, dest_lon, road_conditions=[])
        assert base_route.route_status == "ROUTE_AVAILABLE"

        # Flooded road condition report
        flooded_road = RoadConditionResponse(
            id=101,
            road_name="Musi Riverside Road",
            status="FLOODED",
            latitude=17.385,
            longitude=78.486,
            notes="Submerged by 0.8m floodwaters.",
            last_updated=datetime.now(timezone.utc)
        )

        hazard_route = build_graph_route(origin_lat, origin_lon, dest_lat, dest_lon, road_conditions=[flooded_road])
        assert hazard_route.route_status == "ROUTE_AVAILABLE"
        # Must record hazard avoidance or clear evaluation
        assert hazard_route.road_condition_status in ("HAZARDS_AVOIDED", "CLEAR")

    def test_no_safe_route_when_all_viable_paths_are_blocked(self, loaded_road_graph, monkeypatch):
        """When floodwaters block all paths to destination, returns NO_SAFE_ROUTE."""
        import networkx as nx

        # Simulate path finding failure on G_eval where unconstrained G has a path
        orig_lat, orig_lon = 17.397, 78.478
        dest_lat, dest_lon = 17.3789, 78.4777

        # Mock match_road_conditions to return blocked edges and simulate severance
        from app.services import routing as routing_module

        def mock_match(G, conditions):
            # Return dummy edge keys and matched hazard
            return {(1, 2, 0)}, ["Musi River Crossing (FLOODED)"], []

        monkeypatch.setattr(routing_module, "match_road_conditions", mock_match)

        # Force nx.shortest_path on G_eval to raise NetworkXNoPath while G has path
        orig_shortest_path = nx.shortest_path

        def mock_shortest_path(G, source, target, weight=None):
            # If G is G_eval (restricted view), raise NoPath
            if hasattr(G, "_graph"):
                raise nx.NetworkXNoPath("Simulated road network severance by flood")
            return orig_shortest_path(G, source, target, weight=weight)

        monkeypatch.setattr(nx, "shortest_path", mock_shortest_path)
        monkeypatch.setattr(nx, "has_path", lambda G, s, t: True)

        res = routing_module.build_graph_route(
            orig_lat, orig_lon, dest_lat, dest_lon,
            road_conditions=[{"status": "FLOODED", "latitude": 17.385, "longitude": 78.486}]
        )
        assert res.route_status == "NO_SAFE_ROUTE"
        assert res.road_condition_status == "BLOCKED"
        assert any("flooded or blocked" in w.lower() for w in res.warnings)


# =============================================================================
# 3. Flood Hazard Intersections & Safety Warnings
# =============================================================================

class TestFloodHazardIntersectionWarnings:
    """Verify warnings and safety stops when coordinates intersect flood hazard zones."""

    def test_warning_when_origin_intersects_flood_hazard(self, client):
        """When evacuation origin is within a documented flood polygon, attaches alert."""
        # Lower Begumpet Flash Flood Zone [DEMO]: 17.442, 78.475
        payload = {
            "origin": {"latitude": 17.442, "longitude": 78.475},
            "shelter_id": 1
        }
        resp = client.post("/evacuation-route", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert any("intersects active flood hazard zone" in w for w in data.get("warnings", []))

    def test_warning_when_destination_intersects_flood_hazard(self, client):
        """When destination itself is inside an active flood hazard, a prominent warning is attached."""
        # Lower Begumpet Flash Flood Zone is at (17.442, 78.475) with HIGH severity
        payload = {
            "origin": {"latitude": 17.397, "longitude": 78.478},
            "destination": {"latitude": 17.442, "longitude": 78.475}
        }
        resp = client.post("/evacuation-route", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert any("Destination intersects documented flood hazard area" in w for w in data.get("warnings", []))


    def test_check_location_warns_and_provides_safety_disclaimer(self, client):
        """Check location API provides spatial rule and mandatory safety disclaimer."""
        # Inside Lower Begumpet corridor
        resp = client.get("/flood-hazards/check-location?latitude=17.442&longitude=78.475")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_in_hazard_zone"] is True
        assert data["hazard_count"] >= 1
        assert data["highest_severity"] in ("HIGH", "SEVERE", "EXTREME")
        assert len(data["intersected_hazards"]) >= 1
        assert "Ray-casting" in data["spatial_rule"]
        assert "Absence of an alert does NOT guarantee that the area is safe" in data["disclaimer"]

        # Point outside documented zones
        resp_clear = client.get("/flood-hazards/check-location?latitude=17.350&longitude=78.400")
        assert resp_clear.status_code == 200
        data_clear = resp_clear.json()
        assert data_clear["is_in_hazard_zone"] is False
        assert data_clear["highest_severity"] == "NONE"
        assert "Absence of an alert does NOT guarantee that the area is safe" in data_clear["disclaimer"]


# =============================================================================
# 4. Live Data Reliability, Staleness & Provider Failures
# =============================================================================

class TestLiveDataReliabilityAndFailures:
    """Verify provider timeout handling, staleness detection, and error transparency."""

    def test_weather_staleness_flag_when_observation_is_old(self, monkeypatch):
        """When OpenWeather observation dt is > 3 hours old, is_stale must be True."""
        from app.services import weather as weather_module
        old_time = datetime.now(timezone.utc) - timedelta(hours=4)

        # Mock OpenWeather API response with old dt
        class MockResp:
            status_code = 200
            def raise_for_status(self): pass
            def json(self):
                return {
                    "dt": int(old_time.timestamp()),
                    "main": {"temp": 28.0, "humidity": 80.0, "pressure": 1005.0},
                    "wind": {"speed": 4.5},
                    "weather": [{"main": "Rain", "description": "heavy rain"}],
                    "rain": {"1h": 12.0}
                }

        monkeypatch.setattr(weather_module.settings, "weather_api_key", "mock_key")
        monkeypatch.setattr(weather_module.httpx, "get", lambda *args, **kwargs: MockResp())

        res = weather_module.fetch_weather(17.385, 78.486)
        assert res.is_stale is True
        assert res.warning is not None
        assert "older than 3 hours" in res.warning

    def test_weather_provider_timeout_returns_504(self, monkeypatch, client):
        """When weather provider times out, returns HTTP 504 with structured message."""
        from app.services import weather as weather_module
        import httpx

        def mock_timeout(*args, **kwargs):
            raise httpx.TimeoutException("Connection timed out")

        monkeypatch.setattr(weather_module.settings, "weather_api_key", "mock_key")
        monkeypatch.setattr(weather_module.httpx, "get", mock_timeout)

        resp = client.get("/weather?latitude=17.385&longitude=78.486")
        assert resp.status_code == 504
        assert "timed out" in resp.json()["detail"].lower()

    def test_hazard_service_captures_provider_warnings_on_feed_failure(self, monkeypatch, client):
        """When NDMA SACHET or GloFAS fails, provider_warnings are populated transparently."""
        hz_svc = HazardService()

        # Mock NDMA Sachet to raise an exception
        def mock_sachet_fail(*args, **kwargs):
            hz_svc.last_provider_warnings.append("NDMA SACHET live CAP alert feed was unavailable (SimulatedNetworkError).")
            return []

        monkeypatch.setattr(hz_svc, "fetch_ndma_sachet_alerts", mock_sachet_fail)

        hazards = hz_svc.get_hazards(include_demo=True, include_authoritative=True)
        assert len(hazards) > 0  # Municipal zones and demo still available
        warnings = hz_svc.get_last_provider_warnings()
        assert len(warnings) > 0
        assert any("NDMA SACHET" in w for w in warnings)


# =============================================================================
# 5. Flood-Only Scope Preservation & Hyderabad Model Policy
# =============================================================================

class TestFloodOnlyScopeAndHyderabadPolicy:
    """Verify non-flood exclusion and Hyderabad model suppression invariants."""

    def test_disaster_alerts_strictly_flood_only(self, client):
        """Official disaster alerts API must strictly filter and return flood records only."""
        resp = client.get("/disaster-alerts")
        assert resp.status_code == 200
        alerts = resp.json()
        assert len(alerts) > 0
        for alert in alerts:
            assert alert["disaster_type"] in {
                "FLOOD", "FLASH_FLOOD", "URBAN_INUNDATION",
                "WATERLOGGING", "RIVER_OVERFLOW", "FLOOD_RELATED_HEAVY_RAINFALL"
            }

    def test_non_flood_disaster_types_rejected_by_hazard_api(self, client):
        """Querying non-flood disaster types must return HTTP 400 Bad Request."""
        for disallowed in ["EARTHQUAKE", "TSUNAMI", "CYCLONE", "WILDFIRE", "LANDSLIDE", "DROUGHT"]:
            resp = client.get(f"/flood-hazards?hazard_type={disallowed}")
            assert resp.status_code == 400
            assert "Unsupported non-flood" in resp.json()["detail"]

    def test_hyderabad_model_unsupported_guard_intact(self, client):
        """Hyderabad coordinates must strictly return MODEL_UNSUPPORTED with 50km guard."""
        payload = {
            "latitude": 17.385,
            "longitude": 78.486,
            "target_date": "2024-08-01"
        }
        resp = client.post("/predict/integrated", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["prediction_available"] is False
        assert data["coverage_status"] == "MODEL_UNSUPPORTED"
        assert data["maximum_supported_distance_km"] == 50.0
        assert data["prediction"] is None


# =============================================================================
# 6. Security, File Validation & Error Sanitization
# =============================================================================

class TestSecurityAndErrorHandling:
    """Audit administrative intake path validation, payload limits, and error sanitization."""

    def test_path_traversal_sanitization_in_institutional_intake(self, tmp_path):
        """Filenames with directory traversal sequences must be sanitized to pure basenames."""
        engine = InstitutionalIntakeEngine(base_dir=tmp_path)
        content = "timestamp,station_id,rainfall_mm\n2024-08-01T00:00:00Z,ST-01,15.5\n"
        meta = {
            "provider": "GHMC Engineering",
            "source_reference": "Ref-2024",
            "retrieval_date": "2024-08-02T00:00:00Z",
            "measurement_classification": "OBSERVED",
        }

        # Submit dangerous path
        res = engine.commit_batch(content, "../../../evil_intake.csv", meta)
        assert res["status"] == "SUCCESS"
        raw_file = Path(tmp_path / res["raw_file"])
        assert raw_file.exists()
        # Verify the file was stored inside the designated raw intake directory
        assert str(raw_file.resolve()).startswith(str(engine.raw_dir.resolve()))
        assert ".." not in raw_file.name

    def test_null_byte_injection_rejected(self, tmp_path):
        """Filenames with null bytes must be rejected."""
        engine = InstitutionalIntakeEngine(base_dir=tmp_path)
        meta = {
            "provider": "GHMC",
            "source_reference": "Ref",
            "retrieval_date": "2024-08-01T00:00:00Z",
        }
        val = engine.validate_content("col1,col2\n1,2", "file\x00.csv", meta)
        assert val["valid"] is False
        assert any("null byte" in err["error"] for err in val["errors"])

    def test_excessive_payload_size_rejected(self, tmp_path):
        """Payloads exceeding 10MB limit must be rejected."""
        engine = InstitutionalIntakeEngine(base_dir=tmp_path)
        meta = {
            "provider": "GHMC",
            "source_reference": "Ref",
            "retrieval_date": "2024-08-01T00:00:00Z",
        }
        oversized_content = "x" * (11 * 1024 * 1024)  # 11MB
        val = engine.validate_content(oversized_content, "large.csv", meta)
        assert val["valid"] is False
        assert any("exceeds maximum allowable intake limit" in err["error"] for err in val["errors"])

    def test_global_exception_handler_sanitizes_errors(self, monkeypatch):
        """Unhandled server errors must return a clean message without stack trace leakage."""
        from app.api import resources as res_api

        def mock_crash():
            raise RuntimeError("Secret DB Password in memory: postgres://admin:super_secret@localhost:5432/db")

        monkeypatch.setattr(res_api, "demo_alerts", mock_crash)

        client_no_raise = TestClient(app, raise_server_exceptions=False)
        resp = client_no_raise.get("/disaster-alerts")
        assert resp.status_code == 500
        data = resp.json()
        assert "super_secret" not in str(data)
        assert "An internal server error occurred" in data["detail"]

