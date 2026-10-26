# DRAFT INSTITUTIONAL DATA REQUEST — NOT YET SUBMITTED
## Document Status: DRAFT / PENDING REVIEW
> **Notice**: This document is an editable institutional request template prepared for academic research and flood decision-support validation. It has **NOT** been submitted to the recipient organization, and no data access or institutional agreement has been granted.

---

**Date**: [Insert Submission Date, e.g., 2026-10-25]  
**To**:  
The Member Secretary / Director,  
Telangana State Development Planning Society (TSDPS),  
Planning Department, Government of Telangana,  
Aranya Bhavan / BRKR Bhavan, Hyderabad, Telangana, India.  

**From**:  
SafeMap AI Research Group / Academic Decision-Support Core  
[Insert Institution / University / Organization Name]  
[Insert Contact Address and Email]  

**Subject**: Requisition for Historical High-Resolution Automatic Weather Station (AWS) Meteorological Telemetry across Greater Hyderabad Municipal Corporation (GHMC) for Non-Commercial Flood Risk and Model Readiness Research.

---

### 1. Research Purpose & Background

SafeMap AI is an academic and non-commercial open research initiative evaluating urban flood risk, geospatial evacuation routing, and meteorological data readiness in Hyderabad, Telangana. 

Currently, open government statistical abstracts provide district-level rainfall totals averaged over 217 km². However, urban flash flooding in Hyderabad is frequently triggered by localized mesoscale convective cloudbursts where intense precipitation (e.g., 100 mm in 2 hours) is concentrated within individual mandals while other parts of the city remain dry. 

To scientifically evaluate urban flood thresholds, establish true statistical power, and assess false-positive alarm rates without data fabrication, localized station-level telemetry is indispensable.

### 2. Specific Data Requisition Parameters

| Dimension | Requested Specification | Minimum Acceptable Specification |
|:---|:---|:---|
| **Geographic Scope** | All operational AWS stations within GHMC boundaries and immediate peri-urban mandals in Ranga Reddy and Medchal-Malkajgiri districts (~100+ stations). | Core urban mandals: Begumpet, Khairatabad, Shaikpet, Nampally, Ghatkesar, Serilingampally, Rajendranagar, Alwal, Kukatpally, Amberpet, Charminar. |
| **Target Period** | 10-Year Continuous Record: **1 January 2014 to 31 December 2024** | 5-Year Record: **1 January 2019 to 31 December 2024** |
| **Temporal Resolution** | **15-minute** cumulative precipitation; or **hourly** cumulative precipitation. | Daily 24-hour summary totals with sub-daily peak intensity indicators. |
| **Key Parameters** | 1. Tipping-bucket rainfall accumulation ($mm$)<br>2. Hourly ambient temperature ($^\circ C$)<br>3. Relative humidity ($\%$)<br>4. Wind speed and direction ($km/h$) | Tipping-bucket cumulative rainfall ($mm$) with station timestamp. |

### 3. Required Metadata & Quality Indicators

To guarantee scientific reproducibility and valid integration into SafeMap AI's evidence audit framework, the requested dataset must include the following metadata fields:
1. **Station Identifiers**: Unique station code (`station_id`) and official name (`station_name`).
2. **Geodetic Coordinates**: Station latitude and longitude in WGS84 decimal degrees (minimum 4 decimal places).
3. **Station Elevation**: Elevation above mean sea level in meters ($m$).
4. **Instrument & Calibration Details**: Sensor model (e.g., tipping bucket diameter/resolution: 0.1 mm or 0.5 mm) and most recent calibration date.
5. **Quality Control (QC) Flags**: Explicit data quality flags for each record:
   - `0` / `V`: Validated observation.
   - `1` / `S`: Suspect observation (exceeds physical limits or sensor stuck).
   - `2` / `I`: Interpolated / imputed value.
   - `9` / `M`: Missing observation (sensor offline or telemetry transmission dropout).
6. **Missing-Value Convention**: Explicit representation of missing records (e.g. `null` or `-999.0`), avoiding zero-filling for missing sensors.

### 4. Preferred Data Delivery Format

- **Primary Preference**: Compressed Delimited Files (CSV or Parquet) partitioned by year/month.
- **Alternative Preference**: Programmatic API access (read-only token) or structured JSON time-series extracts.

### 5. Proposed Data Handling, Security, & Ethical Compliance

The research team formally commits to the following data governance protocols:
1. **Non-Commercial Academic Use**: Data will be utilized exclusively for academic research, disaster risk reduction modeling, and peer-reviewed scientific publications.
2. **Zero Commercial Redistribution**: Raw tabular time-series data will not be sold, licensed, or shared with third parties.
3. **Secure Research Storage**: Data will be archived in access-controlled, encrypted storage compliant with institutional information security policies.
4. **Public Reporting Attribution**: Any published research, dashboard aggregation, or technical reports will explicitly credit: *"Hydrometeorological telemetry provided by the Telangana State Development Planning Society (TSDPS), Planning Department, Government of Telangana."*
5. **Transparency & Error Reporting**: Any sensor anomalies, calibration drift, or telemetry gaps identified during scientific quality assurance will be shared back with TSDPS technical staff for mutual benefit.

---

**Authorized Signatory**:  
[Name & Designation]  
[Department / Institution]  
[Phone Number & Email Address]  
