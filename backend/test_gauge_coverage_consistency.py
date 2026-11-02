"""
SafeMap AI — Safety Fix 9: Gauge Coverage Consistency and Invariant Suite

Automated regression test suite verifying:
1. Exact gauge catalog contents and absence of fabricated stations (e.g. "Station 405").
2. Exact Haversine distance from Hyderabad (71.77 km to INDOFLOODS-gauge-916).
3. Cross-endpoint consistency between:
   - GET /risk-map
   - POST /predict/integrated
   - GET /gauges/nearest
4. Universal enforcement of MODEL_UNSUPPORTED across all Hyderabad preset coordinates.
5. Strict adherence to the 50.0 km model coverage boundary safeguard without prediction fabrication.
"""

from datetime import date
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.gauge_reference import GaugeReferenceService
from evaluate_hyderabad_data_readiness import audit_local_data_readiness

client = TestClient(app)
BASE_DIR = Path(__file__).resolve().parent.parent


class TestGaugeCatalogIntegrity:
    """Verifies physical dataset catalog records and nearest gauge calculations."""

    def test_gauge_catalog_has_no_station_405_and_contains_gauge_916(self):
        service = GaugeReferenceService()
        assert service.merged_df is not None
        assert not service.merged_df.empty
        assert len(service.merged_df) == 155

        gauge_ids = service.merged_df['GaugeID'].astype(str).tolist()
        assert "INDOFLOODS-gauge-916" in gauge_ids

        # Explicit proof: Station 405 does not exist in the calibrated dataset
        stations_405 = [gid for gid in gauge_ids if "405" in gid]
        assert len(stations_405) == 0, f"Found unexpected 405 station(s): {stations_405}"

    def test_nearest_gauge_to_hyderabad_center_is_gauge_916_at_71_77_km(self):
        service = GaugeReferenceService()
        hyd_lat, hyd_lon = 17.3850, 78.4867

        distances = service.merged_df.apply(
            lambda r: (str(r['GaugeID']), service._haversine(hyd_lat, hyd_lon, float(r['Latitude']), float(r['Longitude']))),
            axis=1
        )
        sorted_gauges = sorted(distances, key=lambda x: x[1])
        nearest_id, nearest_dist = sorted_gauges[0]

        assert nearest_id == "INDOFLOODS-gauge-916"
        assert round(nearest_dist, 2) == 71.77
        assert 71.70 <= nearest_dist <= 71.85

        # Check second nearest to prove no station is at ~123.6 km
        second_id, second_dist = sorted_gauges[1]
        assert second_id == "INDOFLOODS-gauge-939"
        assert round(second_dist, 2) == 109.07

        # Check that no gauge exists in the 120-125 km bracket
        gauges_at_123km = [g for g in sorted_gauges if 120.0 <= g[1] <= 125.0]
        assert len(gauges_at_123km) == 0, f"Unexpected gauge near 123 km: {gauges_at_123km}"


