"""
Unit and regression tests verifying SafeMap AI's strict Flood-Only Scope:
1. Flood-related official alerts are ingested correctly.
2. Tsunami, earthquake, cyclone, wildfire, landslide, and drought alerts are excluded from active hazards.
3. Ambiguous and non-flood weather alerts are not silently classified as floods.
4. HazardRecord and AlertResponse schemas strictly reject non-flood disaster types.
5. GET /flood-hazards rejects non-flood hazard_type queries.
6. Existing flood layers, historical event catalogue, and weather data remain functional.
7. Flood evacuation routing, road obstruction avoidance, and NO_SAFE_ROUTE behavior are preserved.
8. Emergency facilities, hospitals, and shelters remain functional.
9. Hyderabad ML predictions remain strictly suppressed under MODEL_UNSUPPORTED.
10. No non-flood disaster modules are exposed in active application interfaces.
"""

from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
import xml.etree.ElementTree as ET

from app.main import app
from app.schemas.hazard import (
    ALLOWED_FLOOD_HAZARD_TYPES,
    DISALLOWED_NON_FLOOD_TYPES,
    HazardRecord,
)
from app.schemas.resources import (
    ALLOWED_FLOOD_DISASTER_TYPES,
    DISALLOWED_NON_FLOOD_DISASTER_TYPES,
    AlertResponse,
    RoadConditionResponse,
)
from app.services.hazard import (
    HazardService,
    classify_flood_alert,
)
from app.services.routing import build_graph_route

client = TestClient(app)


# ---------------------------------------------------------------------------
# Task 6.1 & 6.2: Alert Classification & Exclusion of Non-Flood Hazards
# ---------------------------------------------------------------------------

class TestFloodAlertClassificationAndExclusion:
    """Verifies that CAP alerts are correctly classified or excluded based on flood relevance."""

    def test_flood_related_alerts_classified_correctly(self):
        """Official flood, river overflow, waterlogging, and heavy rain warnings are recognized."""
        # 1. Musi River overflow
        res1 = classify_flood_alert(
            headline="Flood Alert: Musi River water level rising rapidly near Moosarambagh",
            description="Upstream reservoir gate opening at Osman Sagar releasing surplus into Musi river."
        )
        assert res1 is not None
        hazard_type, sev = res1
        assert hazard_type == "RIVER_OVERFLOW"
        assert sev in ("HIGH", "SEVERE", "EXTREME", "MODERATE")

        # 2. Urban waterlogging / inundation
        res2 = classify_flood_alert(
            headline="Severe Waterlogging and Urban Inundation in Begumpet and Rasoolpura",
            description="Stormwater drainage overflow inundating low-lying residential sectors."
        )
        assert res2 is not None
        hazard_type, sev = res2
        assert hazard_type in ("URBAN_INUNDATION", "WATERLOGGING")

        # 3. Flash flood warning
        res3 = classify_flood_alert(
            headline="Flash Flood Warning for Hyderabad Municipal Corridors",
            description="Sudden cloudburst causing rapid flash inundation along urban nalas."
        )
        assert res3 is not None
        hazard_type, sev = res3
        assert hazard_type == "FLASH_FLOOD"

        # 4. Extreme rainfall flood alert
        res4 = classify_flood_alert(
            headline="Red Alert: Extremely Heavy Rainfall warning with flash flood risk for Hyderabad",
            description="Continuous torrential rainfall expected to cause extensive street submergence."
        )
        assert res4 is not None
        hazard_type, sev = res4
        assert hazard_type in ("FLOOD_RELATED_HEAVY_RAINFALL", "FLASH_FLOOD")
        assert sev == "EXTREME"

    def test_non_flood_disasters_strictly_excluded(self):
        """Tsunamis, earthquakes, cyclones, wildfires, landslides, droughts must be excluded."""
        fixtures = [
            # Tsunami
            ("Tsunami Warning for East Coast of India", "Seismic sea wave alert following subduction earthquake."),
            # Coastal surge
            ("Coastal Storm Surge and High Tide Warning", "Rough sea conditions with 4m swell along shoreline."),
            # Earthquake
            ("Earthquake Magnitude 5.4 Recorded in Deccan Plateau", "Epicenter 45km deep, minor tremors felt."),
            # Cyclone standalone
            ("Cyclonic Storm Warning for Bay of Bengal", "Gale winds up to 100 km/h tracking towards Odisha coast."),
            # Wildfire
            ("Forest Fire and Wildfire Alert in Eturnagaram Sanctuary", "High heat causing dry vegetation burn."),
            # Landslide
            ("Landslide and Mudslide Hazard for Hilly Slopes", "Rockfall risk along hillside road cuts."),
            # Drought
            ("Severe Drought and Water Scarcity Advisory", "Extended dry spell impacting agricultural irrigation."),
            # Heatwave
            ("Extreme Heatwave Alert: Maximum Temperatures Exceeding 45C", "Severe sunstroke warning."),
            # Volcano
            ("Volcanic Ash Cloud Advisory", "Regional flight advisory due to ash dispersion."),
            # Tornado / Gale
            ("Tornado and Severe Dust Storm Advisory", "High-velocity convective gale winds."),
        ]

        for headline, desc in fixtures:
            classification = classify_flood_alert(headline=headline, description=desc)
            assert classification is None, f"Expected non-flood alert to be excluded, but got: {classification} for '{headline}'"

    def test_ambiguous_and_general_weather_not_classified_as_floods(self):
        """Ordinary rain, thunderstorms, and general weather must NOT be classified as floods."""
        ambiguous_fixtures = [
            ("Thunderstorm with Lightning Warning", "Scattered convective activity across northern districts."),
            ("Light to Moderate Rain Expected Tomorrow", "Intermittent monsoon showers across Telangana."),
            ("Gusty Winds Advisory", "Wind speeds 30-40 km/h expected in open areas."),
            ("General Weather Advisory for Farmers", "Humidity levels high, overcast skies."),
            ("Isolated Passing Showers in Evening", "Short duration light rain in isolated pockets."),
        ]

        for headline, desc in ambiguous_fixtures:
            res = classify_flood_alert(headline=headline, description=desc)
            assert res is None, f"Ambiguous weather must not be converted to flood: '{headline}'"


