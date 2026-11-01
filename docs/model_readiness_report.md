# SafeMap AI — Flood Model Readiness and Hyderabad Data Provenance Report

**Assessment Date**: 2026-10-23  
**Status**: `INSUFFICIENT_LOCAL_DATA` — Operational Predictions Suppressed for Hyderabad  
**Model Coverage Policy**: 50.0 km radius guard strictly enforced  

---

## 1. Executive Summary

SafeMap AI evaluates flood risk using authoritative feeds, municipal surveys, and machine learning models. This report assesses whether the production machine learning model (trained on the Central Water Commission INDOFLOODS dataset) can responsibly predict flood risk in Hyderabad, Telangana.

**Key Conclusion**:  
SafeMap AI **does NOT currently possess sufficient local observational training data** to make validated, automated flood predictions for Hyderabad.
- Nearest INDOFLOODS gauge is **INDOFLOODS-gauge-916** at **71.77 km**, which exceeds the 50.0 km model-coverage guard.
- Hydrological mismatch: The nearest gauge monitors the River Manjra in the **Godavari Basin**, whereas Hyderabad lies in the **Musi River Catchment (Krishna Basin)**.
- In accordance with the model-safety protocol, prediction for Hyderabad returns `MODEL_UNSUPPORTED` with `INSUFFICIENT_LOCAL_DATA`.

---

## 2. Dataset Provenance and Class Balance

| Metric | Value | Provenance & Handling |
| :--- | :--- | :--- |
| **Dataset Source** | INDOFLOODS Archive | Central Water Commission (CWC) historical river gauges across India |
| **Total Samples** | 4548 | Gauge flood event records |
| **Raw Features** | 118 | Hydro-meteorological, topographic, and catchment characteristics |
| **Class 0 (Non-Severe)** | 2919 (64.2%) | Normal to moderate warning events |
| **Class 1 (Severe Flood)** | 1629 (35.8%) | Events reaching or exceeding danger levels |
| **Missing Feature Handling** | Median / Mode Imputation | High-order stream features with missing values handled safely via SimpleImputer |

---

## 3. Data Leakage and Evaluation Methodology

### Why Naive Random Splitting Is Flawed
When records from the same river gauge appear in both training and test sets, the model memorizes gauge-specific static properties (elevation, soil, catchment area) rather than learning general flood dynamics.

| Evaluation Strategy | Test F1 Score | Notes |
| :--- | :--- | :--- |
| **Naive Random Split** (Leakage) | **0.6213** | Events from same gauge leaked across train/test |
| **Gauge-Grouped Split** (`GroupShuffleSplit`) | **0.4850** | Zero gauge overlap (0 gauges shared) |
| **Leakage Gap** | **+0.1363 F1** | Artificial inflation due to data leakage |

---

## 4. Model Readiness and Baseline Comparisons

Evaluated under strict **Gauge-Grouped Split** (Unseen Catchments):

| Model Architecture | Accuracy | Severe Precision | Severe Recall | Severe F1 | ROC-AUC | Brier Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Dummy (Majority Class)** | 0.6485 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | — |
| **Logistic Regression** | 0.5025 | 0.3544 | 0.5054 | 0.4167 | — | — |
| **Random Forest (Production)** | **0.6739** | **0.5450** | **0.4368** | **0.4850** | **0.6682** | **0.2113** |

### Cross-Validation Stability
- **5-Fold GroupKFold F1 Mean**: `0.3739 ± 0.0884`
- **5-Fold GroupKFold ROC-AUC**: `0.6364`
- **Overfitting Gap**: Training F1 is `0.9982` vs Unseen Test F1 `0.4850`. The model overfits to training catchments and generalizes with moderate fidelity to new rivers.

---

## 5. Hyderabad Geographic Applicability Audit

| Audit Parameter | Observation | Validation Impact |
| :--- | :--- | :--- |
| **Queried Location** | Hyderabad Central (17.385, 78.4867) | Urban metropolitan center |
| **Nearest INDOFLOODS Gauge** | `INDOFLOODS-gauge-916` (Godavari/Manjira) | Located at Singur Dam, Telangana |
| **Distance to Nearest Gauge** | **71.77 km** | Exceeds 50.0 km coverage threshold |
| **Gauges within 50.0 km** | **0** | Zero local telemetry available in INDOFLOODS |
| **Catchment Basin** | Godavari Basin vs **Krishna/Musi Basin** | **Hydrological Disconnection**: River flows in opposite direction |
| **Local Model Status** | `INSUFFICIENT_LOCAL_DATA` | **Automated predictions suppressed** |

---

## 6. Audit of Real Local Data Sources for Hyderabad

1. **Telangana State Development Planning Society (TSDPS)**:
   - *Network*: Automatic Weather Stations (AWS) with ~100+ telemetry rain gauges across GHMC.
   - *Access Barrier*: Public dashboard displays summary graphics; long-term machine-readable time-series archives require institutional credentials and departmental permission.
2. **Central Water Commission (CWC) / WRIS**:
   - *Network*: National telemetry portal. Musi River urban stage gauges are monitored by state irrigation departments, not published as open machine-readable streaming endpoints.
3. **Musi River Discharge (Copernicus GloFAS via Open-Meteo)**:
   - *Status*: Operational integration completed.
   - *Semantics*: Modelled river discharge forecast (`MODEL_FORECAST`), not observed physical telemetry. Severity is kept as `UNKNOWN` until calibrated with Musi River rating curves.
4. **Municipal Flood-Prone Zones (GHMC / MRDCL GeoJSON)**:
   - *Status*: Operational spatial layer with ray-casting Point-in-Polygon (PIP).
   - *Semantics*: Retained as `PUBLIC_UNVERIFIED` and `HISTORICAL_VULNERABILITY`. Never labeled official real-time sensor measurements.

---

## 7. Safety Invariants & Operational Directives

1. **50 km Coverage Guard**: Strict geographic invariant. Predictions are withheld if distance > 50.0 km.
2. **Absence of Alerts != Safety**: SafeMap AI never treats missing sensors or feeds as evidence of safety.
3. **Explicit Source Categorization**:
   - `OFFICIAL_ALERT`: Authoritative CAP bulletins (NDMA SACHET).
   - `MODEL_FORECAST`: Uncalibrated hydrological forecasts (GloFAS).
   - `HISTORICAL_VULNERABILITY`: Published survey flood zones (GHMC).
   - `DEMO`: Simulated scenarios for UI evaluation.
