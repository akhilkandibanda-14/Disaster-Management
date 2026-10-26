# SafeMap AI — Local Flood Data Source and Dataset Inventory

**Document Version**: 1.0.0  
**Target Region**: Greater Hyderabad Municipal Corporation (GHMC) and Musi River Catchment, Telangana, India  
**Reference Coordinates**: `17.3850° N, 78.4867° E`  
**Model-Coverage Guard**: 50.0 km radius invariant strictly enforced  
**Assessment Date**: 2026-10-24  
**Pipeline Manifest**: [`data/data_manifest.json`](../data/data_manifest.json)  

---

## 1. Executive Summary & Objective

In accordance with Milestone 6, SafeMap AI establishes a reproducible, source-traceable inventory of public hydrological, meteorological, and flood-inundation evidence relevant to Hyderabad, Telangana. 

### Core Scientific Directive
> [!IMPORTANT]
> **Data Readiness Rule:** A successful data import must **never** be equated with model readiness. An automated flood-prediction model for Hyderabad must **not** be promised or deployed until continuous, localized observational evidence genuinely supports it.

The current production machine learning model is conditioned upon the Central Water Commission (CWC) **INDOFLOODS** dataset. The nearest INDOFLOODS gauge is **INDOFLOODS-gauge-916** at **71.77 km** distance on the River Manjra (**Godavari Basin**), whereas Hyderabad lies in the **Musi River Catchment (Krishna Basin)**. Because this exceeds the 50.0 km model-coverage guard, SafeMap AI retains the transparent `MODEL_UNSUPPORTED` state for Hyderabad.

---

## 2. Public Source Investigation & Access Status Audit

Every identified data source was investigated for actual availability, data format, spatial resolution, temporal span, licensing terms, and access restrictions.

