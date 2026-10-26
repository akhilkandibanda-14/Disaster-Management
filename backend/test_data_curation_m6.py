"""
Comprehensive test suite for SafeMap AI Milestone 6:
Local Flood Data Acquisition, Dataset Curation, Provenance Manifest,
and Model Readiness Safety Guards.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.data_importers.bhuvan_inundation_importer import BhuvanInundationImporter
from app.services.data_importers.curation_pipeline import SafeMapCurationPipeline
from app.services.data_importers.des_rainfall_importer import DESRainfallImporter
from app.services.data_importers.era5_weather_importer import ERA5WeatherImporter
from app.services.data_importers.flood_event_catalogue_importer import FloodEventCatalogueImporter
from app.services.data_importers.glofas_discharge_importer import GloFASDischargeImporter
from app.services.data_importers.hazards_geojson_importer import HazardsGeoJsonImporter
from app.services.data_importers.importer_base import (
    VALID_DATA_CLASSIFICATIONS,
    compute_sha256,
    normalize_iso_timestamp,
    validate_coordinates,
    validate_data_classification,
    validate_geojson_geometry,
)
from evaluate_hyderabad_data_readiness import audit_local_data_readiness

client = TestClient(app)
BASE_DIR = Path(__file__).resolve().parent.parent


class TestImporterUtilities:
    """Tests core normalization, hashing, coordinate validation, and geometry guards."""

    def test_compute_sha256_nonexistent_and_real(self, tmp_path):
        assert compute_sha256(tmp_path / "nonexistent.txt") == ""
        test_file = tmp_path / "sample.txt"
        test_file.write_text("SafeMap AI Integrity Test", encoding="utf-8")
        h1 = compute_sha256(test_file)
        h2 = compute_sha256(test_file)
        assert len(h1) == 64
        assert h1 == h2

    def test_normalize_iso_timestamp_varied_formats(self):
        assert normalize_iso_timestamp("2020") == "2020-01-01T00:00:00Z"
        assert normalize_iso_timestamp("2020-10-14") == "2020-10-14T00:00:00Z"
        assert normalize_iso_timestamp("2020-10-14T06:30:00Z") == "2020-10-14T06:30:00Z"
        assert normalize_iso_timestamp(None) is None
        assert normalize_iso_timestamp("nan") is None
        assert normalize_iso_timestamp("   ") is None

    def test_validate_coordinates(self):
        # Valid WGS84 coordinates
        ok, lat, lon, err = validate_coordinates(17.385, 78.4867)
        assert ok is True
        assert lat == 17.385
        assert lon == 78.4867
        assert err == ""

        # Out-of-bounds latitude
        ok, _, _, err = validate_coordinates(95.0, 78.0)
        assert ok is False
        assert "Latitude" in err

        # Out-of-bounds longitude
        ok, _, _, err = validate_coordinates(17.0, -190.0)
        assert ok is False
        assert "Longitude" in err

        # Non-numeric inputs
        ok, _, _, err = validate_coordinates("invalid", "coords")
        assert ok is False
        assert "Non-numeric" in err

        # Missing values
        ok, _, _, err = validate_coordinates(None, 78.0)
        assert ok is False
        assert "Missing" in err

    def test_validate_data_classification(self):
        for valid in VALID_DATA_CLASSIFICATIONS:
            ok, norm = validate_data_classification(valid.lower())
            assert ok is True
            assert norm == valid

        ok, err = validate_data_classification("INVALID_CUSTOM_TYPE")
        assert ok is False
        assert "Invalid classification" in err

        ok, err = validate_data_classification(None)
        assert ok is False
        assert "Missing" in err

    def test_validate_geojson_geometry(self):
        # Valid closed polygon
        valid_poly = {
            "type": "Polygon",
            "coordinates": [
                [[78.4, 17.3], [78.5, 17.3], [78.5, 17.4], [78.4, 17.4], [78.4, 17.3]]
            ]
        }
        ok, err = validate_geojson_geometry(valid_poly)
        assert ok is True
        assert err == ""

        # Unclosed ring
        unclosed = {
            "type": "Polygon",
            "coordinates": [
                [[78.4, 17.3], [78.5, 17.3], [78.5, 17.4], [78.4, 17.4]]
            ]
        }
        ok, err = validate_geojson_geometry(unclosed)
        assert ok is False
        assert "not closed" in err

        # Non-dictionary
        ok, err = validate_geojson_geometry("invalid_geom")
        assert ok is False


class TestReproducibleImporters:
    """Tests each individual dataset importer against raw data files and malformed scenarios."""

    def test_des_rainfall_importer(self):
        importer = DESRainfallImporter()
        res = importer.import_and_curate()
        assert res["status"] == "SUCCESS"
        assert res["records_imported"] >= 19
        assert res["duplicates_skipped"] == 0
        assert res["malformed_skipped"] == 0
        assert "1970" in res["year_range"]
        assert "2023" in res["year_range"]
        assert len(res["raw_sha256"]) == 64
        assert len(res["curated_sha256"]) == 64

    def test_flood_event_catalogue_importer(self):
        importer = FloodEventCatalogueImporter()
        res = importer.import_and_curate()
        assert res["status"] == "SUCCESS"
        assert res["records_imported"] == 8
        assert res["duplicates_skipped"] == 0
        assert res["malformed_skipped"] == 0
        assert "1908" in res["date_range"]
        assert "2023" in res["date_range"]

        # Verify curated JSON contents
        curated_path = Path(res["curated_json"])
        with open(curated_path, "r", encoding="utf-8") as f:
            events = json.load(f)
        assert len(events) == 8
        for ev in events:
            assert ev["event_id"].startswith("HYD-EVT-")
            assert ev["data_classification"] in VALID_DATA_CLASSIFICATIONS
            assert ev["confidence_level"] in {"LOW", "MEDIUM", "HIGH", "VERY_HIGH"}
            assert "Z" in ev["start_date_iso"]
            assert ev["rainfall_unit"] == "mm"
            assert ev["discharge_unit"] == "m^3/s"

    def test_importer_malformed_and_duplicate_handling(self, tmp_path):
        # Create a raw JSON with 1 valid, 1 duplicate, and 1 malformed record
        bad_raw = tmp_path / "bad_floods.json"
        sample_data = [
            {
                "event_id": "HYD-EVT-TEST-01",
                "start_date": "2020-10-14",
                "flood_type": "TEST",
                "description": "Valid event",
                "data_classification": "OBSERVATION",
                "max_24h_rainfall_mm": 100.0,
            },
            {
                "event_id": "HYD-EVT-TEST-01",  # Duplicate ID
                "start_date": "2020-10-14",
                "flood_type": "TEST",
                "description": "Duplicate event",
                "data_classification": "OBSERVATION",
            },
            {
                "event_id": "HYD-EVT-TEST-02",
                "start_date": "INVALID_DATE",  # Malformed date
                "flood_type": "TEST",
                "description": "Malformed event",
                "data_classification": "OBSERVATION",
            },
            {
                "event_id": "HYD-EVT-TEST-03",
                "start_date": "2021-05-01",
                "flood_type": "TEST",
                "description": "Negative rain",
                "max_24h_rainfall_mm": -50.0,  # Negative rainfall
                "data_classification": "OBSERVATION",
            }
        ]
        bad_raw.write_text(json.dumps(sample_data), encoding="utf-8")

        curated_json = tmp_path / "curated_test.json"
        curated_csv = tmp_path / "curated_test.csv"
        importer = FloodEventCatalogueImporter(
            raw_path=bad_raw, curated_json_path=curated_json, curated_csv_path=curated_csv
        )
        res = importer.import_and_curate()

        assert res["status"] == "SUCCESS"
        assert res["records_imported"] == 1
        assert res["duplicates_skipped"] == 1
        assert res["malformed_skipped"] == 2

    def test_bhuvan_inundation_importer(self):
        importer = BhuvanInundationImporter()
        res = importer.import_and_curate()
        assert res["status"] == "SUCCESS"
        assert res["records_imported"] == 1
        assert res["access_status"] == "MAP_VIEWER_AND_REPORT_ONLY"
        assert res["submergence_pockets_count"] >= 7

    def test_glofas_discharge_importer(self):
        importer = GloFASDischargeImporter()
        res = importer.import_and_curate()
        assert res["status"] == "SUCCESS"
        assert res["records_imported"] == 11
        assert res["peak_discharge_cumec"] > 600.0  # Oct 2020 peak was ~676.64 m^3/s

    def test_hazards_geojson_importer(self):
        importer = HazardsGeoJsonImporter()
        res = importer.import_and_curate()
        assert res["status"] == "SUCCESS"
        assert res["records_imported"] >= 5

    def test_era5_weather_importer(self):
        importer = ERA5WeatherImporter()
        res = importer.import_and_curate()
        assert res["status"] == "SUCCESS"
        assert res["daily_records_curated"] == 11
        assert res["oct13_14_precip_total_mm"] > 50.0


class TestCurationPipelineAndManifest:
    """Tests the master curation pipeline and generated data manifest."""

    def test_pipeline_execution_and_manifest_validity(self):
        pipeline = SafeMapCurationPipeline(base_dir=BASE_DIR)
        res = pipeline.run()

        assert res["status"] == "COMPLETED"
        assert res["total_curated_datasets"] == 6

        manifest_path = Path(res["manifest_file"])
        assert manifest_path.exists()

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["manifest_version"] in ["1.0.0", "1.1.0", "1.2.0"]
        assert manifest["project"] == "SafeMap AI"
        assert manifest["summary_metrics"]["historical_flood_events_catalogued"] == 8
        assert manifest["summary_metrics"]["downloaded_and_verified_sources"] >= 5

        # Verify all datasets have valid checksums and verified URLs
        for ds in manifest["datasets"]:
            assert "dataset_id" in ds
            assert "source_url" in ds
            assert ds["source_url"].startswith("http")
            assert "access_status" in ds
            assert "data_classification" in ds
            assert ds["data_classification"] in VALID_DATA_CLASSIFICATIONS


class TestDataReadinessAuditAndSafetyGuards:
    """Verifies scientific readiness assessment, statistical power limits, and safety invariants."""

    def test_hyderabad_data_readiness_audit(self):
        audit = audit_local_data_readiness(base_dir=BASE_DIR)

        assert audit["readiness_determination"]["status"] == "INSUFFICIENT_LOCAL_DATA"
        assert audit["readiness_determination"]["suitable_for_training"] is False
        assert audit["readiness_determination"]["suitable_for_validation"] is False

        # Nearest INDOFLOODS gauge must be > 50 km (71.77 km)
        nearest = audit["nearest_indofloods_gauge"]
        assert nearest["distance_km"] > 50.0
        assert nearest["is_within_50km_guard"] is False

        # Baseline LOEO recall
        assert audit["baseline_evaluation_loeo"]["positive_recall"] > 0.5
        assert "UNDEFINED" in audit["baseline_evaluation_loeo"]["specificity"]

        # Statistical power
        assert "< 0.12" in audit["statistical_power_audit"]["statistical_power_estimate"]
        assert audit["statistical_power_audit"]["wilson_95ci_width_on_n8"] > 0.40

    def test_hyderabad_model_unsupported_guard_intact(self):
        # Querying central Hyderabad coordinates directly
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

    def test_routing_and_hazard_endpoints_preserved(self):
        # Flood Hazards endpoint
        haz_resp = client.get("/flood-hazards")
        assert haz_resp.status_code == 200
        hazard_data = haz_resp.json()
        assert hazard_data["total"] >= 5
        assert len(hazard_data["hazards"]) >= 5

        # Shelters endpoint
        sh_resp = client.get("/shelters")
        assert sh_resp.status_code == 200
        shelters_data = sh_resp.json()
        shelter_list = shelters_data["shelters"]
        assert len(shelter_list) >= 11
        for s in shelter_list:
            assert s["data_status"] == "PUBLIC_UNVERIFIED"

        # Emergency facilities endpoint
        ef_resp = client.get("/emergency-facilities")
        assert ef_resp.status_code == 200




class TestDataCurationApiEndpoints:
    """Verifies FastAPI endpoints for manifest, historical events, and readiness audit."""

    def test_api_manifest_endpoint(self):
        resp = client.get("/data-curation/manifest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["manifest_version"] in ["1.0.0", "1.1.0", "1.2.0"]
        assert data["summary_metrics"]["historical_flood_events_catalogued"] == 8

    def test_api_historical_events_endpoint(self):
        resp = client.get("/data-curation/historical-events")
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) == 8

        # Test filter by classification (4 direct OBSERVATION events post-audit: 2000, 2016, 2021, 2023)
        resp_obs = client.get("/data-curation/historical-events?classification=OBSERVATION")
        assert resp_obs.status_code == 200
        obs_events = resp_obs.json()
        assert len(obs_events) >= 4
        for ev in obs_events:
            assert ev["data_classification"] == "OBSERVATION"

        # Test filter by confidence (post-Milestone 7 audit, 2020 confidence is HIGH)
        resp_high = client.get("/data-curation/historical-events?confidence=HIGH")
        assert resp_high.status_code == 200
        h_events = resp_high.json()
        assert len(h_events) >= 1
        assert any(ev["event_id"] == "HYD-EVT-2020-01" for ev in h_events)

    def test_api_readiness_audit_endpoint(self):
        resp = client.get("/data-curation/readiness-audit")
        assert resp.status_code == 200
        audit = resp.json()
        assert audit["readiness_determination"]["status"] == "INSUFFICIENT_LOCAL_DATA"
        assert len(audit["data_gap_requirements"]) >= 4