# ---------------------------------------------------------------------------
# Task 6.1 & 6.2: Synthetic CAP Feed RSS Parser Integration
# ---------------------------------------------------------------------------

class TestSyntheticCapFeedIngestion:
    """Tests NDMA SACHET RSS/CAP XML ingestion with mixed synthetic disaster fixtures."""

    @pytest.fixture
    def synthetic_cap_feed_xml(self) -> str:
        """Synthetic CAP RSS feed containing 2 flood alerts and 4 non-flood/ambiguous alerts."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>NDMA SACHET Live Disaster Feed</title>
    <item>
      <title>Flood Warning: Musi River Causeway Overflow at Moosarambagh</title>
      <link>https://sachet.ndma.gov.in/alert?identifier=TEST-FL-001</link>
      <description>River stage rising above warning level due to upstream dam releases.</description>
      <pubDate>Mon, 26 Oct 2026 10:00:00 +0530</pubDate>
    </item>
    <item>
      <title>Tsunami Alert for Coastal Harbors</title>
      <link>https://sachet.ndma.gov.in/alert?identifier=TEST-TSU-001</link>
      <description>Undersea seismic activity trigger tsunami watch.</description>
      <pubDate>Mon, 26 Oct 2026 10:05:00 +0530</pubDate>
    </item>
    <item>
      <title>Earthquake of Magnitude 4.8 Recorded</title>
      <link>https://sachet.ndma.gov.in/alert?identifier=TEST-EQ-001</link>
      <description>Epicenter detected 120km away. No structural damage reported.</description>
      <pubDate>Mon, 26 Oct 2026 10:10:00 +0530</pubDate>
    </item>
    <item>
      <title>Urban Inundation and Waterlogging in Begumpet Low-Lying Sectors</title>
      <link>https://sachet.ndma.gov.in/alert?identifier=TEST-FL-002</link>
      <description>Extensive waterlogging along storm drains causing road blockages.</description>
      <pubDate>Mon, 26 Oct 2026 10:15:00 +0530</pubDate>
    </item>
    <item>
      <title>Wildfire Risk for Forest Border Zones</title>
      <link>https://sachet.ndma.gov.in/alert?identifier=TEST-FIRE-001</link>
      <description>Dry brush conditions elevate wildfire danger.</description>
      <pubDate>Mon, 26 Oct 2026 10:20:00 +0530</pubDate>
    </item>
    <item>
      <title>Thunderstorm and Lightning Advisory</title>
      <link>https://sachet.ndma.gov.in/alert?identifier=TEST-THU-001</link>
      <description>Scattered lightning strikes expected in open fields.</description>
      <pubDate>Mon, 26 Oct 2026 10:25:00 +0530</pubDate>
    </item>
  </channel>
</rss>"""

    def test_feed_ingestion_retains_floods_and_excludes_non_floods(self, synthetic_cap_feed_xml):
        """Verifies that only the 2 flood alerts are ingested, and the other 4 are excluded."""
        service = HazardService()
        alerts = service.fetch_ndma_sachet_alerts(feed_content=synthetic_cap_feed_xml)

        # Only 2 alerts should be ingested
        assert len(alerts) == 2, f"Expected exactly 2 flood alerts, but got {len(alerts)}"

        # Verify ingested alerts are flood-related
        for a in alerts:
            assert a.hazard_type in ("RIVER_OVERFLOW", "URBAN_INUNDATION", "FLOOD", "FLASH_FLOOD", "FLOOD_RELATED_HEAVY_RAINFALL")
            assert a.source_type == "OFFICIAL_ALERT"
            assert a.data_status == "AUTHORITATIVE"

        # Verify excluded non-flood alerts are NOT in results
        alert_ids = [a.hazard_id for a in alerts]
        assert "TEST-FL-001" in alert_ids[0] or "TEST-FL-001" in alert_ids[1]
        assert not any("TSU" in hid for hid in alert_ids)
        assert not any("EQ" in hid for hid in alert_ids)
        assert not any("FIRE" in hid for hid in alert_ids)
        assert not any("THU" in hid for hid in alert_ids)