| Source ID | Source Agency & Name | Primary Portal URL | Access Status | Data Classification | Geographic Resolution | Time Horizon | License / Terms |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DES-HYD** | Telangana Directorate of Economics and Statistics (DES) | [des.telangana.gov.in](https://des.telangana.gov.in) | **DOWNLOADED_AND_VERIFIED** | `OBSERVATION` | Hyderabad District Aggregate | 1970–2023 (Annual & Seasonal) | Open Government Data (Attribution required) |
| **TSDPS-AWS** | Telangana State Development Planning Society (TSDPS) | [tsdps.telangana.gov.in](https://tsdps.telangana.gov.in) | **RESTRICTED_PORTAL_VIEWER_ONLY** | `OBSERVATION` | Point AWS (~100+ stations in GHMC) | 2014–Present (15-min / Hourly) | Restricted; Institutional permission & NDA required for raw time-series |
| **BHUVAN-NRSC** | ISRO / NRSC Disaster Management Geoportal (Bhuvan) | [bhuvan-app1.nrsc.gov.in](https://bhuvan-app1.nrsc.gov.in/disaster/disaster.php) | **MAP_VIEWER_AND_REPORT_ONLY** | `HISTORICAL_INUNDATION` | 10 m grid (Cartosat & Sentinel-1 SAR) | Oct 18, 2020 (Single post-event snapshot) | ISRO Open Viewer; GeoTIFF rasters require nodal credentials |
| **NDMA-SACHET** | National Disaster Management Authority (NDMA) SACHET | [sachet.ndma.gov.in](https://sachet.ndma.gov.in) | **DOWNLOADED_AND_VERIFIED** | `OFFICIAL_ALERT` | District / Sub-district Alert Polygon | 2022–Present (Event incidents) | Public Disaster Alert Protocol (CAP) |
| **CWC-INDOFLOODS** | Central Water Commission (CWC) National River Gauges | [indiawris.gov.in](https://indiawris.gov.in) | **GEOGRAPHICALLY_EXCLUDED** | `OBSERVATION` | Catchment / Stream Gauge | 1970–2020 | Research Open Access (No gauges within 50 km of Hyderabad) |
| **GLOFAS-MUSI** | Copernicus GloFAS via Open-Meteo Flood API | [flood-api.open-meteo.com](https://flood-api.open-meteo.com/v1/flood) | **DOWNLOADED_AND_VERIFIED** | `MODEL_FORECAST` | 0.05° Gridded Reach (17.375°N, 78.475°E) | Oct 10–20, 2020 (Daily discharge) | Copernicus Open Access (Uncalibrated model output) |
| **ERA5-HYD** | ECMWF ERA5 Reanalysis via Open-Meteo Archive | [archive-api.open-meteo.com](https://archive-api.open-meteo.com/v1/archive) | **DOWNLOADED_AND_VERIFIED** | `MODELLED` | 0.1° (~11 km) Grid (17.399°N, 78.457°E) | Oct 10–20, 2020 (Hourly / Daily) | Copernicus Climate Change Service |
| **GHMC-ZONES** | GHMC Disaster Management & MRDCL Flood Zones | [telangana.gov.in](https://www.telangana.gov.in) | **DOWNLOADED_AND_VERIFIED** | `HISTORICAL_VULNERABILITY` | Survey Polygons (WGS84) | 2024 Survey Benchmark | Public Municipal Survey Data (`PUBLIC_UNVERIFIED`) |

---

## 3. Detailed Source Breakdown & Technical Characteristics

### 3.1. Telangana Directorate of Economics and Statistics (DES)
- **Publisher**: Directorate of Economics and Statistics, Planning Department, Government of Telangana.
- **Publication**: *Telangana State Statistical Abstract* & Annual District Rainfall Tables.
- **Physical Availability**: Published tables in annual statistical abstracts, digitized and archived by SafeMap AI as CSV.
- **Spatial Resolution**: District-level aggregate for Hyderabad District (area: ~217 km²).
- **Temporal Coverage**: 19 historical benchmarks spanning 1970 to 2023, capturing normal rainfall, actual recorded rainfall, percentage deviation, and seasonal splits (Southwest Monsoon June–September; Northeast Monsoon October–December).
- **Data Classification**: `OBSERVATION`.
- **Known Limitations**:
  - District aggregates obscure severe localized convective bursts. A station in Ghatkesar may record 320 mm in 24 hours while western Hyderabad records 60 mm; the district aggregate averages these out.
  - No sub-daily (hourly) rainfall metrics are available in the annual statistical abstract.

### 3.2. Telangana State Development Planning Society (TSDPS)
- **Publisher**: Telangana State Development Planning Society, Government of Telangana.
- **Network Architecture**: High-density urban Automatic Weather Station (AWS) network featuring ~100+ telemetry stations across GHMC mandals (e.g., Begumpet, Shaikpet, Nampally, Ghatkesar, Serilingampally, Khairatabad).
- **Operational Reality & Access Barriers**:
  - **Public Tier**: Daily bulletin PDFs, monthly district rain summaries, and web maps showing current 24-hour accumulations are publicly viewable on `https://tsdps.telangana.gov.in`.
  - **Restricted Tier**: High-frequency 15-minute and 1-hour raw tabular time series are **not** exposed via an open REST API. Access requires formal institutional credentials, written data-sharing agreements, and departmental authorization.
  - **Scraping Prohibition**: SafeMap AI strictly complies with site access guidelines and does **not** attempt to scrape authenticated portals or bypass credentials.
- **Data Classification**: `OBSERVATION` (when sourced from official bulletins).

### 3.3. ISRO / NRSC Bhuvan Flood Inundation Products
- **Publisher**: National Remote Sensing Centre (NRSC), Indian Space Research Organisation (ISRO).
- **Product Title**: Satellite Inundation Assessment for Hyderabad Flash Floods (October 2020 Event).
- **Sensor Suite**: Optical Cartosat-1/2 and Sentinel-1 C-band Synthetic Aperture Radar (SAR) with 10 m spatial resolution.
- **Spatial Bounds**: `[78.30°E, 17.25°N]` to `[78.65°E, 17.55°N]`, encompassing GHMC and the Musi River corridor.
- **Access Status**:
  - Publicly accessible as interactive Web Map Service (WMS/WFS) visual layers and disaster evaluation damage reports.
  - Raw full-resolution GIS GeoTIFF inundation masks require formal nodal credentials via the NDMA/Disaster Management Support Programme.
- **Data Classification**: `HISTORICAL_INUNDATION`.
- **Critical Sensor Constraints**:
  - Optical sensors cannot penetrate cloud cover during active cyclones (Deep Depression BOB 02).
  - SAR observation was captured on **18 October 2020**, approximately 4 days after the peak flood wave (13–14 October). Significant flood waters had already drained, capturing only persistent ponding in low-lying lake beds and causeways.
  - Urban building shadows and dense tree canopy cause false negatives in street-level flood detection.

### 3.4. NDMA SACHET National Alerting Portal
- **Publisher**: National Disaster Management Authority (NDMA), Government of India.
- **Standard**: ITU-T X.1303 Common Alerting Protocol (CAP) XML/JSON feeds.
- **Operational Function**: Disseminates official geo-targeted warnings for extreme rainfall, flash floods, and reservoir discharge gates.
- **Data Classification**: `OFFICIAL_ALERT`.
- **Limitation**: Primarily oriented toward real-time broadcasts. Historical alerts are retained in state disaster management authority logs (TG-SDMA), but comprehensive multi-year historical alert databases require state-level archive retrieval.

### 3.5. Copernicus GloFAS River Discharge Simulation
- **Publisher**: European Centre for Medium-Range Weather Forecasts (ECMWF) via Open-Meteo Flood API.
- **Spatial Resolution**: 0.05° (~5 km) gridded river network reach at `17.375°N, 78.475°E` (Musi River).
- **Temporal Resolution**: Daily river discharge in cubic meters per second ($m^3/s$).
- **Data Classification**: `MODEL_FORECAST` / `MODELLED`.
- **Safety Directive**:
  > [!WARNING]
  > GloFAS river discharge values are uncalibrated global hydrological model estimates. Because the local Musi River rating curves, urban stormwater outfalls, and dam gate operations (Osman Sagar, Himayat Sagar) are not assimilated into the global model, **GloFAS output must NEVER be presented to citizens as physical stream gauge measurements.**

---

## 4. Machine-Readable Data Manifest Architecture

The complete data manifest is stored at [`data/data_manifest.json`](../data/data_manifest.json) and generated automatically by `SafeMapCurationPipeline`.

### Tracked Metadata Fields for Every Dataset
For every curated dataset, SafeMap AI tracks:
1. `dataset_id`: Unique alphanumeric identifier (e.g., `HYD-HISTORICAL-FLOOD-CATALOGUE`).
2. `title`: Official dataset title.
3. `publisher`: Publishing authority or agency.
4. `source_url`: Verified public source URL.
5. `access_status`: Explicit status (`DOWNLOADED_AND_VERIFIED`, `MAP_VIEWER_AND_REPORT_ONLY`, `RESTRICTED_PORTAL_VIEWER_ONLY`, `GEOGRAPHICALLY_EXCLUDED`).
6. `access_restrictions`: Legal or technical barriers to acquisition.
7. `data_classification`: Semantic provenance category (`OBSERVATION`, `OFFICIAL_ALERT`, `HISTORICAL_INUNDATION`, `HISTORICAL_VULNERABILITY`, `MODELLED`, `MODEL_FORECAST`, `PUBLIC_UNVERIFIED`, `DEMO`).
8. `files`: File paths for both `raw` and `curated` assets.
9. `checksums`: SHA-256 hashes for both raw source files and curated outputs to guarantee cryptographic reproducibility.
10. `audit`: Number of valid records imported, duplicates skipped, and malformed rows rejected.

---

## 5. Storage Directory Structure

```text
Disaster-Management/
├── data/
│   ├── data_manifest.json                      <-- Machine-readable provenance manifest
│   ├── raw/                                    <-- Raw, immutable source files
│   │   ├── bhuvan_nrsc/
│   │   │   └── bhuvan_hyd_oct2020_metadata.json
│   │   ├── des_telangana/
│   │   │   └── hyderabad_rainfall_annual_des.csv
│   │   ├── flood_events/
│   │   │   └── hyderabad_historical_floods_raw.json
│   │   ├── hazards/
│   │   │   └── hyderabad_flood_zones.geojson
│   │   ├── open_meteo/
│   │   │   ├── hyderabad_era5_oct2020.json
│   │   │   └── musi_glofas_oct2020.json
│   │   ├── emergency_facilities/
│   │   │   └── hyderabad_emergency_facilities.csv
│   │   ├── roads/
│   │   │   └── hyderabad_road_network.graphml
│   │   └── shelters/
│   │       └── hyderabad_shelters.csv
│   └── curated/                                <-- Normalized, validated, deduplicated files
│       ├── bhuvan_hyd_oct2020_curated.json
│       ├── hyderabad_era5_oct2020_curated.csv
│       ├── hyderabad_flood_event_catalogue.csv
│       ├── hyderabad_flood_event_catalogue.json
│       ├── hyderabad_flood_zones_curated.geojson
│       ├── hyderabad_rainfall_annual_curated.csv
│       └── musi_glofas_oct2020_curated.csv
```

---

## 6. Manual Acquisition Protocols for Restricted Sources

Where sources are accessible only via map viewers or require institutional authorization, SafeMap AI documents the protocol for future researchers rather than manufacturing artificial data:

### Protocol A: TSDPS AWS Sub-Daily Raw Time-Series Requisition
1. **Target Authority**: Director, Telangana State Development Planning Society, Planning Department, Secretariat, Hyderabad.
2. **Requisition Type**: Institutional Research Data Request for Urban Flood Modeling and Disaster Management.
3. **Target Parameters**: 15-minute tipping-bucket rainfall (mm), 1-hour ambient temperature (°C), relative humidity (%), wind speed (km/h) for the period 2014–2024 across 102 GHMC AWS stations.
4. **Draft Request Template**: [`docs/data_requests/template_tsdps_aws_rainfall.md`](data_requests/template_tsdps_aws_rainfall.md).

### Protocol B: ISRO / NRSC Full-Resolution SAR Inundation Rasters
1. **Target Authority**: General Manager, Disaster Management Support Programme (DMSP), National Remote Sensing Centre (NRSC), Balanagar, Hyderabad.
2. **Requisition Type**: Formal requisition through State Disaster Management Authority (TG-SDMA) or academic MoA.
3. **Target Product**: Sentinel-1 / Cartosat Level-3 GeoTIFF flood inundation extent rasters (10 m grid) for October 13–20, 2020, July 2022, and July 2023 flood windows.
4. **Draft Request Template**: [`docs/data_requests/template_nrsc_bhuvan_sar_inundation.md`](data_requests/template_nrsc_bhuvan_sar_inundation.md).

### Protocol C: Telangana Irrigation & CAD Musi River Stage & Reservoir Outflow Logs
1. **Target Authority**: Chief Engineer (Hydrology & Dam Safety), Irrigation & CAD Department, Jalasoudha, Errum Manzil, Hyderabad.
2. **Requisition Type**: Hydrometric research requisition for urban river modeling and causeway submergence.
3. **Target Parameters**: Hourly water stage (feet/meters MSL), inflow, and gate discharge logs (cusecs) for Osman Sagar, Himayat Sagar, and Musi River causeways (Moosarambagh, Chaderghat, Afzalgunj).
4. **Draft Request Template**: [`docs/data_requests/template_irrigation_musi_river_stage_and_discharge.md`](data_requests/template_irrigation_musi_river_stage_and_discharge.md).

### Protocol D: Negative-Control Multi-Year Baseline & Municipal Logs
1. **Target Authorities**: India Meteorological Department (IMD), TSDPS, and GHMC Directorate of Enforcement, Vigilance & Disaster Management (EV&DM) / Disaster Response Force (DRF).
2. **Requisition Type**: Non-flood baseline matrix for false-alarm rate calibration.
3. **Target Parameters**: Continuous daily rainfall records matched with daily municipal emergency logs confirming zero de-watering pump deployments.
4. **Draft Request Template**: [`docs/data_requests/template_negative_control_observations.md`](data_requests/template_negative_control_observations.md).
5. **Technical Requirements Report**: [`docs/negative_control_data_requirements.md`](negative_control_data_requirements.md).

---

## 7. Milestone 8 Acquisition Audit Summary

| Source Category | Datasets Included | Status | Unsupported Measurement Gaps |
|:---|:---|:---|:---|
| **Locally Downloaded & Verified** | DES Annual Rainfall (1970–2023), GloFAS Oct 2020 Reanalysis, ERA5 Oct 2020 Weather, GHMC Survey Flood Zones, NDMA SACHET Alert, Curated Flood Event Catalogue | Active in `data/curated/` | Musi River discharge in 2000, 2016, 2021, and 2023 lacks physical gauge telemetry and remains nullified (`null`) in observation fields. |
| **Map Viewer & Report Only** | ISRO / NRSC Bhuvan October 2020 Flood Extent | Viewer / PDF Public | Full-resolution Level-3 SAR GeoTIFF rasters require nodal credentials. |
| **Restricted Institutional Access** | TSDPS AWS 15-minute Telemetry (~100+ stations), Telangana I&CAD Dam Gate Outflows | Draft Requests Prepared | Raw high-frequency telemetry requires signed data-sharing agreements. |
| **Negative Control Data** | Verified multi-year non-flood daily matrices | Under Requisition | Specificity and false-positive rates remain mathematically undefined. |
