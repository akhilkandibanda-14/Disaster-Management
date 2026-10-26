# SafeMap AI — Institutional Data Intake & Validation Guide

**Document Version**: 1.0.0  
**Status**: Standard Operating Procedure (SOP)  
**Target Domain**: Institutional Evidence Ingestion, Sensor Telemetry Normalization, and Provenance Auditing  

---

## 1. Overview & Objective

When authorized data files (such as high-density AWS rainfall telemetry from TSDPS, reservoir sluice gate releases from Telangana Irrigation & CAD, or SAR inundation extent polygons from ISRO NRSC) become available through formal institutional agreements, SafeMap AI provides a reproducible, validated ingestion pipeline.

### Guiding Principles
1. **Zero Credential Scraping**: SafeMap AI does not attempt automated web scraping of authenticated or restricted government portals.
2. **Standard Format Support**: Accepts CSV, JSON, and OGC GeoJSON files.
3. **Cryptographic Provenance**: Every imported batch records file SHA-256, provider identity, formal source document identifier, retrieval date, data owner, and usage restrictions.
4. **Unit Normalization with Value Preservation**: Original numeric values and units are permanently preserved alongside normalized metric values (`mm`, `m³/s`, `m`).
5. **No Silent Data Manipulation**: Missing observations are explicitly tagged as `null` / `MISSING`. Missing values are **never** silently filled with zeros.
6. **Strict Idempotency**: Submitting an identical file (matching SHA-256) multiple times safely skips duplicate processing without database corruption.

---

## 2. Ingestion Metadata Contract

Every incoming institutional batch must provide the following metadata header:

```json
{
  "provider": "TSDPS",
  "source_reference": "TSDPS-AWS-BULLETIN-2024-OCT",
  "retrieval_date": "2026-10-25T00:00:00Z",
  "data_owner": "Telangana State Development Planning Society, Planning Dept, GoTS",
  "usage_restrictions": "RESTRICTED_RESEARCH_ONLY",
  "measurement_classification": "OBSERVED"
}
```

### Metadata Fields

| Field Name | Type | Mandatory? | Description & Allowed Values |
|:---|:---|:---:|:---|
| `provider` | string | **YES** | Sourcing agency (e.g. `TSDPS`, `TG_IRRIGATION`, `ISRO_NRSC`, `IMD`, `GHMC`). |
| `source_reference` | string | **YES** | Official document ID, bulletin number, requisition token, or archive URL. |
| `retrieval_date` | string | **YES** | ISO 8601 date timestamp when data was received (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SSZ`). |
| `data_owner` | string | NO | Formal legal owner or rights holder. Defaults to `provider`. |
| `usage_restrictions` | string | NO | License or legal restrictions (e.g. `RESTRICTED_RESEARCH_ONLY`, `GOVERNMENT_OPEN_DATA`). |
| `measurement_classification` | string | NO | Must be one of: `OBSERVED`, `SECONDARY_REPORTED`, `ESTIMATED`, `MODELLED`, `HISTORICAL_VULNERABILITY`, `DEMO`. |

---

## 3. Data Validation Rules & Normalization Engine

### 3.1. Timestamps
- Recognized field names: `timestamp`, `date`, `datetime`, `start_date`, `time`, `observation_time`.
- Formats accepted: ISO 8601 strings (`2020-10-14T08:00:00Z`, `2020-10-14`, `2020-10-14 08:00:00`).
- Valid calendar range: Years $1900$ to $2100$.
- Action on failure: Rejects record with row number and actionable error description.

### 3.2. Geodetic Coordinates
- Recognized field names: `latitude` / `lat`, `longitude` / `lon` / `lng`, or GeoJSON Point coordinates `[lon, lat]`.
- Value bounds: Latitude $\in [-90.0, 90.0]$, Longitude $\in [-180.0, 180.0]$.
- Regional Tagging: Validates whether coordinates lie within the Hyderabad Metropolitan Bounding Box (`[17.00°N, 78.10°E]` to `[17.80°N, 78.80°E]`).

### 3.3. Station Identifiers
- Recognized field names: `station_id`, `station_code`, `station`, `gauge_id`, `site_id`, `id`.
- Permitted characters: Alphanumeric characters, underscores (`_`), hyphens (`-`), and periods (`.`). Length: 2 to 64 characters.

### 3.4. Physical Units & Normalization
SafeMap AI normalizes all measurements to standard scientific units while preserving the original raw entries:

| Parameter | Accepted Input Units | Normalization Multiplier | Normalized Target Unit |
|:---|:---|:---:|:---:|
| **Rainfall** | `mm`, `millimeter` | $\times 1.0$ | `mm` |
| | `cm`, `centimeter` | $\times 10.0$ | `mm` |
| | `inch`, `inches`, `in` | $\times 25.4$ | `mm` |
| **Discharge** | `m^3/s`, `m3/s`, `cumec` | $\times 1.0$ | `m^3/s` |
| | `cusec`, `cusecs`, `cfs` | $\times 0.0283168466$ | `m^3/s` |
| **Water Stage** | `m`, `meter`, `meters` | $\times 1.0$ | `m` |
| | `ft`, `foot`, `feet` | $\times 0.3048$ | `m` |

### 3.5. Missing Values & Sentinel Values
- Recognized missing value sentinels: `null`, `""`, `"-999"`, `"-999.0"`, `"-9999"`, `"NA"`, `"N/A"`, `"NULL"`, `"NaN"`.
- Rule: Explicitly stored as `null` / `None`. **Never filled with 0.0.**

---

## 4. API & CLI Ingestion Workflow

### API Endpoints
SafeMap AI exposes four REST API endpoints under `/data-curation/intake`:

1. `POST /data-curation/intake/validate`  
   **Dry-run validation**. Inspects incoming CSV/JSON text against all validation contracts without saving to disk. Returns row-by-row error diagnostics and sample normalized records.

2. `POST /data-curation/intake/commit`  
   **Validated ingestion**. Validates and saves the raw file copy to `data/raw/institutional/` and normalized records to `data/curated/institutional/`. Logs the batch in `intake_ledger.json`.

3. `GET /data-curation/intake/sources`  
   Returns the complete classified inventory of available sources, viewer-only datasets, restricted institutional sources, draft request templates, and unsupported measurement gaps.

4. `GET /data-curation/intake/log`  
   Returns the complete chronological ledger of all ingested institutional data batches.

---

## 5. Storage Directory Structure

```text
data/
├── raw/
│   └── institutional/                          <-- Raw, immutable authorized source files
│       └── INTAKE_TSDPS_20261025_001.csv
├── curated/
│   └── institutional/                          <-- Normalized JSON datasets & audit ledger
│       ├── intake_ledger.json                  <-- Chronological cryptographic intake ledger
│       └── INTAKE_TSDPS_20261025_001_curated.json
```
