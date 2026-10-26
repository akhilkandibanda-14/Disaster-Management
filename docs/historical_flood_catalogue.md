# SafeMap AI — Hyderabad Historical Flood Event Catalogue (1908–2023)

**Dataset ID**: `HYD-HISTORICAL-FLOOD-CATALOGUE`  
**Temporal Span**: 1908-09-28 to 2023-07-24 (115 years)  
**Sample Count**: 8 distinct catalogued urban flood events  
**Audit Standard**: Milestone 7 Historical Flood Evidence Audit & Provenance Assurance  
**Verification State**: 0 Fully Verified · 8 Partially Verified · 0 Unverified  
**Curated Files**: 
- JSON: [`data/curated/hyderabad_flood_event_catalogue.json`](../data/curated/hyderabad_flood_event_catalogue.json)
- CSV: [`data/curated/hyderabad_flood_event_catalogue.csv`](../data/curated/hyderabad_flood_event_catalogue.csv)
- Audit Report: [`docs/historical_flood_evidence_audit.md`](historical_flood_evidence_audit.md)

---

## 1. Overview & Classification Policy

The SafeMap AI Historical Flood Event Catalogue documents verified flood, deluge, and causeway inundation events across Hyderabad, Telangana. 

### Semantic Classification Standards
In accordance with SafeMap AI's evidence audit guidelines, each event is strictly classified by its evidentiary provenance:
- `OBSERVATION`: Physical ground-truth rain gauge or automated weather station (AWS) measurement published in official meteorological archives.
- `HISTORICAL_INUNDATION`: Post-event satellite remote-sensing water masks (e.g., ISRO/NRSC Bhuvan Cartosat/Sentinel-1 SAR).
- `OFFICIAL_ALERT`: Authoritative emergency bulletins issued by national or state disaster management authorities (NDMA SACHET / TG-SDMA).
- `HISTORICAL_RECORD`: Multi-decadal archival reports from engineering commissions or gazettes (e.g. Visvesvaraya Technical Committee Report 1909).
- `MODELLED`: Gridded atmospheric or hydrological reanalysis (e.g., Copernicus GloFAS or ERA5).

### Measurement Classifications
Under Milestone 7 quality assurance, every numeric measurement is classified by its physical nature:
- `OBSERVED`: Direct telemetry from a physical instrument (e.g. TSDPS AWS or IMD rain gauge).
- `SECONDARY_REPORTED`: Published in retrospective administrative summaries or secondary literature.
- `ESTIMATED`: Computed via post-hoc hydraulic equations (slope-area method) or converted from reservoir gate opening heights.
- `UNVERIFIED`: Numerical claim without verifiable physical stream-gauge records (set to `null` in observation fields).

### Non-Derivation Invariants
1. **River Discharge Non-Inference**: River discharge is never inferred from rainfall without an official calibrated stream gauge or dam release schedule.
2. **Reanalysis Invariant**: GloFAS reanalysis forecasts are never substituted for physical river observations.
3. **District Rainfall Invariant**: District-level rainfall totals are never attributed to individual stations.
4. **Vulnerability Polygon Invariant**: A static vulnerability polygon is never treated as proof that a flood occurred on a given date.
5. **Audit Trail Invariant**: When an unsupported measurement is corrected or nullified, the original number is preserved in `audit_trail` with documented rationale.

---

## 2. Audited Event Catalogue Summary Table

| Event ID | Event Name & Date | Max 24h Rain (mm) | Rainfall Station & Type | Peak River Discharge ($m^3/s$) | Discharge Type | Confidence | Verification State |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| `HYD-EVT-1908-01` | **Great Musi Flood of 1908**<br/>1908-09-28 | 431.8 | Shamshabad Catchment<br/>`SECONDARY_REPORTED` | 12,034.0 | `ESTIMATED`<br>(Slope-Area) | **MEDIUM** | `PARTIALLY_VERIFIED` |
| `HYD-EVT-2000-01` | **August 2000 Urban Deluge**<br/>2000-08-23 | 241.5 | IMD Begumpet Observatory<br/>`SECONDARY_REPORTED` | *Null*<br>(Prior: 1250 cumec) | `UNVERIFIED`<br>(No Gauge) | **MEDIUM** | `PARTIALLY_VERIFIED` |
| `HYD-EVT-2008-01` | **August 2008 Musi River Swell**<br/>2008-08-10 | 115.0 | Rajendranagar AWS / IMD<br/>`SECONDARY_REPORTED` | 480.0 | `ESTIMATED`<br>(Dam Outflow) | **LOW** | `PARTIALLY_VERIFIED` |
| `HYD-EVT-2016-01` | **Sep 2016 Alwal-Bhandari Inundation**<br/>2016-09-21 | 165.4 | Hakimpet AFS / TSDPS AWS<br/>`OBSERVED` | *Null*<br>(Prior: 210 cumec) | `UNVERIFIED`<br>(No Gauge) | **MEDIUM** | `PARTIALLY_VERIFIED` |
| `HYD-EVT-2020-01` | **October 2020 Flash Flood Catastrophe**<br/>2020-10-13 | 320.0 | Ghatkesar AWS / Begumpet<br/>`OBSERVED` | 850.0 | `ESTIMATED`<br>(Dam Outflow) | **HIGH** | `PARTIALLY_VERIFIED` |
| `HYD-EVT-2021-01` | **July 2021 Central Flash Inundation**<br/>2021-07-14 | 115.8 | TSDPS AWS Nampally<br/>`OBSERVED` | *Null*<br>(Prior: 95 cumec) | `UNVERIFIED`<br>(No Gauge) | **MEDIUM** | `PARTIALLY_VERIFIED` |
| `HYD-EVT-2022-01` | **July 2022 Musi Catchment Surge**<br/>2022-07-22 | 98.4 | TSDPS AWS Rajendranagar<br/>`SECONDARY_REPORTED` | 226.5 | `ESTIMATED`<br>(Dam Outflow) | **MEDIUM** | `PARTIALLY_VERIFIED` |
| `HYD-EVT-2023-01` | **July 2023 Arterial Corridor Stagnation**<br/>2023-07-19 | 128.5 | TSDPS AWS Shaikpet<br/>`OBSERVED` | *Null*<br>(Prior: 85 cumec) | `UNVERIFIED`<br>(No Gauge) | **MEDIUM** | `PARTIALLY_VERIFIED` |

