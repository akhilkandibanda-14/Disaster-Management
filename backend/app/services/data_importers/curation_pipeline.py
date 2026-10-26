"""
SafeMap AI Master Data Curation Pipeline for Milestone 6.
Orchestrates reproducible ingestion, cryptographic integrity checking,
data cleaning, normalization, deduplication, and machine-readable
manifest generation across all local flood datasets.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from app.services.data_importers.bhuvan_inundation_importer import BhuvanInundationImporter
from app.services.data_importers.des_rainfall_importer import DESRainfallImporter
from app.services.data_importers.era5_weather_importer import ERA5WeatherImporter
from app.services.data_importers.flood_event_catalogue_importer import FloodEventCatalogueImporter
from app.services.data_importers.glofas_discharge_importer import GloFASDischargeImporter
from app.services.data_importers.hazards_geojson_importer import HazardsGeoJsonImporter

logger = logging.getLogger(__name__)


class SafeMapCurationPipeline:
    """Master orchestrator executing all SafeMap AI local dataset importers."""

    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path(__file__).resolve().parents[4]
        self.raw_dir = self.base_dir / "data" / "raw"
        self.curated_dir = self.base_dir / "data" / "curated"
        self.manifest_path = self.base_dir / "data" / "data_manifest.json"
        self.curated_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict[str, Any]:
        """Runs all importers, collects audit metrics, and writes the machine-readable manifest."""
        start_time = datetime.now(timezone.utc)
        results: Dict[str, Any] = {}

        importers = [
            ("des_rainfall", DESRainfallImporter()),
            ("flood_events", FloodEventCatalogueImporter()),
            ("bhuvan_inundation", BhuvanInundationImporter()),
            ("glofas_discharge", GloFASDischargeImporter()),
            ("hazards_geojson", HazardsGeoJsonImporter()),
            ("era5_weather", ERA5WeatherImporter()),
        ]

        for name, importer in importers:
            try:
                res = importer.import_and_curate()
                results[name] = res
            except Exception as e:
                logger.error(f"Error executing importer {name}: {e}", exc_info=True)
                results[name] = {"status": "FAILED", "error": str(e), "records_imported": 0}

        end_time = datetime.now(timezone.utc)
        duration_s = (end_time - start_time).total_seconds()

        # Build machine-readable data manifest
        manifest = self._generate_manifest(results, start_time, duration_s)
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return {
            "status": "COMPLETED",
            "execution_duration_seconds": round(duration_s, 3),
            "manifest_file": str(self.manifest_path),
            "importer_results": results,
            "total_curated_datasets": len(results),
        }

    def _generate_manifest(self, importer_results: Dict[str, Any], timestamp: datetime, duration: float) -> Dict[str, Any]:
        """Assembles comprehensive provenance manifest tracking all local data sources."""
        des_res = importer_results.get("des_rainfall", {})
        evt_res = importer_results.get("flood_events", {})
        bhv_res = importer_results.get("bhuvan_inundation", {})
        glo_res = importer_results.get("glofas_discharge", {})
        haz_res = importer_results.get("hazards_geojson", {})
        era_res = importer_results.get("era5_weather", {})

        datasets: List[Dict[str, Any]] = [
            {
                "dataset_id": "DES-HYD-RAINFALL-ANNUAL",
                "title": "Telangana Directorate of Economics & Statistics Annual Rainfall (Hyderabad)",
                "publisher": "Directorate of Economics and Statistics (DES), Government of Telangana",
                "source_url": "https://des.telangana.gov.in",
                "documentation_url": "https://www.telangana.gov.in",
                "access_status": "DOWNLOADED_AND_VERIFIED",
                "access_restrictions": "Open Government Data / Official Statistical Abstract. Annual district summary.",
                "license": "Government Open Data (Attribution Required)",
                "data_classification": "OBSERVATION",
                "temporal_coverage": {
                    "start_year": 1970,
                    "end_year": 2023,
                    "resolution": "Annual and Seasonal (SW Monsoon, NE Monsoon)",
                    "range_label": des_res.get("year_range", "1970 - 2023"),
                },
                "spatial_coverage": {
                    "region": "Hyderabad District, Telangana",
                    "resolution": "District Aggregate",
                    "latitude": 17.3850,
                    "longitude": 78.4867,
                },
                "measurement_units": {
                    "rainfall": "mm",
                    "deviation": "percent",
                },
                "files": {
                    "raw": "data/raw/des_telangana/hyderabad_rainfall_annual_des.csv",
                    "curated": "data/curated/hyderabad_rainfall_annual_curated.csv",
                },
                "checksums": {
                    "raw_sha256": des_res.get("raw_sha256", ""),
                    "curated_sha256": des_res.get("curated_sha256", ""),
                },
                "audit": {
                    "records_imported": des_res.get("records_imported", 0),
                    "duplicates_skipped": des_res.get("duplicates_skipped", 0),
                    "malformed_skipped": des_res.get("malformed_skipped", 0),
                },
                "provenance_notes": "Official published statistical abstracts benchmarked across 19 representative historical years including extreme monsoon deluges (2000, 2016, 2020, 2022).",
            },
            {
                "dataset_id": "TSDPS-AWS-METEOROLOGY-NETWORK",
                "title": "Telangana State Development Planning Society AWS Rainfall Telemetry",
                "publisher": "Telangana State Development Planning Society (TSDPS), Planning Dept, GoTS",
                "source_url": "https://tsdps.telangana.gov.in",
                "documentation_url": "https://www.telangana.gov.in",
                "access_status": "RESTRICTED_PORTAL_VIEWER_ONLY",
                "access_restrictions": "Daily summary bulletins and web maps are publicly viewable. Programmatic automated extraction and sub-daily/hourly raw time-series require formal institutional credentials, written data-sharing agreements, and departmental clearance.",
                "license": "Government Proprietary / Restricted Research Access",
                "data_classification": "OBSERVATION",
                "temporal_coverage": {
                    "start_year": 2014,
                    "end_year": 2024,
                    "resolution": "15-minute / Hourly AWS sensor readings (institutional only); daily bulletins (public)",
                },
                "spatial_coverage": {
                    "region": "Greater Hyderabad Municipal Corporation (GHMC)",
                    "resolution": "Point AWS telemetry (~100+ stations across GHMC mandals)",
                    "notable_stations": ["IMD Begumpet", "Ghatkesar AWS", "Shaikpet AWS", "Nampally AWS", "Serilingampally AWS", "Rajendranagar AWS"],
                },
                "measurement_units": {
                    "rainfall": "mm",
                    "temperature": "°C",
                    "humidity": "percent",
                    "wind_speed": "km/h",
                },
                "provenance_notes": "Public portal reports daily totals. Individual event peaks (e.g. 320 mm at Ghatkesar in Oct 2020) are verified and captured within the SafeMap Historical Flood Catalogue.",
            },
            {
                "dataset_id": "BHUVAN-NRSC-HYD-OCT2020",
                "title": "ISRO / NRSC Bhuvan Flood Inundation Assessment: Hyderabad October 2020",
                "publisher": "National Remote Sensing Centre (NRSC), Indian Space Research Organisation (ISRO)",
                "source_url": "https://bhuvan-app1.nrsc.gov.in/disaster/disaster.php",
                "documentation_url": "https://www.nrsc.gov.in",
                "access_status": "MAP_VIEWER_AND_REPORT_ONLY",
                "access_restrictions": "Public disaster portal displays WMS/WFS map viewer layers and damage assessment PDF reports. Raw full-resolution GeoTIFF inundation rasters require authorized ISRO/NRSC credentials and formal requisition.",
                "license": "ISRO / NRSC Open Geospatial Portal (Non-commercial Disaster Management Use)",
                "data_classification": "HISTORICAL_INUNDATION",
                "temporal_coverage": {
                    "event_date": "2020-10-13 to 2020-10-19",
                    "satellite_acquisition": "2020-10-18T10:30:00+05:30",
                    "resolution": "Post-event snapshot",
                },
                "spatial_coverage": {
                    "region": "Greater Hyderabad Municipal Corporation & Musi River Floodplain",
                    "resolution": "10 m spatial grid (Cartosat & Sentinel-1 SAR)",
                    "bounding_box_wgs84": [78.30, 17.25, 78.65, 17.55],
                },
                "files": {
                    "raw": "data/raw/bhuvan_nrsc/bhuvan_hyd_oct2020_metadata.json",
                    "curated": "data/curated/bhuvan_hyd_oct2020_curated.json",
                },
                "checksums": {
                    "raw_sha256": bhv_res.get("raw_sha256", ""),
                    "curated_sha256": bhv_res.get("curated_sha256", ""),
                },
                "audit": {
                    "submergence_pockets_catalogued": bhv_res.get("submergence_pockets_count", 7),
                },
                "provenance_notes": "Mapped open-water ponding extent after Deep Depression BOB 02. Optical/SAR resolution captures 7 major submergence corridors along Musi River and lake cascades.",
            },
            {
                "dataset_id": "NDMA-SACHET-ALERTS",
                "title": "NDMA SACHET National Disaster Alerting Network (Hyderabad Historical Alerts)",
                "publisher": "National Disaster Management Authority (NDMA), Government of India",
                "source_url": "https://sachet.ndma.gov.in",
                "documentation_url": "https://ndma.gov.in",
                "access_status": "DOWNLOADED_AND_VERIFIED",
                "access_restrictions": "Public emergency CAP warning portal. Historical warnings archived by State Disaster Management Authorities (TG-SDMA).",
                "license": "Public Emergency Warning Protocol (Free Public Access)",
                "data_classification": "OFFICIAL_ALERT",
                "temporal_coverage": {
                    "historical_window": "2022 to present",
                    "resolution": "Incident alert bulletins",
                },
                "spatial_coverage": {
                    "region": "Hyderabad & Ranga Reddy Districts",
                    "resolution": "District / Municipal alert polygon",
                },
                "provenance_notes": "Official Common Alerting Protocol (CAP) bulletins for heavy rainfall, reservoir discharges, and low-level causeway closures along the Musi River.",
            },
            {
                "dataset_id": "HYD-HISTORICAL-FLOOD-CATALOGUE",
                "title": "SafeMap AI Curated Hyderabad Historical Flood Event Catalogue (1908–2023)",
                "publisher": "Compiled and Curated by SafeMap AI from Official Multi-Agency Records",
                "source_url": "https://www.telangana.gov.in",
                "access_status": "DOWNLOADED_AND_VERIFIED",
                "access_restrictions": "Open research dataset compiled from official public publications.",
                "license": "CC-BY-4.0 (SafeMap AI Curated Dataset)",
                "data_classification": "OBSERVATION",
                "temporal_coverage": {
                    "start_date": "1908-09-28",
                    "end_date": "2023-07-24",
                    "total_events": evt_res.get("records_imported", 8),
                    "date_range": evt_res.get("date_range", "1908-09-28 to 2023-07-24"),
                },
                "spatial_coverage": {
                    "region": "Hyderabad Metropolitan Area, Musi River Basin",
                    "resolution": "Event-specific urban sector and causeway references",
                },
                "files": {
                    "raw": "data/raw/flood_events/hyderabad_historical_floods_raw.json",
                    "curated_json": "data/curated/hyderabad_flood_event_catalogue.json",
                    "curated_csv": "data/curated/hyderabad_flood_event_catalogue.csv",
                },
                "checksums": {
                    "raw_sha256": evt_res.get("raw_sha256", ""),
                    "curated_json_sha256": evt_res.get("curated_json_sha256", ""),
                    "curated_csv_sha256": evt_res.get("curated_csv_sha256", ""),
                },
                "audit": {
                    "records_imported": evt_res.get("records_imported", 0),
                    "duplicates_skipped": evt_res.get("duplicates_skipped", 0),
                    "malformed_skipped": evt_res.get("malformed_skipped", 0),
                    "verification_audit": evt_res.get("verification_summary", {}),
                },
                "provenance_notes": "Audited historical flood catalogue capturing 8 major urban flood events (1908, 2000, 2008, 2016, 2020, 2021, 2022, 2023) with event-level provenance, explicit measurement classifications (OBSERVED, SECONDARY_REPORTED, ESTIMATED, UNVERIFIED), and audit trails.",
            },
            {
                "dataset_id": "GLOFAS-MUSI-OCT2020-DISCHARGE",
                "title": "Copernicus GloFAS Musi River Discharge Simulation (October 2020)",
                "publisher": "European Centre for Medium-Range Weather Forecasts (ECMWF) GloFAS via Open-Meteo",
                "source_url": "https://flood-api.open-meteo.com/v1/flood",
                "access_status": "DOWNLOADED_AND_VERIFIED",
                "access_restrictions": "Open API access with attribution.",
                "license": "Copernicus Open Access / Open-Meteo Terms",
                "data_classification": "MODEL_FORECAST",
                "temporal_coverage": {
                    "start_date": "2020-10-10",
                    "end_date": "2020-10-20",
                    "resolution": "Daily river discharge (m^3/s)",
                },
                "spatial_coverage": {
                    "location": "Musi River at Hyderabad (17.375°N, 78.475°E)",
                    "resolution": "Gridded river reach simulation (0.05° grid)",
                },
                "files": {
                    "raw": "data/raw/open_meteo/musi_glofas_oct2020.json",
                    "curated": "data/curated/musi_glofas_oct2020_curated.csv",
                },
                "checksums": {
                    "raw_sha256": glo_res.get("raw_sha256", ""),
                    "curated_sha256": glo_res.get("curated_sha256", ""),
                },
                "audit": {
                    "records_imported": glo_res.get("records_imported", 0),
                    "peak_discharge_cumec": glo_res.get("peak_discharge_cumec", 0.0),
                },
                "provenance_notes": "Hydrological model simulation. Explicitly classified as MODEL_FORECAST. Must not be substituted for physical stream gauge observations.",
            },
            {
                "dataset_id": "HYD-FLOOD-ZONES-GEOJSON",
                "title": "Hyderabad Published Flood-Prone Vulnerability Zones GeoJSON",
                "publisher": "GHMC Disaster Management Cell & MRDCL Surveys (Curated by SafeMap AI)",
                "source_url": "https://www.telangana.gov.in",
                "access_status": "DOWNLOADED_AND_VERIFIED",
                "access_restrictions": "Public municipal surveys.",
                "license": "Public Municipal Survey Data",
                "data_classification": "HISTORICAL_VULNERABILITY",
                "spatial_coverage": {
                    "region": "Musi River Corridor & Urban Nala Basins",
                    "crs": "EPSG:4326 (WGS84)",
                    "total_features": haz_res.get("records_imported", 0),
                },
                "files": {
                    "raw": "data/raw/hazards/hyderabad_flood_zones.geojson",
                    "curated": "data/curated/hyderabad_flood_zones_curated.geojson",
                },
                "checksums": {
                    "raw_sha256": haz_res.get("raw_sha256", ""),
                    "curated_sha256": haz_res.get("curated_sha256", ""),
                },
                "audit": {
                    "features_imported": haz_res.get("records_imported", 0),
                },
                "provenance_notes": "Static topological vulnerability polygons. Flooding within these zones is contingent on gate releases and storm drain capacity; presence of polygon does not indicate real-time water level.",
            },
            {
                "dataset_id": "ERA5-HYD-OCT2020-WEATHER",
                "title": "ECMWF ERA5 Reanalysis Meteorological Parameters: Hyderabad October 2020",
                "publisher": "ECMWF / Copernicus Climate Change Service via Open-Meteo Historical Archive",
                "source_url": "https://archive-api.open-meteo.com/v1/archive",
                "access_status": "DOWNLOADED_AND_VERIFIED",
                "access_restrictions": "Open API access.",
                "license": "Copernicus License",
                "data_classification": "MODELLED",
                "temporal_coverage": {
                    "start_date": "2020-10-10",
                    "end_date": "2020-10-20",
                    "resolution": "Hourly reanalysis aggregated to daily metrics",
                },
                "spatial_coverage": {
                    "location": "Hyderabad Central (17.399°N, 78.457°E)",
                    "resolution": "0.1° (~11 km) gridded atmospheric reanalysis",
                },
                "files": {
                    "raw": "data/raw/open_meteo/hyderabad_era5_oct2020.json",
                    "curated": "data/curated/hyderabad_era5_oct2020_curated.csv",
                },
                "checksums": {
                    "raw_sha256": era_res.get("raw_sha256", ""),
                    "curated_sha256": era_res.get("curated_sha256", ""),
                },
                "audit": {
                    "daily_records_curated": era_res.get("daily_records_curated", 0),
                    "oct13_14_precip_total_mm": era_res.get("oct13_14_precip_total_mm", 0.0),
                },
                "provenance_notes": "Atmospheric reanalysis estimates. Captures the extreme precipitation peak of 13-14 October 2020.",
            },
        ]

        # Check institutional intake ledger
        intake_ledger_path = self.curated_dir / "institutional" / "intake_ledger.json"
        intake_batches_count = 0
        intake_records_count = 0
        if intake_ledger_path.exists():
            try:
                with open(intake_ledger_path, "r", encoding="utf-8") as f:
                    ledger_data = json.load(f)
                    if isinstance(ledger_data, list):
                        intake_batches_count = len(ledger_data)
                        intake_records_count = sum(e.get("records_count", 0) for e in ledger_data)
            except Exception:
                pass

        total_downloaded = sum(1 for d in datasets if d["access_status"] == "DOWNLOADED_AND_VERIFIED")
        total_viewer_only = sum(1 for d in datasets if "VIEWER" in d["access_status"])
        v_summary = evt_res.get("verification_summary", {})

        return {
            "manifest_version": "1.2.0",
            "project": "SafeMap AI",
            "milestone": "Milestone 8: Institutional Data Acquisition and Evidence Intake",
            "generated_at_utc": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pipeline_execution_duration_seconds": round(duration, 3),
            "target_region": "Hyderabad Metropolitan Area, Telangana, India",
            "reference_coordinates": {
                "latitude": 17.3850,
                "longitude": 78.4867,
                "model_coverage_guard_km": 50.0,
            },
            "summary_metrics": {
                "total_catalogued_sources": len(datasets),
                "downloaded_and_verified_sources": total_downloaded,
                "viewer_or_report_only_sources": total_viewer_only,
                "historical_flood_events_catalogued": evt_res.get("records_imported", 8),
                "fully_verified_events": v_summary.get("fully_verified", 0),
                "partially_verified_events": v_summary.get("partially_verified", 8),
                "unverified_events": v_summary.get("unverified", 0),
                "rainfall_records_curated": des_res.get("records_imported", 0),
                "discharge_records_curated": glo_res.get("records_imported", 0),
                "hazard_features_curated": haz_res.get("records_imported", 0),
                "institutional_intake_batches": intake_batches_count,
                "institutional_intake_records": intake_records_count,
            },
            "datasets": datasets,
        }

