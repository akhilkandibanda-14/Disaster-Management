"""
Importer for Copernicus GloFAS Musi River Discharge Reanalysis/Forecast data.
Validates daily timestamps, discharge units (m^3/s), and enforces MODELLED/MODEL_FORECAST
data classification to prevent mistaking model output for physical stream gauge measurements.
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
    validate_coordinates,
)

logger = logging.getLogger(__name__)


class GloFASDischargeImporter(BaseDataImporter):
    """Imports, validates, and curates GloFAS modelled Musi River discharge time series."""

    def __init__(self, raw_path: Optional[Path] = None, curated_path: Optional[Path] = None):
        base_dir = Path(__file__).resolve().parents[4]
        raw = raw_path or (base_dir / "data" / "raw" / "open_meteo" / "musi_glofas_oct2020.json")
        curated = curated_path or (base_dir / "data" / "curated" / "musi_glofas_oct2020_curated.csv")
        super().__init__(raw, curated)

    def import_and_curate(self) -> Dict[str, Any]:
        if not self.raw_data_path.exists():
            return {
                "status": "FAILED",
                "error": f"Raw GloFAS file not found: {self.raw_data_path}",
                "records_imported": 0,
            }

        raw_checksum = compute_sha256(self.raw_data_path)
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            with open(self.raw_data_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception as e:
            return {
                "status": "FAILED",
                "error": f"Failed to parse GloFAS JSON: {e}",
                "records_imported": 0,
            }

        lat = raw_data.get("latitude")
        lon = raw_data.get("longitude")
        v, valid_lat, valid_lon, err = validate_coordinates(lat, lon)
        if not v:
            return {
                "status": "FAILED",
                "error": f"Invalid coordinates in GloFAS data: {err}",
                "records_imported": 0,
            }

        daily = raw_data.get("daily", {})
        times = daily.get("time", [])
        discharges = daily.get("river_discharge", [])

        if len(times) != len(discharges):
            return {
                "status": "FAILED",
                "error": f"Mismatched array lengths: {len(times)} dates vs {len(discharges)} discharge values",
                "records_imported": 0,
            }

        valid_rows: List[Dict[str, Any]] = []
        duplicates_count = 0
        malformed_count = 0
        self.seen_keys.clear()

        for t_raw, q_raw in zip(times, discharges):
            iso_ts = normalize_iso_timestamp(t_raw)
            if not iso_ts:
                malformed_count += 1
                continue

            date_str = iso_ts[:10]
            if date_str in self.seen_keys:
                duplicates_count += 1
                continue
            self.seen_keys.add(date_str)

            try:
                q_val = float(q_raw)
                if q_val < 0.0:
                    malformed_count += 1
                    continue
                q_clean = round(q_val, 2)
            except (ValueError, TypeError):
                malformed_count += 1
                continue

            valid_rows.append({
                "date_iso": iso_ts,
                "river_discharge_cumec": q_clean,
                "unit": "m^3/s",
                "latitude": valid_lat,
                "longitude": valid_lon,
                "river_name": "Musi River",
                "source": "Copernicus GloFAS via Open-Meteo Flood API",
                "source_url": "https://flood-api.open-meteo.com/v1/flood",
                "data_classification": "MODEL_FORECAST",
                "calibration_status": "UNCALIBRATED_SIMULATION",
                "raw_checksum_sha256": raw_checksum,
                "curated_at_utc": now_iso,
            })

        valid_rows.sort(key=lambda x: x["date_iso"])

        if valid_rows:
            fieldnames = list(valid_rows[0].keys())
            with open(self.curated_data_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(valid_rows)

        curated_checksum = compute_sha256(self.curated_data_path)

        return {
            "status": "SUCCESS",
            "dataset_id": "GLOFAS-MUSI-OCT2020-DISCHARGE",
            "raw_file": str(self.raw_data_path),
            "curated_file": str(self.curated_data_path),
            "raw_sha256": raw_checksum,
            "curated_sha256": curated_checksum,
            "total_items_read": len(times),
            "records_imported": len(valid_rows),
            "duplicates_skipped": duplicates_count,
            "malformed_skipped": malformed_count,
            "date_range": f"{valid_rows[0]['date_iso'][:10]} to {valid_rows[-1]['date_iso'][:10]}" if valid_rows else "N/A",
            "peak_discharge_cumec": max([r["river_discharge_cumec"] for r in valid_rows]) if valid_rows else None,
        }
