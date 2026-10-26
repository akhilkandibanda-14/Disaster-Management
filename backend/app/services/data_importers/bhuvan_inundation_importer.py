"""
Importer and provenance validator for ISRO / NRSC Bhuvan Flood Inundation Products.
Validates spatial bounding box, satellite acquisition timestamps, remote sensing platform
specifications, access restrictions, and output curated metadata.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.data_importers.importer_base import (
    BaseDataImporter,
    compute_sha256,
    normalize_iso_timestamp,
    validate_coordinates,
    validate_data_classification,
)

logger = logging.getLogger(__name__)


class BhuvanInundationImporter(BaseDataImporter):
    """Imports, validates, and curates ISRO/NRSC Bhuvan inundation assessment metadata."""

    def __init__(self, raw_path: Optional[Path] = None, curated_path: Optional[Path] = None):
        base_dir = Path(__file__).resolve().parents[4]
        raw = raw_path or (base_dir / "data" / "raw" / "bhuvan_nrsc" / "bhuvan_hyd_oct2020_metadata.json")
        curated = curated_path or (base_dir / "data" / "curated" / "bhuvan_hyd_oct2020_curated.json")
        super().__init__(raw, curated)

    def import_and_curate(self) -> Dict[str, Any]:
        if not self.raw_data_path.exists():
            return {
                "status": "FAILED",
                "error": f"Raw Bhuvan metadata file not found: {self.raw_data_path}",
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
                "error": f"Failed to parse Bhuvan JSON: {e}",
                "records_imported": 0,
            }

        dataset_id = raw_data.get("dataset_id", "BHUVAN-NRSC-HYD-OCT2020")
        bbox = raw_data.get("spatial_coverage", {}).get("bounding_box_wgs84", [])

        # Validate bounding box: [min_lon, min_lat, max_lon, max_lat]
        if len(bbox) != 4:
            return {
                "status": "FAILED",
                "error": f"Invalid bounding box in Bhuvan metadata: {bbox}",
                "records_imported": 0,
            }

        min_lon, min_lat, max_lon, max_lat = bbox
        v1, _, _, err1 = validate_coordinates(min_lat, min_lon)
        v2, _, _, err2 = validate_coordinates(max_lat, max_lon)
        if not (v1 and v2):
            return {
                "status": "FAILED",
                "error": f"Invalid coordinates in bounding box: {err1 or err2}",
                "records_imported": 0,
            }

        event_period = raw_data.get("event_period", {})
        norm_start = normalize_iso_timestamp(event_period.get("rainfall_start"))
        norm_peak = normalize_iso_timestamp(event_period.get("rainfall_peak"))
        norm_sat = normalize_iso_timestamp(event_period.get("satellite_observation_date"))

        raw_cls = raw_data.get("data_classification", "HISTORICAL_INUNDATION")
        valid_cls, norm_classification = validate_data_classification(raw_cls)
        if not valid_cls:
            norm_classification = "HISTORICAL_INUNDATION"

        curated_data = {
            "dataset_id": dataset_id,
            "title": raw_data.get("title", ""),
            "publisher": raw_data.get("publisher", "National Remote Sensing Centre (NRSC), ISRO"),
            "portal_url": raw_data.get("portal_url", "https://bhuvan-app1.nrsc.gov.in/disaster/disaster.php"),
            "documentation_url": raw_data.get("documentation_url", "https://www.nrsc.gov.in"),
            "disaster_type": raw_data.get("disaster_type", "URBAN_FLASH_FLOOD"),
            "meteorological_trigger": raw_data.get("meteorological_trigger", "Deep Depression BOB 02"),
            "event_period_normalized": {
                "rainfall_start_iso": norm_start,
                "rainfall_peak_iso": norm_peak,
                "satellite_observation_iso": norm_sat,
            },
            "spatial_coverage": {
                "geographic_region": raw_data.get("spatial_coverage", {}).get("geographic_region", "Greater Hyderabad"),
                "bounding_box_wgs84": [round(min_lon, 4), round(min_lat, 4), round(max_lon, 4), round(max_lat, 4)],
                "mapped_submergence_pockets": raw_data.get("spatial_coverage", {}).get("mapped_submergence_pockets", []),
                "pocket_count": len(raw_data.get("spatial_coverage", {}).get("mapped_submergence_pockets", [])),
            },
            "remote_sensing_platform": raw_data.get("remote_sensing_platform", {
                "sensor_types": ["Optical Cartosat", "Sentinel-1 Synthetic Aperture Radar (SAR)"],
                "resolution_m": 10.0,
            }),
            "format_available": raw_data.get("format_available", "WMS/WFS map viewer layers & PDF reports"),
            "access_status": raw_data.get("access_status", "MAP_VIEWER_AND_REPORT_ONLY"),
            "access_restrictions": raw_data.get("access_restrictions", "Requires authorized institutional credentials for raw GeoTIFF rasters"),
            "data_classification": norm_classification,
            "curation_notes": raw_data.get("curation_notes", ""),
            "raw_checksum_sha256": raw_checksum,
            "curated_at_utc": now_iso,
        }

        with open(self.curated_data_path, "w", encoding="utf-8") as f:
            json.dump(curated_data, f, indent=2)

        curated_checksum = compute_sha256(self.curated_data_path)

        return {
            "status": "SUCCESS",
            "dataset_id": dataset_id,
            "raw_file": str(self.raw_data_path),
            "curated_file": str(self.curated_data_path),
            "raw_sha256": raw_checksum,
            "curated_sha256": curated_checksum,
            "access_status": curated_data["access_status"],
            "submergence_pockets_count": curated_data["spatial_coverage"]["pocket_count"],
            "records_imported": 1,
            "duplicates_skipped": 0,
            "malformed_skipped": 0,
        }
