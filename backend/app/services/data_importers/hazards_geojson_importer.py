"""
Importer and validator for Hyderabad flood vulnerability zones GeoJSON.
Validates FeatureCollection structure, coordinate reference system (WGS84),
closed Polygon rings, attributes, and data classifications.
"""

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
    validate_geojson_geometry,
)

logger = logging.getLogger(__name__)


class HazardsGeoJsonImporter(BaseDataImporter):
    """Imports, validates, and curates published flood hazard zones GeoJSON."""

    def __init__(self, raw_path: Optional[Path] = None, curated_path: Optional[Path] = None):
        base_dir = Path(__file__).resolve().parents[4]
        raw = raw_path or (base_dir / "data" / "raw" / "hazards" / "hyderabad_flood_zones.geojson")
        curated = curated_path or (base_dir / "data" / "curated" / "hyderabad_flood_zones_curated.geojson")
        super().__init__(raw, curated)

    def import_and_curate(self) -> Dict[str, Any]:
        if not self.raw_data_path.exists():
            return {
                "status": "FAILED",
                "error": f"Raw hazards file not found: {self.raw_data_path}",
                "records_imported": 0,
            }

        raw_checksum = compute_sha256(self.raw_data_path)
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            with open(self.raw_data_path, "r", encoding="utf-8") as f:
                raw_geojson = json.load(f)
        except Exception as e:
            return {
                "status": "FAILED",
                "error": f"Failed to parse GeoJSON: {e}",
                "records_imported": 0,
            }

        if raw_geojson.get("type") != "FeatureCollection":
            return {
                "status": "FAILED",
                "error": "Root GeoJSON must be of type FeatureCollection",
                "records_imported": 0,
            }

        features = raw_geojson.get("features", [])
        valid_features: List[Dict[str, Any]] = []
        duplicates_count = 0
        malformed_count = 0
        self.seen_keys.clear()

        for idx, feat in enumerate(features):
            if not isinstance(feat, dict) or feat.get("type") != "Feature":
                malformed_count += 1
                continue

            props = feat.get("properties", {})
            geom = feat.get("geometry", {})

            hazard_id = props.get("hazard_id") or feat.get("id")
            if not hazard_id:
                malformed_count += 1
                continue
            hazard_id = str(hazard_id).strip()

            if hazard_id in self.seen_keys:
                duplicates_count += 1
                continue
            self.seen_keys.add(hazard_id)

            # Validate geometry
            valid_geom, geom_err = validate_geojson_geometry(geom)
            if not valid_geom:
                logger.warning(f"Invalid geometry in hazard {hazard_id}: {geom_err}")
                malformed_count += 1
                continue

            # Validate classifications
            raw_status = props.get("data_status", "PUBLIC_UNVERIFIED")
            valid_cls, norm_status = validate_data_classification(raw_status)
            if not valid_cls:
                norm_status = "PUBLIC_UNVERIFIED"

            pub_date = normalize_iso_timestamp(props.get("published_date"))

            curated_props = dict(props)
            curated_props["hazard_id"] = hazard_id
            curated_props["data_status"] = norm_status
            curated_props["published_date_iso"] = pub_date
            curated_props["crs"] = "EPSG:4326 (WGS84)"
            curated_props["data_classification"] = "HISTORICAL_VULNERABILITY"
            curated_props["raw_checksum_sha256"] = raw_checksum
            curated_props["curated_at_utc"] = now_iso

            valid_features.append({
                "type": "Feature",
                "id": hazard_id,
                "properties": curated_props,
                "geometry": geom,
            })

        curated_geojson = {
            "type": "FeatureCollection",
            "metadata": {
                "dataset_id": "HYD-FLOOD-ZONES-GEOJSON",
                "title": "Curated Hyderabad Published Flood-Prone Vulnerability Zones",
                "publisher": "GHMC Disaster Management Cell & MRDCL (Curated by SafeMap AI)",
                "data_classification": "HISTORICAL_VULNERABILITY",
                "data_status": "PUBLIC_UNVERIFIED",
                "crs": "urn:ogc:def:crs:OGC:1.3:CRS84",
                "raw_checksum_sha256": raw_checksum,
                "curated_at_utc": now_iso,
                "total_features": len(valid_features),
            },
            "features": valid_features,
        }

        with open(self.curated_data_path, "w", encoding="utf-8") as f:
            json.dump(curated_geojson, f, indent=2)

        curated_checksum = compute_sha256(self.curated_data_path)

        return {
            "status": "SUCCESS",
            "dataset_id": "HYD-FLOOD-ZONES-GEOJSON",
            "raw_file": str(self.raw_data_path),
            "curated_file": str(self.curated_data_path),
            "raw_sha256": raw_checksum,
            "curated_sha256": curated_checksum,
            "total_items_read": len(features),
            "records_imported": len(valid_features),
            "duplicates_skipped": duplicates_count,
            "malformed_skipped": malformed_count,
        }