---

## 3. Provenance and Audit Trail Schema

Each catalogue record in [`data/curated/hyderabad_flood_event_catalogue.json`](../data/curated/hyderabad_flood_event_catalogue.json) implements the following metadata extensions:

```json
{
  "event_id": "HYD-EVT-2020-01",
  "rainfall_measurement_type": "OBSERVED",
  "discharge_measurement_type": "ESTIMATED",
  "verification_state": "PARTIALLY_VERIFIED",
  "provenance": {
    "source_title": "ISRO / NRSC Bhuvan Satellite Flood Assessment & TSDPS Special Weather Bulletin (October 2020)",
    "publisher": "National Remote Sensing Centre (ISRO), TSDPS, and IMD",
    "publication_year": 2020,
    "direct_url": "https://bhuvan-app1.nrsc.gov.in/disaster/disaster.php",
    "citation_detail": "Bhuvan Sentinel-1 SAR flood extent map; TSDPS AWS Ghatkesar 320 mm 24h record; Osman Sagar (14 gates) & Himayat Sagar (8 gates) release logs.",
    "evidence_note": "Precipitation and satellite inundation are verified from official TSDPS, IMD, and NRSC records. Peak river discharge of ~850 m³/s represents combined dam gate outflow calculation, NOT a river stream-gauge observation.",
    "measurement_classifications": {
      "rainfall": "OBSERVED",
      "satellite_inundation": "OBSERVED",
      "discharge": "ESTIMATED",
      "glofas_discharge": "MODELLED"
    },
    "verification_status": "PARTIALLY_VERIFIED",
    "unresolved_issues": "Satellite acquisition was captured on 18 Oct (4 days post-peak); river discharge is calculated dam outflow rather than physical stream telemetry."
  },
  "audit_trail": {
    "original_classification": "HISTORICAL_INUNDATION",
    "original_confidence": "VERY_HIGH",
    "corrected_classification": "HISTORICAL_INUNDATION",
    "corrected_confidence": "HIGH",
    "original_reported_discharge_cumec": null,
    "correction_rationale": "Downgraded confidence from VERY_HIGH to HIGH because river discharge is an outflow estimation rather than physical gauge telemetry and satellite scene was captured post-peak."
  }
}
```

---

## 4. Key Evidentiary Findings

1. **Absence of Calibrated In-Stream Gauges**: Hyderabad has no open, continuous hydrometric gauge recording flow on the Musi River mainstem within GHMC limits. Discharges during major events are regulated by twin upstream reservoirs (Osman Sagar and Himayat Sagar) and calculated from sluice gate discharge curves.
2. **Correction of Unsupported Discharges**:
   - For **2000** (1,250 cumec), **2016** (210 cumec), **2021** (95 cumec), and **2023** (85 cumec), flooding was localized to urban lake breaches (Alwal, Fox Sagar), overflowing stormwater drains (nalas), or road underpasses. No in-stream river overflow occurred. These values have been nullified in the observation fields and preserved in the audit trails.
3. **Defensible Confidence Ratings**:
   - `VERY_HIGH` ratings were eliminated across all entries because continuous stream telemetry is absent.
   - `HIGH` was retained exclusively for **2020** where dual AWS ground stations and Bhuvan Sentinel-1 SAR water masks corroborate the event.
   - **2008** was downgraded to `LOW` because records rely on pre-bifurcation physical departmental ledgers.
   - All other events are rated `MEDIUM`.