class TestEndpointCoverageConsistency:
    """Verifies that all three gauge-evaluating API endpoints return identical coverage metrics."""

    def test_hyderabad_center_across_all_endpoints(self):
        lat, lon = 17.3850, 78.4867

        # 1. GET /risk-map
        res_risk = client.get(f"/risk-map?latitude={lat}&longitude={lon}")
        assert res_risk.status_code == 200
        d_risk = res_risk.json()

        # 2. POST /predict/integrated
        res_pred = client.post("/predict/integrated", json={
            "latitude": lat,
            "longitude": lon,
            "target_date": "2026-10-27"
        })
        assert res_pred.status_code == 200
        d_pred = res_pred.json()

        # 3. GET /gauges/nearest
        res_gauge = client.get(f"/gauges/nearest?latitude={lat}&longitude={lon}")
        assert res_gauge.status_code == 200
        d_gauge = res_gauge.json()

        # Consistent Reference Gauge ID
        assert d_risk["gauge_id"] == "INDOFLOODS-gauge-916"
        assert d_pred["nearest_gauge"] == "INDOFLOODS-gauge-916"
        assert d_pred["coverage"]["reference_gauge"] == "INDOFLOODS-gauge-916"
        assert d_gauge["reference_gauge"]["gauge_id"] == "INDOFLOODS-gauge-916"

        # Consistent Distance (71.77 km)
        assert d_risk["distance_km"] == 71.77
        assert d_risk["nearest_gauge_distance_km"] == 71.77
        assert d_pred["gauge_distance_km"] == 71.77
        assert d_pred["coverage"]["distance_km"] == 71.77
        assert round(d_gauge["distance_km"], 2) == 71.77

        # Consistent Coverage Status
        assert d_risk["coverage_status"] == "MODEL_UNSUPPORTED"
        assert d_pred["coverage_status"] == "MODEL_UNSUPPORTED"
        assert d_pred["coverage"]["status"] == "MODEL_UNSUPPORTED"
        assert d_gauge["within_model_coverage"] is False

        # Consistent Prediction Suppression (Truth-in-Data)
        assert d_risk["prediction_available"] is False
        assert d_pred["prediction_available"] is False
        assert d_risk["risk_level"] is None
        assert d_pred["risk_level"] is None
        assert d_risk["predicted_class"] is None
        assert d_pred["prediction"] is None

        # Consistent 50.0 km Threshold Enforcement
        assert d_risk["coverage_limit_km"] == 50.0
        assert d_pred["maximum_supported_distance_km"] == 50.0
        assert d_pred["coverage"]["maximum_distance_km"] == 50.0
        assert d_gauge["max_allowed_distance_km"] == 50.0

    def test_hyderabad_presets_are_all_unsupported(self):
        """All supported municipal test coordinates in Hyderabad must be rejected by model coverage."""
        presets = [
            ("Charminar", 17.3616, 78.4747),
            ("Banjara Hills", 17.4156, 78.4350),
            ("Secunderabad", 17.4399, 78.4983),
            ("Hitec City", 17.4474, 78.3762),
            ("Khairatabad", 17.4116, 78.4593),
            ("Musi River Causeway", 17.3820, 78.4910),
        ]

        for name, lat, lon in presets:
            res_risk = client.get(f"/risk-map?latitude={lat}&longitude={lon}")
            assert res_risk.status_code == 200
            data = res_risk.json()

            assert data["coverage_status"] == "MODEL_UNSUPPORTED", f"{name} should be MODEL_UNSUPPORTED"
            assert data["prediction_available"] is False, f"{name} should not manufacture prediction"
            assert data["risk_level"] is None
            assert data["distance_km"] > 50.0
            assert data["gauge_id"] == "INDOFLOODS-gauge-916"

    def test_supported_location_consistency(self):
        """Supported coordinates within 50km of an INDOFLOODS gauge must agree on MODEL_SUPPORTED."""
        # Location near INDOFLOODS-gauge-394 (lat=12.18, lon=77.73)
        lat, lon = 12.18, 77.73

        res_risk = client.get(f"/risk-map?latitude={lat}&longitude={lon}")
        assert res_risk.status_code == 200
        d_risk = res_risk.json()

        res_pred = client.post("/predict/integrated", json={
            "latitude": lat,
            "longitude": lon,
            "target_date": "2026-10-27"
        })
        assert res_pred.status_code == 200
        d_pred = res_pred.json()

        assert d_risk["coverage_status"] == "MODEL_SUPPORTED"
        assert d_pred["coverage_status"] == "MODEL_SUPPORTED"
        assert d_risk["prediction_available"] is True
        assert d_pred["prediction_available"] is True
        assert d_risk["distance_km"] < 50.0
        assert d_pred["gauge_distance_km"] < 50.0


class TestScientificReadinessAuditAgreement:
    """Verifies that the standalone scientific audit report agrees with the live APIs."""

    def test_audit_agrees_with_api_contracts(self):
        audit = audit_local_data_readiness(base_dir=BASE_DIR)
        nearest = audit["nearest_indofloods_gauge"]

        assert nearest["gauge_id"] == "INDOFLOODS-gauge-916"
        assert nearest["distance_km"] == 71.77
        assert nearest["is_within_50km_guard"] is False
        assert "Godavari" in nearest["hydrological_basin"]
        assert "Musi" in nearest["hydrological_basin"]

    def test_assistant_safety_explanation_agrees(self):
        res = client.post("/assistant/query", json={"message": "Explain MODEL_UNSUPPORTED and gauge coverage"})
        assert res.status_code == 200
        reply = res.json()["reply"]

        assert "50.0 km" in reply or "50 km" in reply
        assert "71.8 km" in reply or "gauge-916" in reply
        assert "Manjra" in reply

