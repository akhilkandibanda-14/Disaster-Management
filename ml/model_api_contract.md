# INDOFLOODS ML Model API Contract

## 1. Overview
The INDOFLOODS severity model (`ml/models/flood_severity_model.joblib`) predicts flood severity (0 = Flood, 1 = Severe Flood) using antecedent precipitation variables and comprehensive catchment characteristics.

This document outlines the strict API contract that must be adhered to when integrating this model into the FastAPI backend or frontend. The central principle of this contract is: **No scientific fabrication**. If real data is not available, the system must fail explicitly rather than producing a misleading probability.

## 2. Model Input Requirements
The trained `RandomForest` model expects a dataframe containing precisely 118 raw features (114 numerical, 4 categorical), which the preprocessing pipeline transforms into 130 features (5 numerical features are dropped due to all-NaNs in training, and the 4 categorical features are one-hot encoded into 21 columns).

### Core Required Features (Not Exhaustive):
- **Antecedent Precipitation:** `T1d`, `T2d`, `T3d`, `T4d`, `T5d`, `T6d`, `T7d`, `T8d`, `T9d`, `T10d` (Daily precipitation for the 10 days leading up to the event).
- **Temporal:** `start_month`
- **Environmental/Catchment:** `Annual Mean Temperature`, `Mean Diurnal Range`, `Annual Precipitation`, `Mean Basin Elevation`, `Drainage Area`, etc.
- **Categorical:** `KoppenGeiger Climate Type`, `Land cover`, `Soil type`, `lithology type`.

### Prohibited Features (Leakage/Identifiers):
The following features were strictly removed during training because they either represent geographic identifiers (which leads to overfitting) or post-event leakage metrics (which are impossible to know before the flood):
- `GaugeID`, `EventID`
- `Peak Flood Level (m)`, `Peak FL Date`, `Num Peak FL`
- `Peak Discharge Q (cumec)`, `Flood Volume (cumec)`
- `Event Duration (days)`, `Time to Peak (days)`, `Recession Time (day)`
- `Flood Type`, `Q Date`

## 3. Strict Fabrication Prohibition
The FastAPI integration must **never** map a single, generic `rainfall` input to all proxy `T1d`-`T10d` features. 
- **Why?** The machine learning model learned the relationship of consecutive rain events leading to a saturation point. Injecting a constant `rainfall` value into all 10 days simulates an impossible 10-day torrential downpour that the model has never seen, leading to completely nonsensical predictions.
- **Why catchment features matter?** Catchment attributes (like `Drainage Area`, `Mean Basin Elevation`) dictates how rainfall converts to runoff. Supplying `NaN` or arbitrary values makes the prediction completely blind to the local topography.

## 4. Current API Behavior
To preserve the legacy React frontend without returning misleading data:
1. **Legacy Route (`/predict`):** When the existing frontend sends a `PredictionRequest` (with generic `rainfall`, `temperature`, etc.), the API **intercepts** the request. It returns a `PredictionResponse` with `prediction=None`, `risk_level="UNKNOWN"`, and an explicit message: `"Additional real environmental inputs (T1d-T10d, catchment data) are required for valid scientific prediction."`
2. **Internal Route (`/predict/internal`):** A new internal endpoint accepts `IndofloodsModelInput` which maps strictly to the required precipitation and catchment variables. It returns `predicted_severity`, `flood_probability`, and `severe_flood_probability`.

## 5. Limitations
This model was trained exclusively on INDOFLOODS dataset events. It does not represent Hyderabad/Telangana-specific flood behavior. Until real local catchment parameters and antecedent daily rainfall datasets are connected to this API, the model serves as an architectural placeholder.
