# DRAFT INSTITUTIONAL DATA REQUEST — NOT YET SUBMITTED
## Document Status: DRAFT / PENDING REVIEW
> **Notice**: This document is an editable institutional request template prepared for academic research and flood decision-support validation. It has **NOT** been submitted to the recipient organization, and no data access or institutional agreement has been granted.

---

**Date**: [Insert Submission Date, e.g., 2026-10-25]  
**To**:  
1. The Director, Meteorological Centre Hyderabad, India Meteorological Department (IMD), Begumpet, Hyderabad.  
2. The Member Secretary, Telangana State Development Planning Society (TSDPS), Planning Department, GoTS.  
3. The Director / Commissioner, Disaster Management & Enforcement Vigilance and Disaster Management (EV&DM) / Disaster Response Force (DRF), Greater Hyderabad Municipal Corporation (GHMC), Hyderabad.  

**From**:  
SafeMap AI Research Group / Academic Decision-Support Core  
[Insert Institution / University / Organization Name]  
[Insert Contact Address and Email]  

**Subject**: Requisition for Multi-Year Continuous Meteorological Observations and Municipal Incident Logs to Compile a Negative-Control (Non-Flood) Evaluation Baseline for Urban Hydrological Models.

---

### 1. Scientific Justification: The Critical Need for Negative Controls

A fundamental limitation of conventional disaster databases is **positive-event selection bias**: municipal archives, newspaper chronicles, and state disaster bulletins exclusively record dates when catastrophic flooding, severe property damage, or fatalities occurred. 

In SafeMap AI's statistical audit (Milestone 7), we demonstrated that evaluating a model on an all-positive sample ($N=8$ flood events across 115 years) yields an **undefined specificity** and an **uncomputable false-positive rate**:
$$\text{Specificity} = \frac{TN}{TN + FP} = \text{Undefined (since } TN=0 \text{ and } FP=0 \text{ in disaster catalogues)}$$

Without a continuous observation matrix that includes both flood and **verified non-flood days**, it is mathematically impossible to measure whether a predictive model generates unacceptably high false alarms during ordinary rainy days. 

Importantly, under SafeMap AI's scientific standards, **a day with no reported flood cannot simply be assumed to be a "non-flood" day**. A moderate cloudburst could have caused unrecorded street inundation, or emergency response could have de-watered an underpass without a formal disaster declaration. Therefore, **explicit ground-truth negative-control evidence** is mandatory.

### 2. Specific Data Requisition Parameters

| Data Domain | Provider Organization | Requested Parameters | Target Temporal Horizon |
|:---|:---|:---|:---|
| **Continuous Daily Rainfall Matrix** | IMD & TSDPS | Daily 24-hour rainfall ($mm$) across all operational weather stations within GHMC for every single calendar day, including dry days ($0.0\text{ mm}$), light rain ($0.1–15.0\text{ mm}$), moderate rain ($15.1–64.4\text{ mm}$), and heavy rain ($64.5–115.5\text{ mm}$). | **Five Full Calendar Years: 1 January 2019 to 31 December 2023** (Continuous 1,826 days). |
| **Municipal Emergency Deployment Logs** | GHMC EV&DM / DRF | Daily log of monsoon emergency calls and deployments across the 30 GHMC circles:• Number of water-logging complaint tickets logged.• Number of DRF de-watering pump deployments.• Causeway closure notices or traffic diversions.• Inundation severity rating ($0 = \text{Normal Operations / Zero Inundation}$, $1 = \text{Minor Street Puddling}$, $2 = \text{Localized Underpass Stagnation}$, $3 = \text{Severe Colony Inundation}$). | Same 5-Year Window (2019–2023). |
| **Reservoir Status Matrix** | Telangana I&CAD / HMWSSB | Daily reservoir water level and gate status for Osman Sagar and Himayat Sagar (confirming dates when zero gates were opened and river flows remained at baseflow). | Same 5-Year Window (2019–2023). |

### 3. Classification Framework to be Populated

The requested data will populate SafeMap AI's formal Negative-Control Schema:
1. `CONFIRMED_FLOOD`: Heavy rainfall accompanied by official DRF deployment logs, municipal colony inundation, or satellite SAR inundation masks.
2. `DOCUMENTED_NON_FLOOD`: Daily rainfall verified across stations, paired with DRF records confirming **zero** waterlogging calls and normal traffic operations.
3. `UNKNOWN_OR_UNCLASSIFIED`: Days with substantial rainfall ($> 50\text{ mm}$) where municipal incident logs are missing or inconclusive.
4. `MISSING_OBSERVATION`: Dates with sensor dropouts or telemetry transmission failure.

### 4. Preferred Delivery Formats

- Standard relational database export (CSV or SQLite database) joining station date-stamps with DRF incident ticket summaries.

### 5. Ethical Compliance, Data Governance, & Non-Commercial Undertaking

1. **Non-Commercial Research Integrity**: Data will be used exclusively to benchmark algorithm false-alarm rates in peer-reviewed scientific studies.
2. **Citizen Privacy Protection**: Any individual citizen phone numbers, street addresses, or personal caller details appearing in DRF dispatch logs will be anonymized or scrubbed prior to analysis.
3. **Formal Institutional Attribution**: All resulting scientific publications and technical reports will prominently attribute all contributing state organizations: *"Continuous meteorological baseline and municipal operations logs provided by the India Meteorological Department (IMD), Telangana State Development Planning Society (TSDPS), and GHMC Directorate of Enforcement, Vigilance & Disaster Management."*

---

**Authorized Signatory**:  
[Name & Designation]  
[Department / Institution]  
[Phone Number & Email Address]  
