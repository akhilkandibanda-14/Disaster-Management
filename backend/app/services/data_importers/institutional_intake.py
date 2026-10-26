"""
SafeMap AI — Validated Institutional Data Intake Engine (Milestone 8)
Supports authorized manual file-intake workflows for CSV, JSON, and GeoJSON formats.

Enforces:
- Cryptographic provenance (SHA-256, provider, source reference, retrieval date, data owner, usage terms).
- Strict data validation (coordinates, timestamps, units, missing values, duplicates, station IDs).
- Unit normalization while preserving original values and original units.
- Explicit tracking of missing values (no silent zero-filling).
- Actionable structured error messages with row-level diagnostics.
- Cryptographically idempotent repeated imports.
"""

import csv
import io
import json
import logging
import re
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from app.services.data_importers.importer_base import (
    VALID_MEASUREMENT_TYPES,
    compute_sha256,
    normalize_iso_timestamp,
    validate_measurement_type,
)

logger = logging.getLogger(__name__)

# Geographic bounding box for Greater Hyderabad Municipal Corporation + peri-urban Musi catchment
HYD_BBOX = {
    "lat_min": 17.00,
    "lat_max": 17.80,
    "lon_min": 78.10,
    "lon_max": 78.80,
}

# Supported unit normalization factors
UNIT_NORMALIZATION = {
    "rainfall": {
        "mm": 1.0,
        "millimeter": 1.0,
        "millimeters": 1.0,
        "cm": 10.0,
        "centimeter": 10.0,
        "centimeters": 10.0,
        "inch": 25.4,
        "inches": 25.4,
        "in": 25.4,
    },
    "discharge": {
        "m^3/s": 1.0,
        "m3/s": 1.0,
        "cumec": 1.0,
        "cumecs": 1.0,
        "cusec": 0.0283168466,
        "cusecs": 0.0283168466,
        "cfs": 0.0283168466,
    },
    "stage": {
        "m": 1.0,
        "meter": 1.0,
        "meters": 1.0,
        "ft": 0.3048,
        "foot": 0.3048,
        "feet": 0.3048,
    },
}

SENTINEL_NULLS = {
    "-999",
    "-999.0",
    "-9999",
    "-9999.0",
    "NA",
    "N/A",
    "NULL",
    "NONE",
    "NAN",
    "",
}