# ---------------------------------------------------------------------------
# Task 6.4 & 6.5: Hazard Schema and API Restriction
# ---------------------------------------------------------------------------

class TestHazardSchemaRestrictions:
    """Verifies that HazardRecord and AlertResponse reject non-flood disasters."""

    def test_hazard_record_rejects_non_flood_disasters(self):
        """Attempting to construct HazardRecord with non-flood disaster types raises ValueError."""
        now = datetime.now(timezone.utc)
        non_flood_types = ["TSUNAMI", "EARTHQUAKE", "CYCLONE", "WILDFIRE", "LANDSLIDE", "DROUGHT", "VOLCANO"]

        for nft in non_flood_types:
            with pytest.raises(ValueError, match="Unsupported non-flood disaster"):
                HazardRecord(
                    hazard_id=f"TEST-{nft}",
                    hazard_type=nft,
                    title=f"Test {nft}",
                    description="Testing restriction",
                    source_name="Test Source",
                    last_retrieved=now,
                    data_status="PUBLIC_UNVERIFIED",
                    verification_note="Testing restriction"
                )

    def test_hazard_record_accepts_valid_flood_types(self):
        """Valid flood hazard types are accepted by HazardRecord."""
        now = datetime.now(timezone.utc)
        valid_types = [
            "FLOOD",
            "FLOOD_ZONE",
            "RIVER_OVERFLOW",
            "URBAN_INUNDATION",
            "WATERLOGGING",
            "WATER_STAGNATION",
            "FLASH_FLOOD",
            "FLOOD_RELATED_HEAVY_RAINFALL",
        ]

        for vt in valid_types:
            rec = HazardRecord(
                hazard_id=f"TEST-{vt}",
                hazard_type=vt,
                title=f"Test {vt}",
                description="Valid flood hazard",
                source_name="Test Source",
                last_retrieved=now,
                data_status="PUBLIC_UNVERIFIED",
                verification_note="Valid"
            )
            assert rec.hazard_type == vt

    def test_alert_response_schema_rejects_non_flood_disaster_types(self):
        """AlertResponse rejects non-flood disaster_type values."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="Unsupported non-flood disaster type"):
            AlertResponse(
                id=99,
                disaster_type="EARTHQUAKE",
                severity="HIGH",
                affected_area="Test Area",
                source="Test Source",
                description="Test non-flood alert",
                issued_at=now
            )

        with pytest.raises(ValueError, match="Unsupported non-flood disaster type"):
            AlertResponse(
                id=100,
                disaster_type="TSUNAMI",
                severity="EXTREME",
                affected_area="Coast",
                source="Test Source",
                description="Test tsunami alert",
                issued_at=now
            )

        # Valid flood alert succeeds
        valid_alert = AlertResponse(
            id=101,
            disaster_type="FLOOD",
            severity="HIGH",
            affected_area="Musi corridor",
            source="Test Source",
            description="Valid flood alert",
            issued_at=now
        )
        assert valid_alert.disaster_type == "FLOOD"

    def test_api_flood_hazards_rejects_non_flood_query(self):
        """Querying /flood-hazards with non-flood hazard_type parameter returns HTTP 400."""
        # Non-flood hazard types
        for nft in ["EARTHQUAKE", "TSUNAMI", "CYCLONE", "WILDFIRE", "LANDSLIDE"]:
            resp = client.get(f"/flood-hazards?hazard_type={nft}")
            assert resp.status_code == 400, f"Expected 400 for hazard_type={nft}, got {resp.status_code}"
            assert "Unsupported non-flood hazard type" in resp.json()["detail"]

        # Valid flood hazard query succeeds
        resp_valid = client.get("/flood-hazards?hazard_type=RIVER_OVERFLOW")
        assert resp_valid.status_code == 200


# ---------------------------------------------------------------------------
# Task 6.5 & 6.6: Preservation of Existing Flood Functionality
# ---------------------------------------------------------------------------

class TestPreservationOfFloodFunctionality:
    """Verifies that all flood capabilities remain fully operational after the scope cleanup."""

    def test_flood_hazards_endpoint_operational(self):
        """GET /flood-hazards returns flood zones and demo records."""
        resp = client.get("/flood-hazards")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0
        for h in data["hazards"]:
            assert h["hazard_type"] in ALLOWED_FLOOD_HAZARD_TYPES

    def test_historical_flood_events_catalogue_intact(self):
        """Curated historical flood event catalogue returns the 8 Hyderabad flood events."""
        resp = client.get("/data-curation/historical-events")
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) == 8
        event_types = [e["flood_type"] for e in events]
        for et in event_types:
            assert any(f in et.lower() for f in ["flood", "overflow", "surge", "runoff", "breach"])

    def test_ambient_weather_endpoint_functional(self):
        """Weather endpoint remains functional as supporting context."""
        resp = client.get("/weather?latitude=17.385&longitude=78.486")
        assert resp.status_code == 200
        data = resp.json()
        assert "temperature" in data
        assert "humidity" in data
        assert "rainfall" in data

    def test_flood_routing_and_obstruction_avoidance_preserved(self):
        """Graph-based evacuation routing safely routes around flooded roads."""
        now = datetime.now(timezone.utc)
        res = build_graph_route(
            origin_lat=17.3799,
            origin_lon=78.4860,
            dest_lat=17.3899,
            dest_lon=78.4860,
            road_conditions=[
                RoadConditionResponse(
                    id=901,
                    road_name="Flooded Causeway Road",
                    status="FLOODED",
                    latitude=17.3830,
                    longitude=78.4911,
                    notes="[DEMO] Flooded road segment",
                    last_updated=now
                )
            ]
        )
        assert res.route_status == "ROUTE_AVAILABLE"
        assert res.road_condition_status == "HAZARDS_AVOIDED"
        assert res.is_rerouted is True

    def test_emergency_facilities_and_shelters_intact(self):
        """Hospitals and shelter endpoints remain fully available."""
        fac_resp = client.get("/emergency-facilities")
        assert fac_resp.status_code == 200
        assert fac_resp.json()["total"] >= 18

        sh_resp = client.get("/shelters")
        assert sh_resp.status_code == 200
        assert sh_resp.json()["total"] == 11

    def test_hyderabad_remains_model_unsupported(self):
        """Hyderabad coordinates strictly remain MODEL_UNSUPPORTED and INSUFFICIENT_LOCAL_DATA."""
        resp = client.get("/risk-map?latitude=17.385&longitude=78.486")
        assert resp.status_code == 200
        data = resp.json()
        assert data["coverage_status"] == "MODEL_UNSUPPORTED"
        assert data["data_readiness_status"] == "INSUFFICIENT_LOCAL_DATA"
        assert data["prediction_available"] is False
        assert data["predicted_class"] is None


# ---------------------------------------------------------------------------
# Task 6.8: No Non-Flood Modules in Application
# ---------------------------------------------------------------------------

class TestNoNonFloodModulesInApplication:
    """Verifies that no non-flood modules or standalone menus are present in frontend/API."""

    def test_api_title_and_health_reflect_flood_management(self):
        """FastAPI title and health service name describe flood management."""
        assert "Flood" in app.title
        assert "Disaster Management API" not in app.title

        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "safemap-flood-management-api"

    def test_disaster_alerts_api_only_returns_flood_alerts(self):
        """GET /disaster-alerts returns exclusively flood disaster types."""
        resp = client.get("/disaster-alerts")
        assert resp.status_code == 200
        alerts = resp.json()
        for a in alerts:
            assert a["disaster_type"] in ALLOWED_FLOOD_DISASTER_TYPES
