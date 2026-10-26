"""
SafeMap AI — Milestone 8 Test Suite: Institutional Data Acquisition & Intake Engine
Validates:
- Validation engine for CSV, JSON, GeoJSON institutional payloads.
- Coordinate range validation and Hyderabad regional bounding box tagging.
- ISO 8601 timestamp parsing and year range bounds.
- Unit normalizations (cm -> mm, cusec -> m^3/s, ft -> m) with original value preservation.
- Rejection of invalid units, timestamps, coordinates, and station IDs with actionable error messages.
- Explicit null handling (sentinels -999, NA, NULL, NaN tracked as None; no zero-filling).
- Duplicate row detection within batches.
- Idempotent repeated imports preserving raw files, curated JSON, and audit ledgers.
- 5-state negative-control taxonomy and strict dual-source evidence rules.
- Operational safeguards: Hyderabad MODEL_UNSUPPORTED guard and 50 km distance guard.
- Existing routing, flood hazard, shelter, and emergency facility endpoints.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.data_importers.institutional_intake import (
    InstitutionalIntakeEngine,
    HYD_BBOX,
    UNIT_NORMALIZATION,
    SENTINEL_NULLS,
)
from app.services.data_importers.negative_control_manager import (
    NegativeControlClassification,
    NegativeControlEvidenceRule,
    get_negative_control_requirements_summary,
)

client = TestClient(app)
BASE_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def intake_engine(tmp_path):
    """Creates an isolated InstitutionalIntakeEngine using a temporary directory."""
    return InstitutionalIntakeEngine(base_dir=tmp_path)


class TestInstitutionalIntakeValidationEngine:
    """Task 3: Tests validation contracts, coordinate checks, timestamp checks, and unit conversions."""

    def test_valid_csv_with_unit_normalizations(self, intake_engine):
        csv_data = (
            "timestamp,station_id,latitude,longitude,rainfall,rainfall_unit,discharge,discharge_unit\n"
            "2020-10-14T08:00:00Z,TSDPS-GHATKESAR,17.442,78.682,320.0,mm,850.0,m^3/s\n"
            "2020-10-14T09:00:00Z,TSDPS-BEGUMPET,17.442,78.475,19.18,cm,12000.0,cusec\n"
            "2020-10-14T10:00:00Z,TSDPS-SHAIKPET,17.410,78.390,2.5,inch,500.0,cumec\n"
        )
        metadata = {
            "provider": "TSDPS",
            "source_reference": "BULLETIN-2020-10-14",
            "retrieval_date": "2026-10-25T00:00:00Z",
            "data_owner": "TSDPS Planning Dept",
            "usage_restrictions": "RESTRICTED_RESEARCH_ONLY",
            "measurement_classification": "OBSERVED",
        }

        res = intake_engine.validate_content(csv_data, "tsps_test.csv", metadata)
        assert res["valid"] is True
        assert res["total_records_processed"] == 3
        assert res["valid_records_count"] == 3
        assert len(res["errors"]) == 0

        recs = res["normalized_records"]
        # Row 1: mm -> mm (factor 1.0)
        assert recs[0]["rainfall"]["original_value"] == 320.0
        assert recs[0]["rainfall"]["normalized_value_mm"] == 320.0
        assert recs[0]["rainfall"]["original_unit"] == "mm"
        assert recs[0]["discharge"]["normalized_value_cumec"] == 850.0
        assert recs[0]["in_hyderabad_region"] is True

        # Row 2: cm -> mm (factor 10.0: 19.18 cm -> 191.8 mm)
        assert recs[1]["rainfall"]["original_value"] == 19.18
        assert recs[1]["rainfall"]["original_unit"] == "cm"
        assert recs[1]["rainfall"]["normalized_value_mm"] == 191.8
        # Row 2: cusec -> m^3/s (12,000 cusecs * 0.0283168 ≈ 339.802 m^3/s)
        assert recs[1]["discharge"]["original_unit"] == "cusec"
        assert 339.0 < recs[1]["discharge"]["normalized_value_cumec"] < 341.0

        # Row 3: inch -> mm (factor 25.4: 2.5 inch -> 63.5 mm)
        assert recs[2]["rainfall"]["original_value"] == 2.5
        assert recs[2]["rainfall"]["normalized_value_mm"] == 63.5

    def test_rejection_of_invalid_coordinates(self, intake_engine):
        bad_csv = (
            "timestamp,station_id,latitude,longitude,rainfall\n"
            "2020-10-14T08:00:00Z,STN-01,195.4,78.475,50.0\n"  # Lat > 90
            "2020-10-14T09:00:00Z,STN-02,17.442,-250.0,30.0\n"  # Lon < -180
        )
        metadata = {
            "provider": "TEST",
            "source_reference": "REF-001",
            "retrieval_date": "2026-10-25T00:00:00Z",
        }

        res = intake_engine.validate_content(bad_csv, "bad_coords.csv", metadata)
        assert res["valid"] is False
        assert len(res["errors"]) >= 2
        err_fields = [e["field"] for e in res["errors"]]
        assert "latitude" in err_fields
        assert "longitude" in err_fields
        assert any("between -90.0 and 90.0" in e["error"] for e in res["errors"])

    def test_rejection_of_invalid_timestamps_and_years(self, intake_engine):
        bad_csv = (
            "timestamp,station_id,latitude,longitude,rainfall\n"
            "NOT_A_DATE,STN-01,17.442,78.475,50.0\n"
            "1845-05-12,STN-02,17.442,78.475,50.0\n"  # Year < 1900
        )
        metadata = {
            "provider": "TEST",
            "source_reference": "REF-002",
            "retrieval_date": "2026-10-25T00:00:00Z",
        }

        res = intake_engine.validate_content(bad_csv, "bad_dates.csv", metadata)
        assert res["valid"] is False
        assert len(res["errors"]) >= 2
        assert any("Invalid timestamp" in e["error"] for e in res["errors"])
        assert any("outside allowable range" in e["error"] for e in res["errors"])

    def test_rejection_of_unsupported_units_and_negative_values(self, intake_engine):
        bad_csv = (
            "timestamp,station_id,latitude,longitude,rainfall,rainfall_unit\n"
            "2020-10-14T08:00:00Z,STN-01,17.442,78.475,-25.0,mm\n"  # Negative rainfall
            "2020-10-14T09:00:00Z,STN-02,17.442,78.475,50.0,gallons\n"  # Unsupported unit
        )
        metadata = {
            "provider": "TEST",
            "source_reference": "REF-003",
            "retrieval_date": "2026-10-25T00:00:00Z",
        }

        res = intake_engine.validate_content(bad_csv, "bad_units.csv", metadata)
        assert res["valid"] is False
        assert any("negative" in e["error"].lower() for e in res["errors"])
        assert any("unsupported rainfall unit" in e["error"].lower() for e in res["errors"])

    def test_missing_value_sentinels_are_not_zero_filled(self, intake_engine):
        csv_with_sentinels = (
            "timestamp,station_id,latitude,longitude,rainfall,discharge\n"
            "2020-10-14T08:00:00Z,STN-01,17.442,78.475,-999,NA\n"
            "2020-10-14T09:00:00Z,STN-02,17.442,78.475,,NULL\n"
        )
        metadata = {
            "provider": "TEST",
            "source_reference": "REF-004",
            "retrieval_date": "2026-10-25T00:00:00Z",
        }

        res = intake_engine.validate_content(csv_with_sentinels, "sentinels.csv", metadata)
        assert res["valid"] is True
        recs = res["normalized_records"]
        assert recs[0]["rainfall"] is None, "-999 sentinel must be converted to None, not 0.0"
        assert recs[0]["discharge"] is None, "NA sentinel must be converted to None"
        assert recs[1]["rainfall"] is None, "Empty string must be converted to None"
        assert recs[1]["discharge"] is None, "NULL sentinel must be converted to None"

    def test_duplicate_row_detection(self, intake_engine):
        dup_csv = (
            "timestamp,station_id,latitude,longitude,rainfall\n"
            "2020-10-14T08:00:00Z,TSDPS-001,17.442,78.475,50.0\n"
            "2020-10-14T08:00:00Z,TSDPS-001,17.442,78.475,50.0\n"  # Duplicate timestamp + station
        )
        metadata = {
            "provider": "TEST",
            "source_reference": "REF-DUP",
            "retrieval_date": "2026-10-25T00:00:00Z",
        }

        res = intake_engine.validate_content(dup_csv, "dups.csv", metadata)
        assert res["valid"] is False
        assert any("duplicate record" in e["error"].lower() for e in res["errors"])

    def test_valid_geojson_intake(self, intake_engine):
        geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [78.475, 17.442]},
                    "properties": {
                        "timestamp": "2020-10-14T08:00:00Z",
                        "station_id": "GEO-AWS-01",
                        "rainfall": 120.0,
                        "rainfall_unit": "mm",
                    },
                }
            ],
        }
        metadata = {
            "provider": "ISRO_NRSC",
            "source_reference": "GEOJSON-WATER-EXTENT",
            "retrieval_date": "2026-10-25T00:00:00Z",
        }

        res = intake_engine.validate_content(json.dumps(geojson_data), "points.geojson", metadata)
        assert res["valid"] is True
        assert res["valid_records_count"] == 1
        rec = res["normalized_records"][0]
        assert rec["station_id"] == "GEO-AWS-01"
        assert rec["latitude"] == 17.442
        assert rec["longitude"] == 78.475
        assert rec["rainfall"]["normalized_value_mm"] == 120.0


class TestIdempotencyAndCommitWorkflow:
    """Task 3: Validates commit storage and cryptographic idempotency."""

    def test_idempotent_commit_preserves_ledger(self, intake_engine):
        csv_content = (
            "timestamp,station_id,latitude,longitude,rainfall\n"
            "2020-10-14T08:00:00Z,TSDPS-001,17.442,78.475,85.0\n"
        )
        metadata = {
            "provider": "TSDPS",
            "source_reference": "REQUISITION-2020-10-14",
            "retrieval_date": "2026-10-25T00:00:00Z",
            "data_owner": "Telangana State Development Planning Society",
            "usage_restrictions": "RESTRICTED_RESEARCH_ONLY",
        }

        # 1. First Commit
        commit1 = intake_engine.commit_batch(csv_content, "sample.csv", metadata)
        assert commit1["status"] == "SUCCESS"
        assert commit1["records_stored"] == 1
        raw_sha256 = commit1["file_checksum_sha256"]

        # Verify ledger has 1 entry
        ledger1 = intake_engine.get_intake_log()
        assert len(ledger1) == 1
        assert ledger1[0]["file_checksum_sha256"] == raw_sha256

        # 2. Second Commit with identical content (Idempotency test)
        commit2 = intake_engine.commit_batch(csv_content, "sample.csv", metadata)
        assert commit2["status"] == "IDEMPOTENT_SKIPPED"
        assert commit2["file_checksum_sha256"] == raw_sha256

        # Verify ledger still has exactly 1 entry (no duplicates created)
        ledger2 = intake_engine.get_intake_log()
        assert len(ledger2) == 1


class TestNegativeControlClassificationRules:
    """Task 4: Enforces the 5-state negative-control taxonomy and dual-source evidence rules."""

    def test_missing_telemetry_classified_missing(self):
        res = NegativeControlEvidenceRule.classify_epoch(
            date_iso="2022-08-15",
            rainfall_mm=None,
            has_sensor_telemetry=False,
        )
        assert res["classification"] == NegativeControlClassification.MISSING_OBSERVATION.value
        assert res["is_evaluable_metric"] is False

    def test_modelled_reanalysis_classified_modelled(self):
        res = NegativeControlEvidenceRule.classify_epoch(
            date_iso="2020-10-14",
            rainfall_mm=180.0,
            is_model_output_only=True,
            evidence_note="Copernicus GloFAS Model Simulation",
        )
        assert res["classification"] == NegativeControlClassification.MODELLED_ESTIMATE.value
        assert res["is_evaluable_metric"] is False

    def test_confirmed_flood_classification(self):
        res = NegativeControlEvidenceRule.classify_epoch(
            date_iso="2020-10-14",
            rainfall_mm=191.8,
            drf_dewatering_count=48,
            causeway_submerged=True,
            municipal_log_reference="GHMC DRF Flood Incident Register #1024",
        )
        assert res["classification"] == NegativeControlClassification.CONFIRMED_FLOOD.value
        assert res["is_evaluable_metric"] is True
        assert res["ground_truth_label"] == 1

    def test_documented_non_flood_rule_a_dry_day(self):
        res = NegativeControlEvidenceRule.classify_epoch(
            date_iso="2022-01-15",
            rainfall_mm=0.0,
            drf_dewatering_count=0,
            causeway_submerged=False,
            municipal_log_reference="GHMC Daily Operations Log Jan 15 2022 (Zero Incidents)",
        )
        assert res["classification"] == NegativeControlClassification.DOCUMENTED_NON_FLOOD.value
        assert res["is_evaluable_metric"] is True
        assert res["ground_truth_label"] == 0
        assert "Rule A" in res["rule_applied"]

    def test_documented_non_flood_rule_b_wet_weather(self):
        # 45 mm rain with explicit municipal log confirming zero deployments and open traffic corridors
        res = NegativeControlEvidenceRule.classify_epoch(
            date_iso="2022-09-08",
            rainfall_mm=45.0,
            drf_dewatering_count=0,
            causeway_submerged=False,
            municipal_log_reference="GHMC DRF Daily Log Sep 8 2022 (Normal Flow / Zero Inundation)",
        )
        assert res["classification"] == NegativeControlClassification.DOCUMENTED_NON_FLOOD.value
        assert res["is_evaluable_metric"] is True
        assert res["ground_truth_label"] == 0
        assert "Rule B" in res["rule_applied"]

    def test_cardinal_rule_unverified_rainy_day_remains_unknown(self):
        # 65 mm rain, but NO municipal confirmation log exists.
        # Passive absence of flood notice is NOT proof of no flooding!
        res = NegativeControlEvidenceRule.classify_epoch(
            date_iso="2022-08-20",
            rainfall_mm=65.0,
            municipal_log_reference=None,  # No log
        )
        assert res["classification"] == NegativeControlClassification.UNKNOWN_OR_UNCLASSIFIED.value
        assert res["is_evaluable_metric"] is False
        assert res["ground_truth_label"] is None
        assert "cannot be treated as a true negative" in res["rationale"]


class TestMilestone8ApiEndpoints:
    """Verifies FastAPI endpoints for intake dry-run validation, sources inventory, and negative controls."""

    def test_api_intake_validation_endpoint_success(self):
        payload = {
            "filename": "api_test.csv",
            "content": (
                "timestamp,station_id,latitude,longitude,rainfall,rainfall_unit\n"
                "2020-10-14T08:00:00Z,AWS-001,17.442,78.475,150.0,mm\n"
            ),
            "metadata": {
                "provider": "TSDPS",
                "source_reference": "API-TEST-REF",
                "retrieval_date": "2026-10-25T00:00:00Z",
            },
        }
        resp = client.post("/data-curation/intake/validate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["valid_records_count"] == 1
        assert len(data["sample_records"]) == 1

    def test_api_intake_validation_endpoint_rejection(self):
        payload = {
            "filename": "api_bad.csv",
            "content": (
                "timestamp,station_id,latitude,longitude,rainfall\n"
                "BAD_TIME,AWS-001,195.4,78.475,50.0\n"
            ),
            "metadata": {
                "provider": "TSDPS",
                "source_reference": "API-TEST-REF",
                "retrieval_date": "2026-10-25T00:00:00Z",
            },
        }
        resp = client.post("/data-curation/intake/validate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert len(data["errors"]) >= 2

    def test_api_sources_inventory_endpoint(self):
        resp = client.get("/data-curation/intake/sources")
        assert resp.status_code == 200
        data = resp.json()
        categories = data["source_categories"]
        assert len(categories["downloaded_and_verified"]) >= 5
        assert len(categories["draft_data_requests"]) == 4
        assert len(data["unsupported_measurements_tracker"]) == 4

    def test_api_negative_controls_summary_endpoint(self):
        resp = client.get("/data-curation/negative-controls/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["framework_version"] == "1.0.0"
        assert len(data["supported_states"]) == 5
        assert "Synthetic negative observations are strictly prohibited" in data["anti_fabrication_rule"]
        assert data["sample_size_targets"]["current_hyd_documented_non_floods"] == 0


class TestSafetyGuardsPreserved:
    """Task 6: Confirms 50 km coverage guard and existing emergency services remain intact."""

    def test_hyderabad_remains_model_unsupported(self):
        payload = {
            "latitude": 17.3850,
            "longitude": 78.4867,
            "target_date": "2024-08-15",
        }
        resp = client.post("/predict/integrated", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["coverage_status"] == "MODEL_UNSUPPORTED"
        assert data["prediction_available"] is False
        assert data["gauge_distance_km"] > 50.0

    def test_existing_endpoints_preserved(self):
        # Hazards
        haz_resp = client.get("/flood-hazards")
        assert haz_resp.status_code == 200
        assert len(haz_resp.json()["hazards"]) >= 5

        # Shelters
        sh_resp = client.get("/shelters")
        assert sh_resp.status_code == 200
        assert len(sh_resp.json()["shelters"]) >= 11

        # Facilities
        ef_resp = client.get("/emergency-facilities")
        assert ef_resp.status_code == 200
        assert len(ef_resp.json()["facilities"]) >= 15