class InstitutionalIntakeEngine:
    """
    Validates, normalizes, and stores institutional data files submitted
    through authorized manual ingestion workflows.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            self.base_dir = Path(__file__).resolve().parents[4]
        else:
            self.base_dir = base_dir

        self.raw_dir = self.base_dir / "data" / "raw" / "institutional"
        self.curated_dir = self.base_dir / "data" / "curated" / "institutional"
        self.ledger_path = self.curated_dir / "intake_ledger.json"

        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.curated_dir.mkdir(parents=True, exist_ok=True)

    def validate_content(
        self,
        content: str,
        filename: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Dry-run validation of file content against institutional ingestion contracts.
        Returns a structured validation diagnostic with row-by-row error details.
        """
        raw_bytes = content.encode("utf-8")
        raw_sha256 = sha256(raw_bytes).hexdigest()

        # Security check: payload size limit (10MB)
        if len(content) > 10 * 1024 * 1024:
            return {
                "valid": False,
                "filename": filename,
                "file_checksum_sha256": raw_sha256,
                "errors": [{"field": "content", "value": None, "error": "File size exceeds maximum allowable intake limit of 10 MB."}],
                "warnings": [],
                "total_records_processed": 0,
                "valid_records_count": 0,
            }

        # Security check: prohibited null bytes or illegal path characters in filename
        if "\x00" in filename:
            return {
                "valid": False,
                "filename": filename,
                "file_checksum_sha256": raw_sha256,
                "errors": [{"field": "filename", "value": filename, "error": "Filename contains prohibited null byte characters."}],
                "warnings": [],
                "total_records_processed": 0,
                "valid_records_count": 0,
            }

        # 1. Metadata contract validation
        meta_errors = self._validate_metadata(metadata)
        if meta_errors:
            return {
                "valid": False,
                "filename": filename,
                "file_checksum_sha256": raw_sha256,
                "errors": meta_errors,
                "warnings": [],
                "total_records_processed": 0,
                "valid_records_count": 0,
            }

        ext = Path(filename).suffix.lower()
        if ext in {".csv", ".txt"}:
            return self._validate_csv(content, filename, raw_sha256, metadata)
        elif ext in {".json", ".geojson"}:
            return self._validate_json(content, filename, raw_sha256, metadata)
        else:
            return {
                "valid": False,
                "filename": filename,
                "file_checksum_sha256": raw_sha256,
                "errors": [
                    {
                        "field": "filename",
                        "value": filename,
                        "error": f"Unsupported file extension '{ext}'. Only .csv, .json, and .geojson are accepted.",
                    }
                ],
                "warnings": [],
                "total_records_processed": 0,
                "valid_records_count": 0,
            }

    def commit_batch(
        self,
        content: str,
        filename: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validates and commits an authorized institutional data batch to storage.
        Guarantees idempotency via cryptographic SHA-256 checksums.
        """
        validation = self.validate_content(content, filename, metadata)
        if not validation["valid"]:
            return {
                "status": "VALIDATION_FAILED",
                "message": "Institutional intake rejected due to validation errors. Records were not saved.",
                "validation": validation,
            }

        raw_sha256 = validation["file_checksum_sha256"]
        ledger = self._load_ledger()

        # Check idempotency
        for entry in ledger:
            if entry.get("file_checksum_sha256") == raw_sha256:
                logger.info(f"Idempotent skip: File {filename} (SHA-256: {raw_sha256}) already ingested.")
                return {
                    "status": "IDEMPOTENT_SKIPPED",
                    "message": "File with identical SHA-256 checksum has already been ingested. Preserving existing record.",
                    "batch_id": entry["batch_id"],
                    "file_checksum_sha256": raw_sha256,
                    "records_stored": entry["records_count"],
                    "curated_file": entry["curated_file"],
                }

        # Generate unique batch ID
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_provider = re.sub(r"[^A-Za-z0-9_-]", "", metadata.get("provider", "INSTITUTION")).upper()
        batch_id = f"INTAKE_{safe_provider}_{timestamp_str}"

        # Save raw source file copy with strict path-traversal prevention
        clean_basename = Path(filename).name
        safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", clean_basename)
        if not safe_name or safe_name in (".", ".."):
            safe_name = "data_intake_file.txt"

        raw_file_path = (self.raw_dir / f"{batch_id}_{safe_name}").resolve()
        curated_file_path = (self.curated_dir / f"{batch_id}_curated.json").resolve()

        # Security invariant: target files must strictly reside within repository intake directories
        if not str(raw_file_path).startswith(str(self.raw_dir.resolve())):
            raise ValueError(f"Security error: path traversal detected for filename: {filename}")
        if not str(curated_file_path).startswith(str(self.curated_dir.resolve())):
            raise ValueError(f"Security error: curated target path traversal detected: {curated_file_path}")

        with open(raw_file_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Save normalized curated JSON
        normalized_records = validation.get("normalized_records", [])
        with open(curated_file_path, "w", encoding="utf-8") as f:
            json.dump(normalized_records, f, indent=2)

        curated_sha256 = compute_sha256(curated_file_path)

        # Append to audit ledger
        ledger_entry = {
            "batch_id": batch_id,
            "filename": filename,
            "provider": metadata["provider"],
            "source_reference": metadata["source_reference"],
            "retrieval_date": metadata["retrieval_date"],
            "data_owner": metadata.get("data_owner", metadata["provider"]),
            "usage_restrictions": metadata.get("usage_restrictions", "RESTRICTED_RESEARCH_ONLY"),
            "measurement_classification": metadata.get("measurement_classification", "OBSERVED"),
            "file_checksum_sha256": raw_sha256,
            "curated_sha256": curated_sha256,
            "raw_file": str(raw_file_path.relative_to(self.base_dir)),
            "curated_file": str(curated_file_path.relative_to(self.base_dir)),
            "records_count": len(normalized_records),
            "ingested_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        ledger.append(ledger_entry)
        self._save_ledger(ledger)

        return {
            "status": "SUCCESS",
            "message": f"Successfully ingested {len(normalized_records)} records from {metadata['provider']}.",
            "batch_id": batch_id,
            "file_checksum_sha256": raw_sha256,
            "curated_sha256": curated_sha256,
            "records_stored": len(normalized_records),
            "raw_file": str(raw_file_path.relative_to(self.base_dir)),
            "curated_file": str(curated_file_path.relative_to(self.base_dir)),
            "warnings": validation.get("warnings", []),
        }

    def get_intake_log(self) -> List[Dict[str, Any]]:
        """Returns the chronological audit log of all institutional ingestions."""
        return self._load_ledger()

    def get_sources_inventory(self) -> Dict[str, Any]:
        """Returns comprehensive status of all sources, tracking available vs restricted vs draft requests."""
        ledger = self._load_ledger()
        return {
            "inventory_timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "target_region": "Greater Hyderabad Municipal Corporation (GHMC), Telangana",
            "active_intake_batches_count": len(ledger),
            "total_intake_records_stored": sum(e.get("records_count", 0) for e in ledger),
            "source_categories": {
                "downloaded_and_verified": [
                    {
                        "id": "DES-HYD-RAINFALL-ANNUAL",
                        "agency": "Telangana Directorate of Economics & Statistics (DES)",
                        "coverage": "1970–2023 Annual & Seasonal Rainfall (19 Benchmark Years)",
                        "classification": "OBSERVATION",
                        "status": "DOWNLOADED_AND_VERIFIED",
                    },
                    {
                        "id": "HYD-HISTORICAL-FLOOD-CATALOGUE",
                        "agency": "Various Official Archives (IMD, Nizam PWD, TSDPS, GHMC)",
                        "coverage": "1908–2023 (8 Audited Flood Events)",
                        "classification": "HISTORICAL_RECORD / OBSERVATION",
                        "status": "PARTIALLY_VERIFIED (0 Fully Verified · 8 Partially Verified)",
                    },
                    {
                        "id": "GLOFAS-MUSI-OCT2020",
                        "agency": "Copernicus GloFAS / ECMWF",
                        "coverage": "Oct 10–20, 2020 Daily River Discharge (Gridded Reach)",
                        "classification": "MODELLED",
                        "status": "DOWNLOADED_AND_VERIFIED (Uncalibrated Simulation)",
                    },
                    {
                        "id": "ERA5-HYD-OCT2020",
                        "agency": "ECMWF ERA5 Atmospheric Reanalysis",
                        "coverage": "Oct 10–20, 2020 Meteorological Parameters",
                        "classification": "MODELLED",
                        "status": "DOWNLOADED_AND_VERIFIED",
                    },
                    {
                        "id": "GHMC-FLOOD-ZONES",
                        "agency": "GHMC Disaster Management & MRDCL",
                        "coverage": "5 Surveyed Flood Prone Polygons",
                        "classification": "HISTORICAL_VULNERABILITY",
                        "status": "PUBLIC_UNVERIFIED",
                    },
                ],
                "viewer_or_report_only": [
                    {
                        "id": "BHUVAN-NRSC-HYD-OCT2020",
                        "agency": "ISRO / NRSC Disaster Management Geoportal (Bhuvan)",
                        "coverage": "October 18, 2020 Satellite Flood Extent",
                        "status": "MAP_VIEWER_AND_REPORT_ONLY",
                        "restriction": "Raw full-resolution GeoTIFF rasters require nodal credentials.",
                    }
                ],
                "restricted_institutional_access": [
                    {
                        "id": "TSDPS-AWS-TELEMETRY",
                        "agency": "Telangana State Development Planning Society (TSDPS)",
                        "coverage": "15-minute / Hourly AWS Telemetry (~100+ stations, 2014–2024)",
                        "status": "RESTRICTED_PORTAL_VIEWER_ONLY",
                        "restriction": "Written data-sharing agreement and GoTS authorization required.",
                    },
                    {
                        "id": "TG-IRRIGATION-DAM-TELEMETRY",
                        "agency": "Telangana Irrigation & CAD Department",
                        "coverage": "Osman Sagar & Himayat Sagar Hourly Sluice Gate Outflow Logs",
                        "status": "RESTRICTED_INSTITUTIONAL_ACCESS",
                        "restriction": "State government departmental authorization required.",
                    },
                ],
                "draft_data_requests": [
                    {
                        "template": "docs/data_requests/template_tsdps_aws_rainfall.md",
                        "recipient": "Telangana State Development Planning Society (TSDPS)",
                        "scope": "10-year 15-minute AWS rainfall time series (~100+ stations)",
                        "status": "DRAFT_REQUEST_PREPARED (Not yet submitted)",
                    },
                    {
                        "template": "docs/data_requests/template_irrigation_musi_river_stage_and_discharge.md",
                        "recipient": "Telangana Irrigation & CAD Department / HMWSSB",
                        "scope": "Hourly gate opening logs & Musi River stage gauge readings",
                        "status": "DRAFT_REQUEST_PREPARED (Not yet submitted)",
                    },
                    {
                        "template": "docs/data_requests/template_nrsc_bhuvan_sar_inundation.md",
                        "recipient": "ISRO / NRSC Disaster Management Support Programme",
                        "scope": "Level-3 SAR GeoTIFF flood inundation rasters (2016, 2020, 2022, 2023)",
                        "status": "DRAFT_REQUEST_PREPARED (Not yet submitted)",
                    },
                    {
                        "template": "docs/data_requests/template_negative_control_observations.md",
                        "recipient": "Joint Requisition: IMD, TSDPS, and GHMC DRF",
                        "scope": "Multi-year daily continuous observation matrix + municipal zero-deployment logs",
                        "status": "DRAFT_REQUEST_PREPARED (Not yet submitted)",
                    },
                ],
            },
            "unsupported_measurements_tracker": [
                {
                    "event_id": "HYD-EVT-2000-01",
                    "event_name": "August 2000 Urban Deluge",
                    "missing_parameter": "Peak River Discharge",
                    "audited_status": "Nullified in observations; prior 1250.0 cumec estimate preserved in audit trail.",
                    "required_gauge": "Musi River calibrated stream gauge telemetry (none existed in 2000).",
                },
                {
                    "event_id": "HYD-EVT-2016-01",
                    "event_name": "September 2016 Alwal-Bhandari Inundation",
                    "missing_parameter": "Peak River Discharge",
                    "audited_status": "Nullified in observations; prior 210.0 cumec estimate preserved in audit trail.",
                    "required_gauge": "Flooding caused by Alwal/Fox Sagar lake nala surplus; Musi stream gauge not applicable.",
                },
                {
                    "event_id": "HYD-EVT-2021-01",
                    "event_name": "July 2021 Central Flash Inundation",
                    "missing_parameter": "Peak River Discharge",
                    "audited_status": "Nullified in observations; prior 95.0 cumec estimate preserved in audit trail.",
                    "required_gauge": "Event was arterial underpass waterlogging; no river overflow occurred.",
                },
                {
                    "event_id": "HYD-EVT-2023-01",
                    "event_name": "July 2023 Arterial Stagnation",
                    "missing_parameter": "Peak River Discharge",
                    "audited_status": "Nullified in observations; prior 85.0 cumec estimate preserved in audit trail.",
                    "required_gauge": "Confined to 48 drainage bottlenecks; Musi stream gauge telemetry absent.",
                },
            ],
        }

    # =========================================================================
    # Internal Validation Helpers
    # =========================================================================

    def _validate_metadata(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        errors = []
        required_fields = ["provider", "source_reference", "retrieval_date"]
        for f in required_fields:
            if not metadata.get(f) or not str(metadata.get(f)).strip():
                errors.append({"field": f"metadata.{f}", "value": None, "error": f"Required metadata field '{f}' is missing or empty."})

        # Validate retrieval date
        r_date = metadata.get("retrieval_date")
        if r_date:
            parsed = normalize_iso_timestamp(str(r_date))
            if not parsed:
                errors.append({"field": "metadata.retrieval_date", "value": r_date, "error": "Invalid retrieval_date. Expected ISO 8601 format."})

        # Validate classification
        m_cls = metadata.get("measurement_classification", "OBSERVED")
        if m_cls not in VALID_MEASUREMENT_TYPES:
            errors.append({
                "field": "metadata.measurement_classification",
                "value": m_cls,
                "error": f"Invalid measurement classification '{m_cls}'. Must be one of: {list(VALID_MEASUREMENT_TYPES)}",
            })

        return errors

    def _validate_csv(
        self,
        content: str,
        filename: str,
        raw_sha256: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        errors: List[Dict[str, Any]] = []
        warnings: List[str] = []
        normalized_records: List[Dict[str, Any]] = []
        seen_keys = set()

        try:
            reader = csv.DictReader(io.StringIO(content))
        except Exception as e:
            return {
                "valid": False,
                "filename": filename,
                "file_checksum_sha256": raw_sha256,
                "errors": [{"field": "file", "value": None, "error": f"CSV parse failure: {str(e)}"}],
                "warnings": [],
                "total_records_processed": 0,
                "valid_records_count": 0,
            }

        if not reader.fieldnames:
            return {
                "valid": False,
                "filename": filename,
                "file_checksum_sha256": raw_sha256,
                "errors": [{"field": "header", "value": None, "error": "CSV file contains no header row or is empty."}],
                "warnings": [],
                "total_records_processed": 0,
                "valid_records_count": 0,
            }

        headers = [h.strip().lower() for h in reader.fieldnames if h]

        row_num = 1  # 1-indexed (header is row 1, data starts row 2)
        for raw_row in reader:
            row_num += 1
            row_dict = {k.strip().lower(): v.strip() for k, v in raw_row.items() if k}

            rec, row_errors = self._validate_and_normalize_row(row_dict, row_num, metadata)
            if row_errors:
                errors.extend(row_errors)
            else:
                # Check for duplicates
                dup_key = (rec.get("timestamp_iso"), rec.get("station_id"))
                if dup_key in seen_keys and None not in dup_key:
                    errors.append({
                        "row": row_num,
                        "field": "duplicate",
                        "value": f"{dup_key[1]} @ {dup_key[0]}",
                        "error": f"Duplicate record detected for station '{dup_key[1]}' at timestamp '{dup_key[0]}'.",
                    })
                else:
                    seen_keys.add(dup_key)
                    normalized_records.append(rec)

        if not normalized_records and not errors:
            errors.append({"row": 0, "field": "content", "value": None, "error": "CSV contains no data rows."})

        return {
            "valid": len(errors) == 0,
            "filename": filename,
            "file_checksum_sha256": raw_sha256,
            "total_records_processed": row_num - 1,
            "valid_records_count": len(normalized_records),
            "errors": errors,
            "warnings": warnings,
            "normalized_records": normalized_records if len(errors) == 0 else [],
        }

    def _validate_json(
        self,
        content: str,
        filename: str,
        raw_sha256: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        errors: List[Dict[str, Any]] = []
        warnings: List[str] = []
        normalized_records: List[Dict[str, Any]] = []
        seen_keys = set()

        try:
            data = json.loads(content)
        except Exception as e:
            return {
                "valid": False,
                "filename": filename,
                "file_checksum_sha256": raw_sha256,
                "errors": [{"field": "json", "value": None, "error": f"JSON syntax error: {str(e)}"}],
                "warnings": [],
                "total_records_processed": 0,
                "valid_records_count": 0,
            }

        # Extract items list
        raw_items: List[Dict[str, Any]] = []
        if isinstance(data, list):
            raw_items = data
        elif isinstance(data, dict):
            if data.get("type") == "FeatureCollection" and "features" in data:
                # GeoJSON FeatureCollection
                for f in data.get("features", []):
                    item = dict(f.get("properties", {}))
                    geom = f.get("geometry", {})
                    if geom.get("type") == "Point" and isinstance(geom.get("coordinates"), list):
                        coords = geom["coordinates"]
                        if len(coords) >= 2:
                            item["longitude"] = coords[0]
                            item["latitude"] = coords[1]
                    raw_items.append(item)
            elif "records" in data and isinstance(data["records"], list):
                raw_items = data["records"]
            elif "data" in data and isinstance(data["data"], list):
                raw_items = data["data"]
            else:
                raw_items = [data]

        if not raw_items:
            return {
                "valid": False,
                "filename": filename,
                "file_checksum_sha256": raw_sha256,
                "errors": [{"field": "content", "value": None, "error": "JSON document contains no records or empty array."}],
                "warnings": [],
                "total_records_processed": 0,
                "valid_records_count": 0,
            }

        for idx, item in enumerate(raw_items):
            item_num = idx + 1
            if not isinstance(item, dict):
                errors.append({"row": item_num, "field": "record", "value": str(item), "error": "Record must be a JSON object / dictionary."})
                continue

            low_dict = {str(k).strip().lower(): v for k, v in item.items()}
            rec, row_errors = self._validate_and_normalize_row(low_dict, item_num, metadata)
            if row_errors:
                errors.extend(row_errors)
            else:
                dup_key = (rec.get("timestamp_iso"), rec.get("station_id"))
                if dup_key in seen_keys and None not in dup_key:
                    errors.append({
                        "row": item_num,
                        "field": "duplicate",
                        "value": f"{dup_key[1]} @ {dup_key[0]}",
                        "error": f"Duplicate record detected for station '{dup_key[1]}' at timestamp '{dup_key[0]}'.",
                    })
                else:
                    seen_keys.add(dup_key)
                    normalized_records.append(rec)

        return {
            "valid": len(errors) == 0,
            "filename": filename,
            "file_checksum_sha256": raw_sha256,
            "total_records_processed": len(raw_items),
            "valid_records_count": len(normalized_records),
            "errors": errors,
            "warnings": warnings,
            "normalized_records": normalized_records if len(errors) == 0 else [],
        }

    def _validate_and_normalize_row(
        self,
        row: Dict[str, Any],
        row_num: int,
        metadata: Dict[str, Any],
    ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        errors: List[Dict[str, Any]] = []
        normalized: Dict[str, Any] = {}

        # 1. Timestamp validation
        ts_val = self._find_first(row, ["timestamp", "date", "datetime", "start_date", "time", "observation_time"])
        if not ts_val or str(ts_val).strip() in SENTINEL_NULLS:
            errors.append({"row": row_num, "field": "timestamp", "value": ts_val, "error": "Timestamp field is required and cannot be null."})
        else:
            ts_iso = normalize_iso_timestamp(str(ts_val).strip())
            if not ts_iso:
                errors.append({"row": row_num, "field": "timestamp", "value": str(ts_val), "error": f"Invalid timestamp '{ts_val}'. Expected valid ISO 8601 date."})
            else:
                try:
                    year = int(ts_iso[:4])
                    if not (1900 <= year <= 2100):
                        errors.append({"row": row_num, "field": "timestamp", "value": ts_iso, "error": f"Timestamp year {year} is outside allowable range [1900, 2100]."})
                    else:
                        normalized["timestamp_iso"] = ts_iso
                except ValueError:
                    errors.append({"row": row_num, "field": "timestamp", "value": ts_iso, "error": "Failed to parse year from timestamp."})

        # 2. Coordinates validation
        lat_val = self._find_first(row, ["latitude", "lat", "y"])
        lon_val = self._find_first(row, ["longitude", "lon", "lng", "long", "x"])

        if lat_val is not None and str(lat_val).strip() not in SENTINEL_NULLS:
            try:
                lat_f = float(lat_val)
                if not (-90.0 <= lat_f <= 90.0):
                    errors.append({"row": row_num, "field": "latitude", "value": lat_f, "error": f"Latitude {lat_f} must be between -90.0 and 90.0."})
                else:
                    normalized["latitude"] = round(lat_f, 6)
            except (ValueError, TypeError):
                errors.append({"row": row_num, "field": "latitude", "value": str(lat_val), "error": f"Latitude '{lat_val}' is not a valid floating-point number."})

        if lon_val is not None and str(lon_val).strip() not in SENTINEL_NULLS:
            try:
                lon_f = float(lon_val)
                if not (-180.0 <= lon_f <= 180.0):
                    errors.append({"row": row_num, "field": "longitude", "value": lon_f, "error": f"Longitude {lon_f} must be between -180.0 and 180.0."})
                else:
                    normalized["longitude"] = round(lon_f, 6)
            except (ValueError, TypeError):
                errors.append({"row": row_num, "field": "longitude", "value": str(lon_val), "error": f"Longitude '{lon_val}' is not a valid floating-point number."})

        if "latitude" in normalized and "longitude" in normalized:
            lat = normalized["latitude"]
            lon = normalized["longitude"]
            normalized["in_hyderabad_region"] = (
                HYD_BBOX["lat_min"] <= lat <= HYD_BBOX["lat_max"]
                and HYD_BBOX["lon_min"] <= lon <= HYD_BBOX["lon_max"]
            )

        # 3. Station Identifier validation
        st_val = self._find_first(row, ["station_id", "station_code", "station", "gauge_id", "site_id", "id"])
        if st_val is not None and str(st_val).strip() not in SENTINEL_NULLS:
            st_clean = str(st_val).strip()
            if not (2 <= len(st_clean) <= 64):
                errors.append({"row": row_num, "field": "station_id", "value": st_clean, "error": "Station identifier length must be between 2 and 64 characters."})
            elif not re.match(r"^[A-Za-z0-9_.-]+$", st_clean):
                errors.append({"row": row_num, "field": "station_id", "value": st_clean, "error": f"Station identifier '{st_clean}' contains invalid characters. Use alphanumeric, dash, or underscore."})
            else:
                normalized["station_id"] = st_clean
        else:
            normalized["station_id"] = None

        # 4. Rainfall parameter validation & unit normalization
        rf_val = self._find_first(row, ["rainfall", "rainfall_mm", "precipitation", "rain", "precip", "rainfall_value"])
        rf_unit = self._find_first(row, ["rainfall_unit", "rain_unit", "precip_unit", "unit"])
        if rf_val is not None and str(rf_val).strip() not in SENTINEL_NULLS:
            try:
                rf_f = float(rf_val)
                if rf_f < 0.0:
                    errors.append({"row": row_num, "field": "rainfall", "value": rf_f, "error": f"Rainfall cannot be negative ({rf_f})."})
                else:
                    unit_str = str(rf_unit).strip().lower() if rf_unit else "mm"
                    if unit_str not in UNIT_NORMALIZATION["rainfall"]:
                        errors.append({"row": row_num, "field": "rainfall_unit", "value": unit_str, "error": f"Unsupported rainfall unit '{unit_str}'. Allowed: {list(UNIT_NORMALIZATION['rainfall'].keys())}"})
                    else:
                        factor = UNIT_NORMALIZATION["rainfall"][unit_str]
                        normalized["rainfall"] = {
                            "original_value": rf_f,
                            "original_unit": unit_str,
                            "normalized_value_mm": round(rf_f * factor, 3),
                            "normalized_unit": "mm",
                        }
            except (ValueError, TypeError):
                errors.append({"row": row_num, "field": "rainfall", "value": str(rf_val), "error": f"Rainfall value '{rf_val}' is not a valid numeric float."})
        else:
            normalized["rainfall"] = None

        # 5. Discharge parameter validation & unit normalization
        dq_val = self._find_first(row, ["discharge", "river_discharge", "peak_discharge", "flow", "outflow", "discharge_cumec"])
        dq_unit = self._find_first(row, ["discharge_unit", "flow_unit", "unit"])
        if dq_val is not None and str(dq_val).strip() not in SENTINEL_NULLS:
            try:
                dq_f = float(dq_val)
                if dq_f < 0.0:
                    errors.append({"row": row_num, "field": "discharge", "value": dq_f, "error": f"River discharge cannot be negative ({dq_f})."})
                else:
                    unit_str = str(dq_unit).strip().lower() if dq_unit else "m^3/s"
                    if unit_str not in UNIT_NORMALIZATION["discharge"]:
                        errors.append({"row": row_num, "field": "discharge_unit", "value": unit_str, "error": f"Unsupported discharge unit '{unit_str}'. Allowed: {list(UNIT_NORMALIZATION['discharge'].keys())}"})
                    else:
                        factor = UNIT_NORMALIZATION["discharge"][unit_str]
                        normalized["discharge"] = {
                            "original_value": dq_f,
                            "original_unit": unit_str,
                            "normalized_value_cumec": round(dq_f * factor, 3),
                            "normalized_unit": "m^3/s",
                        }
            except (ValueError, TypeError):
                errors.append({"row": row_num, "field": "discharge", "value": str(dq_val), "error": f"Discharge value '{dq_val}' is not a valid numeric float."})
        else:
            normalized["discharge"] = None

        # 6. Water Stage validation & unit normalization
        stage_val = self._find_first(row, ["stage", "water_level", "river_stage", "gauge_height", "reservoir_level"])
        stage_unit = self._find_first(row, ["stage_unit", "water_level_unit", "unit"])
        if stage_val is not None and str(stage_val).strip() not in SENTINEL_NULLS:
            try:
                stg_f = float(stage_val)
                unit_str = str(stage_unit).strip().lower() if stage_unit else "m"
                if unit_str not in UNIT_NORMALIZATION["stage"]:
                    errors.append({"row": row_num, "field": "stage_unit", "value": unit_str, "error": f"Unsupported stage unit '{unit_str}'. Allowed: {list(UNIT_NORMALIZATION['stage'].keys())}"})
                else:
                    factor = UNIT_NORMALIZATION["stage"][unit_str]
                    normalized["water_stage"] = {
                        "original_value": stg_f,
                        "original_unit": unit_str,
                        "normalized_value_m": round(stg_f * factor, 3),
                        "normalized_unit": "m",
                    }
            except (ValueError, TypeError):
                errors.append({"row": row_num, "field": "water_stage", "value": str(stage_val), "error": f"Water stage '{stage_val}' is not a valid numeric float."})
        else:
            normalized["water_stage"] = None

        # Attach metadata lineage
        normalized["provider"] = metadata["provider"]
        normalized["source_reference"] = metadata["source_reference"]
        normalized["measurement_classification"] = metadata.get("measurement_classification", "OBSERVED")
        normalized["data_owner"] = metadata.get("data_owner", metadata["provider"])
        normalized["usage_restrictions"] = metadata.get("usage_restrictions", "RESTRICTED_RESEARCH_ONLY")

        if errors:
            return None, errors
        return normalized, []

    def _find_first(self, row: Dict[str, Any], candidate_keys: List[str]) -> Optional[Any]:
        for k in candidate_keys:
            if k in row and row[k] is not None:
                return row[k]
        return None

    def _load_ledger(self) -> List[Dict[str, Any]]:
        if not self.ledger_path.exists():
            return []
        try:
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_ledger(self, ledger: List[Dict[str, Any]]) -> None:
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            json.dump(ledger, f, indent=2)
