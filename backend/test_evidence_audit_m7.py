"""
SafeMap AI — Milestone 7 Test Suite: Historical Flood Evidence Audit & Dataset QA
Validates:
- Event-level provenance structure, citation details, and evidence notes.
- Classification of measurements: OBSERVED vs SECONDARY_REPORTED vs ESTIMATED vs UNVERIFIED vs MODELLED.
- Nullification of unsupported discharge numbers (with audit trail preservation).
- Defensible confidence rating rules (downgrades of unearned HIGH/VERY_HIGH).
- Repeatable / idempotent curation pipeline and provenance survival.
- Safety invariants: Hyderabad MODEL_UNSUPPORTED guard and > 50 km distance guard.
- Existing routing, flood hazards, shelters, and emergency facility endpoints.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.data_importers.importer_base import (
    VALID_MEASUREMENT_TYPES,
    VALID_VERIFICATION_STATES,
    VALID_DATA_CLASSIFICATIONS,
)
from app.services.data_importers.curation_pipeline import SafeMapCurationPipeline
from evaluate_hyderabad_data_readiness import audit_local_data_readiness

client = TestClient(app)
BASE_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def curated_catalogue():
    catalogue_path = BASE_DIR / "data" / "curated" / "hyderabad_flood_event_catalogue.json"
    assert catalogue_path.exists(), f"Curated catalogue not found at {catalogue_path}"
    with open(catalogue_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def manifest_data():
    manifest_path = BASE_DIR / "data" / "data_manifest.json"
    assert manifest_path.exists(), f"Data manifest not found at {manifest_path}"
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestEventProvenanceAndAuditTrail:
    """Task 1 & Task 2: Verifies provenance metadata and audit trails across all 8 historical events."""

    def test_catalogue_contains_exactly_eight_distinct_events(self, curated_catalogue):
        assert len(curated_catalogue) == 8
        event_ids = [ev["event_id"] for ev in curated_catalogue]
        assert len(set(event_ids)) == 8, "Event IDs must be unique"
        for eid in event_ids:
            assert eid.startswith("HYD-EVT-")

    def test_all_events_have_required_provenance_structure(self, curated_catalogue):
        required_provenance_keys = {
            "source_title",
            "publisher",
            "direct_url",
            "citation_detail",
            "evidence_note",
            "measurement_classifications",
            "verification_status",
            "unresolved_issues",
        }
        for ev in curated_catalogue:
            assert "provenance" in ev, f"Missing provenance in {ev['event_id']}"
            prov = ev["provenance"]
            for key in required_provenance_keys:
                assert key in prov, f"Missing provenance key '{key}' in {ev['event_id']}"
                assert prov[key] is not None, f"Provenance key '{key}' cannot be null in {ev['event_id']}"

            # Verify direct_url starts with http
            assert prov["direct_url"].startswith("http"), f"Invalid direct_url in {ev['event_id']}"
            # Verify evidence note is substantive (> 20 chars)
            assert len(prov["evidence_note"]) > 20, f"Evidence note too short in {ev['event_id']}"

    def test_all_events_have_audit_trail(self, curated_catalogue):
        required_audit_keys = {
            "original_classification",
            "original_confidence",
            "corrected_classification",
            "corrected_confidence",
            "correction_rationale",
        }
        for ev in curated_catalogue:
            assert "audit_trail" in ev, f"Missing audit_trail in {ev['event_id']}"
            audit = ev["audit_trail"]
            for key in required_audit_keys:
                assert key in audit, f"Missing audit key '{key}' in {ev['event_id']}"
            assert len(audit["correction_rationale"]) > 15

    def test_all_events_marked_partially_verified(self, curated_catalogue):
        """No event can be marked FULLY VERIFIED because Hyderabad lacks continuous Musi River stream gauge telemetry."""
        for ev in curated_catalogue:
            assert ev["verification_state"] in VALID_VERIFICATION_STATES
            assert ev["verification_state"] == "PARTIALLY_VERIFIED"
            assert ev["provenance"]["verification_status"] == "PARTIALLY_VERIFIED"


class TestMeasurementClassificationsAndUnsupportedFields:
    """Task 3: Validates observation vs modelled vs estimated classifications and unsupported field nullification."""

    def test_rainfall_measurement_classifications(self, curated_catalogue):
        for ev in curated_catalogue:
            rf_type = ev["rainfall_measurement_type"]
            assert rf_type in VALID_MEASUREMENT_TYPES
            assert rf_type in {"OBSERVED", "SECONDARY_REPORTED"}
            assert ev["rainfall_unit"] == "mm"
            assert ev["max_24h_rainfall_mm"] is not None
            assert ev["max_24h_rainfall_mm"] > 0

        # Specific checks: 2016, 2020, 2021, 2023 had direct station/AWS telemetry
        direct_obs_events = {"HYD-EVT-2016-01", "HYD-EVT-2020-01", "HYD-EVT-2021-01", "HYD-EVT-2023-01"}
        for ev in curated_catalogue:
            if ev["event_id"] in direct_obs_events:
                assert ev["rainfall_measurement_type"] == "OBSERVED"
            else:
                assert ev["rainfall_measurement_type"] == "SECONDARY_REPORTED"

    def test_unsupported_river_discharges_are_nullified_and_preserved_in_audit_trail(self, curated_catalogue):
        """Events in 2000, 2016, 2021, 2023 were urban stormwater / lake breaches with NO stream gauge flow.
        Their discharge values must be null in the observation field, with prior numbers preserved in audit_trail."""
        unsupported_discharge_events = {
            "HYD-EVT-2000-01": 1250.0,
            "HYD-EVT-2016-01": 210.0,
            "HYD-EVT-2021-01": 95.0,
            "HYD-EVT-2023-01": 85.0,
        }
        for ev in curated_catalogue:
            if ev["event_id"] in unsupported_discharge_events:
                expected_orig = unsupported_discharge_events[ev["event_id"]]
                assert ev["peak_river_discharge_cumec"] is None, (
                    f"Discharge must be null for {ev['event_id']}"
                )
                assert ev["discharge_measurement_type"] == "UNVERIFIED"
                assert ev["audit_trail"]["original_reported_discharge_cumec"] == expected_orig
                assert "stripped" in ev["audit_trail"]["correction_rationale"].lower() or "unsupported" in ev["audit_trail"]["correction_rationale"].lower()

    def test_estimated_discharges_marked_estimated(self, curated_catalogue):
        """1908 (slope-area hydraulic post-hoc), 2008 (dam release), 2020 (dam release), 2022 (dam release)
        must NOT be marked OBSERVED; they are ESTIMATED."""
        estimated_discharge_events = {
            "HYD-EVT-1908-01": 12034.0,
            "HYD-EVT-2008-01": 480.0,
            "HYD-EVT-2020-01": 850.0,
            "HYD-EVT-2022-01": 226.5,
        }
        for ev in curated_catalogue:
            if ev["event_id"] in estimated_discharge_events:
                expected_val = estimated_discharge_events[ev["event_id"]]
                assert ev["peak_river_discharge_cumec"] == expected_val
                assert ev["discharge_measurement_type"] == "ESTIMATED"
                assert ev["discharge_measurement_type"] != "OBSERVED"

    def test_confidence_ratings_follow_defensible_evidence_rules(self, curated_catalogue):
        """Rules:
        - HIGH: Only granted if multiple corroborating primary telemetry sources exist (e.g. 2020: dual AWS + Bhuvan SAR).
        - VERY_HIGH: Disallowed across all records because Hyderabad lacks continuous in-stream gauge calibration.
        - LOW: Historical events where discharge/rainfall are secondary press reports or archived state ledgers.
        - MEDIUM: Standard historical events with documented institutional reports."""
        for ev in curated_catalogue:
            assert ev["confidence_level"] != "VERY_HIGH", f"VERY_HIGH is indefensible for {ev['event_id']}"

        # 2020 was downgraded from VERY_HIGH to HIGH
        ev_2020 = next(e for e in curated_catalogue if e["event_id"] == "HYD-EVT-2020-01")
        assert ev_2020["confidence_level"] == "HIGH"
        assert ev_2020["audit_trail"]["original_confidence"] == "VERY_HIGH"

        # 2008 was downgraded from HIGH to LOW
        ev_2008 = next(e for e in curated_catalogue if e["event_id"] == "HYD-EVT-2008-01")
        assert ev_2008["confidence_level"] == "LOW"
        assert ev_2008["audit_trail"]["original_confidence"] == "HIGH"


class TestIdempotencyAndPipelineIntegrity:
    """Task 5: Ensures curation pipeline is idempotent and provenance survives repeatable imports."""

    def test_pipeline_is_idempotent(self):
        pipeline = SafeMapCurationPipeline(base_dir=BASE_DIR)
        run1 = pipeline.run()
        assert run1["status"] == "COMPLETED"

        run2 = pipeline.run()
        assert run2["status"] == "COMPLETED"

        # Check raw checksums and imported counts match between executions
        assert run1["importer_results"]["flood_events"]["raw_sha256"] == run2["importer_results"]["flood_events"]["raw_sha256"]
        assert run1["importer_results"]["flood_events"]["records_imported"] == run2["importer_results"]["flood_events"]["records_imported"] == 8
        assert run1["importer_results"]["des_rainfall"]["raw_sha256"] == run2["importer_results"]["des_rainfall"]["raw_sha256"]
        assert run1["importer_results"]["des_rainfall"]["curated_sha256"] == run2["importer_results"]["des_rainfall"]["curated_sha256"]

    def test_manifest_contains_milestone_7_verification_metrics(self, manifest_data):
        assert manifest_data["manifest_version"] in ["1.1.0", "1.2.0"]
        assert any(m in manifest_data["milestone"] for m in ["Milestone 7", "Milestone 8"])
        metrics = manifest_data["summary_metrics"]
        assert metrics["historical_flood_events_catalogued"] == 8
        assert metrics["fully_verified_events"] == 0
        assert metrics["partially_verified_events"] == 8
        assert metrics["unverified_events"] == 0


class TestStatisticalAuditAndSafetyGuards:
    """Task 4: Confirms statistical conclusions, 120 mm heuristic disclaimer, and 50 km coverage guard."""

    def test_data_readiness_audit_statistical_conclusions(self):
        audit = audit_local_data_readiness(base_dir=BASE_DIR)
        assert audit["readiness_determination"]["status"] == "INSUFFICIENT_LOCAL_DATA"
        assert audit["readiness_determination"]["suitable_for_training"] is False
        assert audit["readiness_determination"]["suitable_for_validation"] is False

        # Statistical power
        power_audit = audit["statistical_power_audit"]
        assert power_audit["sample_size_n"] == 8
        assert "< 0.12" in power_audit["statistical_power_estimate"]
        assert power_audit["wilson_95ci_width_on_n8"] > 0.50

        # Baseline LOEO heuristic
        loeo = audit["baseline_evaluation_loeo"]
        assert "Exploratory Heuristic" in loeo["method"]
        assert "exploratory retrospective heuristic" in loeo["heuristic_disclaimer"].lower()
        assert "UNDEFINED" in loeo["specificity"]
        assert "cannot be computed" in loeo["specificity_note"].lower()

    def test_hyderabad_remains_model_unsupported(self):
        payload = {
            "latitude": 17.3850,
            "longitude": 78.4867,
            "target_date": "2024-08-15"
        }
        resp = client.post("/predict/integrated", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["coverage_status"] == "MODEL_UNSUPPORTED"
        assert data["prediction_available"] is False
        assert data["gauge_distance_km"] > 50.0

    def test_existing_endpoints_preserved(self):
        # Flood hazards
        haz_resp = client.get("/flood-hazards")
        assert haz_resp.status_code == 200
        assert len(haz_resp.json()["hazards"]) >= 5

        # Shelters
        sh_resp = client.get("/shelters")
        assert sh_resp.status_code == 200
        assert len(sh_resp.json()["shelters"]) >= 11

        # Emergency facilities
        ef_resp = client.get("/emergency-facilities")
        assert ef_resp.status_code == 200
        ef_data = ef_resp.json()
        assert len(ef_data["facilities"]) >= 15
        assert ef_data["total"] >= 15
