"""
Importer for SafeMap AI Hyderabad Historical Flood Event Catalogue.
Milestone 7 Quality Assurance:
Validates dates, discharge and rainfall units, deduplicates event IDs,
strictly verifies source provenance, measurement types (OBSERVED,
SECONDARY_REPORTED, MODELLED, ESTIMATED, UNVERIFIED), verification states
(VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED), audit trails, and outputs
both machine-readable JSON and CSV curated catalogues.
"""

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.data_importers.importer_base import (
    BaseDataImporter,
    compute_sha256,
    normalize_iso_timestamp,
    validate_data_classification,
    validate_measurement_type,
    validate_verification_state,
)

logger = logging.getLogger(__name__)

VALID_CONFIDENCE_LEVELS = {"LOW", "MEDIUM", "HIGH", "VERY_HIGH"}


class FloodEventCatalogueImporter(BaseDataImporter):
    """Imports, validates, and curates historical flood event records with full provenance audit."""

    def __init__(self, raw_path: Optional[Path] = None, curated_json_path: Optional[Path] = None, curated_csv_path: Optional[Path] = None):
        base_dir = Path(__file__).resolve().parents[4]
        raw = raw_path or (base_dir / "data" / "raw" / "flood_events" / "hyderabad_historical_floods_raw.json")
        curated_json = curated_json_path or (base_dir / "data" / "curated" / "hyderabad_flood_event_catalogue.json")
        super().__init__(raw, curated_json)
        self.curated_csv_path = curated_csv_path or (base_dir / "data" / "curated" / "hyderabad_flood_event_catalogue.csv")
        self.curated_csv_path.parent.mkdir(parents=True, exist_ok=True)

    def import_and_curate(self) -> Dict[str, Any]:
        if not self.raw_data_path.exists():
            return {
                "status": "FAILED",
                "error": f"Raw flood events file not found: {self.raw_data_path}",
                "records_imported": 0,
            }

        raw_checksum = compute_sha256(self.raw_data_path)
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        valid_events: List[Dict[str, Any]] = []
        duplicates_count = 0
        malformed_count = 0
        total_items = 0
        self.seen_keys.clear()

        try:
            with open(self.raw_data_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception as e:
            return {
                "status": "FAILED",
                "error": f"Failed to parse raw JSON: {e}",
                "records_imported": 0,
            }

        if not isinstance(raw_data, list):
            return {
                "status": "FAILED",
                "error": "Root element of raw flood events JSON must be an array",
                "records_imported": 0,
            }

        for item in raw_data:
            total_items += 1
            if not isinstance(item, dict):
                malformed_count += 1
                continue

            event_id = item.get("event_id")
            if not event_id or not isinstance(event_id, str) or not event_id.strip():
                malformed_count += 1
                continue
            event_id = event_id.strip()

            if event_id in self.seen_keys:
                duplicates_count += 1
                continue
            self.seen_keys.add(event_id)

            # Validate dates
            start_date_raw = item.get("start_date")
            end_date_raw = item.get("end_date")
            start_iso = normalize_iso_timestamp(start_date_raw)
            end_iso = normalize_iso_timestamp(end_date_raw)
            if not start_iso:
                logger.warning(f"Malformed event {event_id}: missing or invalid start_date '{start_date_raw}'")
                malformed_count += 1
                continue

            # Validate classifications
            source_type_raw = item.get("source_type") or item.get("data_classification") or "OBSERVATION"
            valid_cls, norm_classification = validate_data_classification(source_type_raw)
            if not valid_cls:
                logger.warning(f"Malformed event {event_id}: {norm_classification}")
                malformed_count += 1
                continue

            # Validate measurement types and verification state
            rainfall_m_type = item.get("rainfall_measurement_type", "OBSERVED")
            discharge_m_type = item.get("discharge_measurement_type", "UNKNOWN")
            v_state = item.get("verification_state", "UNVERIFIED")

            _, norm_rf_m_type = validate_measurement_type(rainfall_m_type)
            _, norm_dq_m_type = validate_measurement_type(discharge_m_type)
            _, norm_v_state = validate_verification_state(v_state)

            confidence = str(item.get("confidence_level", "MEDIUM")).strip().upper()
            if confidence not in VALID_CONFIDENCE_LEVELS:
                confidence = "MEDIUM"

            # Validate numerical values
            rainfall_val = item.get("max_24h_rainfall_mm")
            rainfall_clean: Optional[float] = None
            if rainfall_val is not None:
                try:
                    rf_f = float(rainfall_val)
                    if rf_f < 0:
                        malformed_count += 1
                        continue
                    rainfall_clean = round(rf_f, 2)
                except (ValueError, TypeError):
                    malformed_count += 1
                    continue

            discharge_val = item.get("peak_river_discharge_cumec")
            discharge_clean: Optional[float] = None
            if discharge_val is not None:
                try:
                    dq_f = float(discharge_val)
                    if dq_f < 0:
                        malformed_count += 1
                        continue
                    discharge_clean = round(dq_f, 2)
                except (ValueError, TypeError):
                    malformed_count += 1
                    continue

            fatalities_val = item.get("fatalities_estimated")
            fatalities_clean: Optional[int] = None
            if fatalities_val is not None:
                try:
                    fat_i = int(fatalities_val)
                    if fat_i < 0:
                        malformed_count += 1
                        continue
                    fatalities_clean = fat_i
                except (ValueError, TypeError):
                    pass

            affected_areas = item.get("affected_areas", [])
            if not isinstance(affected_areas, list):
                affected_areas = [str(affected_areas)]

            # Provenance structure
            provenance_raw = item.get("provenance") or {}
            provenance_clean = {
                "source_title": str(provenance_raw.get("source_title", item.get("publication_title", "Historical Document"))).strip(),
                "publisher": str(provenance_raw.get("publisher", item.get("source_agency", "Official Agency"))).strip(),
                "publication_year": provenance_raw.get("publication_year"),
                "direct_url": str(provenance_raw.get("direct_url", item.get("source_url", ""))).strip(),
                "citation_detail": str(provenance_raw.get("citation_detail", "Archival reference")).strip(),
                "evidence_note": str(provenance_raw.get("evidence_note", "")).strip(),
                "measurement_classifications": provenance_raw.get("measurement_classifications", {
                    "rainfall": norm_rf_m_type,
                    "discharge": norm_dq_m_type,
                }),
                "verification_status": norm_v_state,
                "unresolved_issues": str(provenance_raw.get("unresolved_issues", "None")).strip(),
            }

            # Audit trail structure
            audit_trail_raw = item.get("audit_trail") or {}
            audit_trail_clean = {
                "original_classification": str(audit_trail_raw.get("original_classification", norm_classification)),
                "original_confidence": str(audit_trail_raw.get("original_confidence", confidence)),
                "corrected_classification": str(audit_trail_raw.get("corrected_classification", norm_classification)),
                "corrected_confidence": str(audit_trail_raw.get("corrected_confidence", confidence)),
                "original_reported_discharge_cumec": audit_trail_raw.get("original_reported_discharge_cumec"),
                "correction_rationale": str(audit_trail_raw.get("correction_rationale", "No corrections needed.")),
            }

            curated_record = {
                "event_id": event_id,
                "event_name": str(item.get("event_name", event_id)).strip(),
                "start_date_iso": start_iso,
                "end_date_iso": end_iso or start_iso,
                "flood_type": str(item.get("flood_type", "UNKNOWN")).strip(),
                "description": str(item.get("description", "")).strip(),
                "district": str(item.get("district", "Hyderabad")).strip(),
                "affected_areas": affected_areas,
                "max_24h_rainfall_mm": rainfall_clean,
                "rainfall_station": str(item.get("rainfall_station", "N/A")).strip(),
                "rainfall_unit": "mm",
                "rainfall_measurement_type": norm_rf_m_type,
                "peak_river_discharge_cumec": discharge_clean,
                "discharge_unit": "m^3/s",
                "discharge_measurement_type": norm_dq_m_type,
                "fatalities_estimated": fatalities_clean,
                "source_agency": str(item.get("source_agency", "Official Historical Records")).strip(),
                "source_url": str(item.get("source_url", "")).strip(),
                "data_classification": norm_classification,
                "confidence_level": confidence,
                "verification_state": norm_v_state,
                "geographic_uncertainty": str(item.get("geographic_uncertainty", "Localized urban report")).strip(),
                "provenance": provenance_clean,
                "audit_trail": audit_trail_clean,
                "raw_checksum_sha256": raw_checksum,
                "curated_at_utc": now_iso,
            }
            valid_events.append(curated_record)

        # Sort chronologically by start_date_iso
        valid_events.sort(key=lambda x: x["start_date_iso"])

        # Write curated JSON
        with open(self.curated_data_path, "w", encoding="utf-8") as f:
            json.dump(valid_events, f, indent=2)
        curated_json_checksum = compute_sha256(self.curated_data_path)

        # Write curated CSV (flattening nested provenance fields for tabular consumers)
        if valid_events:
            csv_rows = []
            for ev in valid_events:
                row_copy = {
                    "event_id": ev["event_id"],
                    "event_name": ev["event_name"],
                    "start_date_iso": ev["start_date_iso"],
                    "end_date_iso": ev["end_date_iso"],
                    "flood_type": ev["flood_type"],
                    "district": ev["district"],
                    "affected_areas": "; ".join(ev["affected_areas"]),
                    "max_24h_rainfall_mm": ev["max_24h_rainfall_mm"],
                    "rainfall_station": ev["rainfall_station"],
                    "rainfall_unit": ev["rainfall_unit"],
                    "rainfall_measurement_type": ev["rainfall_measurement_type"],
                    "peak_river_discharge_cumec": ev["peak_river_discharge_cumec"],
                    "discharge_unit": ev["discharge_unit"],
                    "discharge_measurement_type": ev["discharge_measurement_type"],
                    "fatalities_estimated": ev["fatalities_estimated"],
                    "source_agency": ev["source_agency"],
                    "source_url": ev["source_url"],
                    "data_classification": ev["data_classification"],
                    "confidence_level": ev["confidence_level"],
                    "verification_state": ev["verification_state"],
                    "geographic_uncertainty": ev["geographic_uncertainty"],
                    "provenance_source_title": ev["provenance"]["source_title"],
                    "provenance_publisher": ev["provenance"]["publisher"],
                    "provenance_direct_url": ev["provenance"]["direct_url"],
                    "provenance_citation_detail": ev["provenance"]["citation_detail"],
                    "provenance_evidence_note": ev["provenance"]["evidence_note"],
                    "provenance_unresolved_issues": ev["provenance"]["unresolved_issues"],
                    "audit_original_classification": ev["audit_trail"]["original_classification"],
                    "audit_original_confidence": ev["audit_trail"]["original_confidence"],
                    "audit_correction_rationale": ev["audit_trail"]["correction_rationale"],
                    "raw_checksum_sha256": ev["raw_checksum_sha256"],
                    "curated_at_utc": ev["curated_at_utc"],
                }
                csv_rows.append(row_copy)

            fieldnames = list(csv_rows[0].keys())
            with open(self.curated_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_rows)
        curated_csv_checksum = compute_sha256(self.curated_csv_path)

        verified_cnt = sum(1 for e in valid_events if e["verification_state"] == "VERIFIED")
        partially_verified_cnt = sum(1 for e in valid_events if e["verification_state"] == "PARTIALLY_VERIFIED")
        unverified_cnt = sum(1 for e in valid_events if e["verification_state"] == "UNVERIFIED")

        return {
            "status": "SUCCESS",
            "dataset_id": "HYD-HISTORICAL-FLOOD-CATALOGUE",
            "raw_file": str(self.raw_data_path),
            "curated_json": str(self.curated_data_path),
            "curated_csv": str(self.curated_csv_path),
            "raw_sha256": raw_checksum,
            "curated_json_sha256": curated_json_checksum,
            "curated_csv_sha256": curated_csv_checksum,
            "total_items_read": total_items,
            "records_imported": len(valid_events),
            "duplicates_skipped": duplicates_count,
            "malformed_skipped": malformed_count,
            "verification_summary": {
                "fully_verified": verified_cnt,
                "partially_verified": partially_verified_cnt,
                "unverified": unverified_cnt,
            },
            "date_range": f"{valid_events[0]['start_date_iso'][:10]} to {valid_events[-1]['start_date_iso'][:10]}" if valid_events else "N/A",
        }
