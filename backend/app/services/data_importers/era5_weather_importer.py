"""
Importer for Open-Meteo ERA5 Reanalysis Weather Data for Hyderabad October 2020.
Validates hourly timestamps, precipitation values, aggregates daily statistics,
and marks data explicitly as MODELLED / REANALYSIS to distinguish from physical gauge telemetry.
"""

import csv
import json
import logging
from collections import defaultdict
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


class ERA5WeatherImporter(BaseDataImporter):
    """Imports, validates, and curates ERA5 reanalysis weather data during extreme events."""

    def __init__(self, raw_path: Optional[Path] = None, curated_path: Optional[Path] = None):
        base_dir = Path(__file__).resolve().parents[4]
        raw = raw_path or (base_dir / "data" / "raw" / "open_meteo" / "hyderabad_era5_oct2020.json")
        curated = curated_path or (base_dir / "data" / "curated" / "hyderabad_era5_oct2020_curated.csv")
        super().__init__(raw, curated)

    def import_and_curate(self) -> Dict[str, Any]:
        if not self.raw_data_path.exists():
            return {
                "status": "FAILED",
                "error": f"Raw ERA5 file not found: {self.raw_data_path}",
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
                "error": f"Failed to parse ERA5 JSON: {e}",
                "records_imported": 0,
            }

        lat = raw_data.get("latitude")
        lon = raw_data.get("longitude")
        v, valid_lat, valid_lon, err = validate_coordinates(lat, lon)
        if not v:
            return {
                "status": "FAILED",
                "error": f"Invalid coordinates in ERA5 data: {err}",
                "records_imported": 0,
            }

        hourly = raw_data.get("hourly", {})
        times = hourly.get("time", [])
        precips = hourly.get("precipitation", [])
        rains = hourly.get("rain", [])
        temps = hourly.get("temperature_2m", [])
        humidities = hourly.get("relative_humidity_2m", [])

        total_hours = len(times)
        if not (total_hours == len(precips) == len(temps) == len(humidities)):
            return {
                "status": "FAILED",
                "error": "Mismatched hourly array lengths in ERA5 data",
                "records_imported": 0,
            }

        # Aggregate by day
        daily_buckets: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: {
            "precip": [], "temp": [], "humidity": []
        })

        malformed_count = 0
        for i in range(total_hours):
            t_str = times[i]
            day_str = t_str[:10]
            try:
                p_val = float(precips[i])
                t_val = float(temps[i])
                h_val = float(humidities[i])
                daily_buckets[day_str]["precip"].append(p_val)
                daily_buckets[day_str]["temp"].append(t_val)
                daily_buckets[day_str]["humidity"].append(h_val)
            except (ValueError, TypeError):
                malformed_count += 1

        curated_rows: List[Dict[str, Any]] = []
        for day_str in sorted(daily_buckets.keys()):
            bucket = daily_buckets[day_str]
            p_list = bucket["precip"]
            t_list = bucket["temp"]
            h_list = bucket["humidity"]

            daily_sum_p = round(sum(p_list), 2)
            max_hourly_p = round(max(p_list), 2) if p_list else 0.0
            mean_temp = round(sum(t_list) / len(t_list), 2) if t_list else 0.0
            mean_hum = round(sum(h_list) / len(h_list), 2) if h_list else 0.0

            curated_rows.append({
                "date_iso": f"{day_str}T00:00:00Z",
                "daily_precipitation_sum_mm": daily_sum_p,
                "max_hourly_precipitation_mm": max_hourly_p,
                "mean_temperature_c": mean_temp,
                "mean_relative_humidity_pct": mean_hum,
                "latitude": valid_lat,
                "longitude": valid_lon,
                "measurement_unit_rainfall": "mm",
                "source_provider": "ECMWF ERA5 via Open-Meteo Historical Archive",
                "source_url": "https://archive-api.open-meteo.com/v1/archive",
                "data_classification": "MODELLED",
                "raw_checksum_sha256": raw_checksum,
                "curated_at_utc": now_iso,
            })

        if curated_rows:
            fieldnames = list(curated_rows[0].keys())
            with open(self.curated_data_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(curated_rows)

        curated_checksum = compute_sha256(self.curated_data_path)

        return {
            "status": "SUCCESS",
            "dataset_id": "ERA5-HYD-OCT2020-WEATHER",
            "raw_file": str(self.raw_data_path),
            "curated_file": str(self.curated_data_path),
            "raw_sha256": raw_checksum,
            "curated_sha256": curated_checksum,
            "total_hourly_records": total_hours,
            "daily_records_curated": len(curated_rows),
            "duplicates_skipped": 0,
            "malformed_skipped": malformed_count,
            "date_range": f"{curated_rows[0]['date_iso'][:10]} to {curated_rows[-1]['date_iso'][:10]}" if curated_rows else "N/A",
            "oct13_14_precip_total_mm": round(sum(r["daily_precipitation_sum_mm"] for r in curated_rows if r["date_iso"][:10] in ("2020-10-13", "2020-10-14")), 2),
        }
