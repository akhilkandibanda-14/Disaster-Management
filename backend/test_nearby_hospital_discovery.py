import pytest
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services.hospital_discovery import (
    HospitalDiscoveryService,
    haversine_km,
    normalize_facility_name,
)

client = TestClient(app)

CENTRAL_HYD_LAT = 17.3850
CENTRAL_HYD_LON = 78.4867


class TestNearbyHospitalDiscovery:
    """Acceptance test suite for Nearby Hospital Discovery via OpenStreetMap POIs."""

    def test_coordinate_validation_invalid_bounds(self):
        """Rejects latitudes and longitudes outside acceptable ranges."""
        res1 = client.get(f"/emergency-facilities/nearby-hospitals?latitude=95.0&longitude={CENTRAL_HYD_LON}")
        assert res1.status_code == 422

        res2 = client.get(f"/emergency-facilities/nearby-hospitals?latitude={CENTRAL_HYD_LAT}&longitude=-200.0")
        assert res2.status_code == 422

    def test_coordinate_validation_outside_hyderabad(self):
        """Rejects coordinates outside supported Hyderabad metropolitan boundaries with explicit 400."""
        # Bangalore coordinates
        res = client.get("/emergency-facilities/nearby-hospitals?latitude=12.9716&longitude=77.5946&radius_km=5.0")
        assert res.status_code == 400
        assert "Hyderabad coordinates only" in res.json().get("detail", "")

    def test_radius_validation(self):
        """Rejects zero, negative, or excessively large radius values."""
        res_zero = client.get(f"/emergency-facilities/nearby-hospitals?latitude={CENTRAL_HYD_LAT}&longitude={CENTRAL_HYD_LON}&radius_km=0")
        assert res_zero.status_code == 422  # Query(..., gt=0)

        res_excessive = client.get(f"/emergency-facilities/nearby-hospitals?latitude={CENTRAL_HYD_LAT}&longitude={CENTRAL_HYD_LON}&radius_km=50.0")
        assert res_excessive.status_code == 422  # Query(..., le=30.0)

    def test_discovery_distance_sorting(self):
        """Returns genuine OSM hospital candidates sorted strictly ascending by straight-line distance."""
        res = client.get(
            f"/emergency-facilities/nearby-hospitals?latitude={CENTRAL_HYD_LAT}&longitude={CENTRAL_HYD_LON}&radius_km=10.0&limit=10"
        )
        assert res.status_code == 200
        data = res.json()
        assert "hospitals" in data
        assert data["total"] > 0
        hospitals = data["hospitals"]
        assert len(hospitals) <= 10

        # Verify strict ascending sort order by distance_km
        distances = [h["distance_km"] for h in hospitals]
        assert distances == sorted(distances), f"Distances not sorted ascending: {distances}"

        # Verify all candidates are within the specified radius
        for h in hospitals:
            assert h["distance_km"] <= 10.0
            assert h["latitude"] >= 17.2 and h["latitude"] <= 17.6
            assert h["longitude"] >= 78.2 and h["longitude"] <= 78.7
            assert h["facility_id"].startswith("OSM-")

    def test_deduplication_and_name_normalization(self):
        """Verifies deduplication logic cleans names and prevents co-located duplicates."""
        service = HospitalDiscoveryService()
        raw_elements = [
            {
                "type": "node",
                "id": 1001,
                "lat": 17.4265,
                "lon": 78.4552,
                "tags": {"name": "Yashoda Hospital", "amenity": "hospital"}
            },
            {
                "type": "way",
                "id": 2002,
                "center": {"lat": 17.4266, "lon": 78.4553},  # ~15m away
                "tags": {"name": "Yashoda Hospital, Somajiguda", "amenity": "hospital"}
            },
            {
                "type": "node",
                "id": 3003,
                "lat": 17.4156,
                "lon": 78.4485,
                "tags": {"name": "Care Hospital", "amenity": "hospital"}
            }
        ]
        processed = service._process_elements(raw_elements, CENTRAL_HYD_LAT, CENTRAL_HYD_LON, 10.0)
        # Yashoda Hospital duplicates should be merged into 1
        yashoda_entries = [h for h in processed if "Yashoda" in h.name]
        assert len(yashoda_entries) == 1
        assert len(processed) == 2

    def test_missing_name_fallback(self):
        """Falls back safely to 'Unnamed Medical Facility (OSM)' when name tag is absent."""
        service = HospitalDiscoveryService()
        raw_elements = [
            {
                "type": "node",
                "id": 9999,
                "lat": 17.4000,
                "lon": 78.4700,
                "tags": {"amenity": "hospital"}  # Missing name tag
            }
        ]
        processed = service._process_elements(raw_elements, CENTRAL_HYD_LAT, CENTRAL_HYD_LON, 5.0)
        assert len(processed) == 1
        assert processed[0].name == "Unnamed Medical Facility (OSM)"

    def test_truth_in_data_disclosures(self):
        """Candidate records must explicitly disclose unverified operational status and capacity."""
        res = client.get(
            f"/emergency-facilities/nearby-hospitals?latitude={CENTRAL_HYD_LAT}&longitude={CENTRAL_HYD_LON}&radius_km=5.0"
        )
        assert res.status_code == 200
        data = res.json()
        assert data["data_status"] == "PUBLIC_UNVERIFIED"
        assert "not verified" in data["disclaimer"].lower()

        for h in data["hospitals"]:
            assert h["data_status"] == "PUBLIC_UNVERIFIED"
            assert h["verification_status"] == "UNVERIFIED"
            assert h["operational_status"] == "UNKNOWN"
            assert h["capacity"] is None
            assert h["operational_status_verified"] is False
            assert h["capacity_verified"] is False
            assert "not verified" in h["verification_note"].lower()

    def test_overpass_timeout_graceful_fallback(self):
        """When Overpass API times out, service falls back to OSM POI registry with a warning."""
        with patch.object(HospitalDiscoveryService, "_query_overpass", side_effect=httpx.TimeoutException("Read timed out")):
            service = HospitalDiscoveryService()
            response = service.discover_nearby_hospitals(
                latitude=CENTRAL_HYD_LAT,
                longitude=CENTRAL_HYD_LON,
                radius_km=5.0,
                force_refresh=True
            )
            assert response.total > 0
            assert "OSM POI Registry" in response.source
            assert response.warning is not None
            assert "timed out" in response.warning.lower()

    def test_in_memory_cache_efficiency(self):
        """Subsequent queries with identical coordinates and radius return cached results."""
        res1 = client.get(
            f"/emergency-facilities/nearby-hospitals?latitude={CENTRAL_HYD_LAT}&longitude={CENTRAL_HYD_LON}&radius_km=4.0"
        )
        assert res1.status_code == 200

        res2 = client.get(
            f"/emergency-facilities/nearby-hospitals?latitude={CENTRAL_HYD_LAT}&longitude={CENTRAL_HYD_LON}&radius_km=4.0"
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert "Cached" in data2["source"]

    def test_facility_id_lookup_resolution(self):
        """Discovered hospital candidates can be fetched via GET /emergency-facilities/{facility_id}."""
        # 1. Discover a candidate
        disc_res = client.get(
            f"/emergency-facilities/nearby-hospitals?latitude={CENTRAL_HYD_LAT}&longitude={CENTRAL_HYD_LON}&radius_km=5.0"
        )
        hospitals = disc_res.json().get("hospitals", [])
        assert len(hospitals) > 0
        candidate = hospitals[0]
        fac_id = candidate["facility_id"]

        # 2. Look up via emergency facilities endpoint
        lookup_res = client.get(f"/emergency-facilities/{fac_id}")
        assert lookup_res.status_code == 200
        fac_data = lookup_res.json()
        assert fac_data["facility_id"] == fac_id
        assert fac_data["name"] == candidate["name"]
        assert fac_data["latitude"] == candidate["latitude"]
        assert fac_data["longitude"] == candidate["longitude"]
        assert fac_data["operational_status"] == "UNKNOWN"

    def test_evacuation_routing_to_osm_hospital(self):
        """Calculates an evacuation route to an OSM candidate using its exact coordinates."""
        disc_res = client.get(
            f"/emergency-facilities/nearby-hospitals?latitude=17.3970&longitude=78.4780&radius_km=5.0"
        )
        hospitals = disc_res.json().get("hospitals", [])
        assert len(hospitals) > 0
        target_hospital = hospitals[0]

        route_payload = {
            "origin": {"latitude": 17.3970, "longitude": 78.4780},
            "destination": {
                "latitude": target_hospital["latitude"],
                "longitude": target_hospital["longitude"]
            },
            "facility_id": target_hospital["facility_id"],
            "compute_alternatives": False
        }
        res = client.post("/evacuation-route", json=route_payload)
        assert res.status_code == 200
        route_data = res.json()
        assert route_data["route_status"] in ("ROUTE_AVAILABLE", "NO_SAFE_ROUTE")
        # Disclaimers must be present
        assert any("OpenStreetMap" in w for w in route_data.get("warnings", [])) or route_data.get("road_source") == "OpenStreetMap"

    def test_empty_search_radius(self):
        """Small search radius returns a clean empty candidate list without errors."""
        res = client.get(
            f"/emergency-facilities/nearby-hospitals?latitude={CENTRAL_HYD_LAT}&longitude={CENTRAL_HYD_LON}&radius_km=0.01&force_refresh=true"
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 0
        assert data["hospitals"] == []

    def test_nizampet_pragathi_nagar_2km_coverage(self):
        """Discovers genuine nearby OSM healthcare facilities within 2 km of Nizampet/Pragathi Nagar."""
        res = client.get(
            "/emergency-facilities/nearby-hospitals?latitude=17.5072&longitude=78.3897&radius_km=2.0&force_refresh=true"
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 5, f"Expected at least 5 hospitals within 2 km of 17.5072, 78.3897, got {data['total']}"
        assert len(data["hospitals"]) >= 5
        # Verify nearest facility is under 1.0 km
        assert data["hospitals"][0]["distance_km"] <= 1.0
        # Verify distance ordering
        distances = [h["distance_km"] for h in data["hospitals"]]
        assert distances == sorted(distances)
