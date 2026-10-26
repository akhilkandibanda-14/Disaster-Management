"""
Importer for Telangana Directorate of Economics and Statistics (DES)
historical rainfall publications for Hyderabad District.
"""

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from app.services.data_importers.importer_base import (
    BaseDataImporter,
    compute_sha256,
    normalize_iso_timestamp,
)

logger = logging.getLogger(__name__)


class DESRainfallImporter(BaseDataImporter):
    """Imports, validates, and normalizes DES Telangana annual/seasonal rainfall records."""

    def __init__(self, raw_path: Path = None, curated_path: Path = None):
        base_dir = Path(__file__).resolve().parents[4]
        raw = raw_path or (base_dir / "data" / "raw" / "des_telangana" / "hyderabad_rainfall_annual_des.csv")
        curated = curated_path or (base_dir / "data" / "curated" / "hyderabad_rainfall_annual_curated.csv")
        super().__init__(raw, curated)

    def import_and_curate(self) -> Dict[str, Any]:
        if not self.raw_data_path.exists():
            return {
                "status": "FAILED",
                "error": f"Raw DES file not found: {self.raw_data_path}",
                "records_imported": 0
            }

        raw_checksum = compute_sha256(self.raw_data_path)
        mtime = self.raw_data_path.stat().st_mtime
        now_iso = datetime.fromtimestamp(mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        valid_rows: List[Dict[str, Any]] = []
        duplicates_count = 0
        malformed_count = 0
        total_rows = 0
        self.seen_keys.clear()

        with open(self.raw_data_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_rows += 1
                try:
                    year_val = row.get("Year", "").strip()
                    if not year_val or not year_val.isdigit():
                        malformed_count += 1
                        continue

                    year_int = int(year_val)
                    if year_int in self.seen_keys:
                        duplicates_count += 1
                        continue
                    self.seen_keys.add(year_int)

                    normal_mm = float(row.get("Normal_Annual_mm", 0.0))
                    actual_mm = float(row.get("Actual_Annual_mm", 0.0))
                    dev_pct = float(row.get("Deviation_Percent", 0.0))
                    sw_mm = float(row.get("SW_Monsoon_Actual_mm", 0.0))
                    ne_mm = float(row.get("NE_Monsoon_Actual_mm", 0.0))

                    if normal_mm < 0 or actual_mm < 0 or sw_mm < 0 or ne_mm < 0:
                        malformed_count += 1
                        continue

                    iso_date = normalize_iso_timestamp(year_val)

                    valid_rows.append({
                        "year": year_int,
                        "observation_date_iso": iso_date,
                        "normal_annual_rainfall_mm": round(normal_mm, 2),
                        "actual_annual_rainfall_mm": round(actual_mm, 2),
                        "deviation_percent": round(dev_pct, 2),
                        "sw_monsoon_rainfall_mm": round(sw_mm, 2),
                        "ne_monsoon_rainfall_mm": round(ne_mm, 2),
                        "district": "Hyderabad",
                        "measurement_unit": "mm",
                        "geographic_resolution": "District Aggregate",
                        "source_agency": row.get("Source_Agency", "DES Telangana"),
                        "publication_title": row.get("Publication_Title", "Telangana State Statistical Abstract"),
                        "data_classification": "OBSERVATION",
                        "raw_checksum_sha256": raw_checksum,
                        "curated_at_utc": now_iso
                    })
                except (ValueError, KeyError) as e:
                    logger.warning(f"Malformed row in DES rainfall dataset: {row} ({e})")
                    malformed_count += 1

        # Sort chronologically
        valid_rows.sort(key=lambda r: r["year"])

        # Write curated output
        if valid_rows:
            fieldnames = list(valid_rows[0].keys())
            with open(self.curated_data_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(valid_rows)

        curated_checksum = compute_sha256(self.curated_data_path)

        return {
            "status": "SUCCESS",
            "dataset_id": "DES-HYD-RAINFALL-ANNUAL",
            "raw_file": str(self.raw_data_path),
            "curated_file": str(self.curated_data_path),
            "raw_sha256": raw_checksum,
            "curated_sha256": curated_checksum,
            "total_rows_read": total_rows,
            "records_imported": len(valid_rows),
            "duplicates_skipped": duplicates_count,
            "malformed_skipped": malformed_count,
            "year_range": f"{valid_rows[0]['year']} - {valid_rows[-1]['year']}" if valid_rows else "N/A"
        }
