# Open-Meteo Rainfall Integration

This document outlines the design and behavior of the `backend/app/services/rainfall.py` antecedent rainfall service. This service is responsible for querying true historical precipitation data to calculate the exact `T1d`-`T10d` features required by the INDOFLOODS machine learning model.

## 1. Selected Source & API 
- **Source:** Open-Meteo Historical Weather API
- **Base URL:** `https://archive-api.open-meteo.com/v1/archive`
- **Data Type:** Reanalysis / model-derived (primarily ECMWF ERA5)
- **API Key:** NOT REQUIRED (Open-Meteo offers free access for non-commercial/academic use)
- **Requested Value:** Daily aggregated rainfall (`rain_sum`) in millimeters (`mm`).

## 2. Calculation Convention (T1d–T10d)
To maintain scientific validity and match the INDOFLOODS model training, the features must represent contiguous cumulative days of rainfall prior to the prediction day. 

### Target Date Exclusion Convention
The `target_date` (Prediction Day `D`) is **excluded** from the cumulative calculation. Only completed days prior to the target date are used. 

For example, if `target_date = 2025-08-20`:
The service requests 10 full prior days from Open-Meteo: `2025-08-10` through `2025-08-19`.

### Cumulative Method
The cumulative variables are calculated systematically:
- **T1d**: Rainfall on D-1
- **T2d**: Rainfall on D-1 + D-2
- **T3d**: Rainfall on D-1 + D-2 + D-3
...
- **T10d**: Rainfall on D-1 + D-2 + ... + D-10

There is **NO fabrication**. The service relies entirely on an array of 10 genuine daily values. Missing data or null values returned by Open-Meteo will cause the endpoint to safely return an error rather than silently fabricating a proxy variable.

## 3. Example Request & Response

### Request Endpoint
`GET /weather/antecedent-rainfall?latitude=17.385&longitude=78.4867&target_date=2025-08-20`

### Example Response
```json
{
  "latitude": 17.385,
  "longitude": 78.4867,
  "target_date": "2025-08-20",
  "data_source": "Open-Meteo Historical API",
  "data_type": "reanalysis/model-derived",
  "rainfall_unit": "mm",
  "T1d": 10.0,
  "T2d": 19.0,
  "T3d": 27.0,
  "T4d": 34.0,
  "T5d": 40.0,
  "T6d": 45.0,
  "T7d": 49.0,
  "T8d": 52.0,
  "T9d": 54.0,
  "T10d": 55.0,
  "daily_rainfall_values": {
    "2025-08-19": 10.0,
    "2025-08-18": 9.0,
    "2025-08-17": 8.0,
    "2025-08-16": 7.0,
    "2025-08-15": 6.0,
    "2025-08-14": 5.0,
    "2025-08-13": 4.0,
    "2025-08-12": 3.0,
    "2025-08-11": 2.0,
    "2025-08-10": 1.0
  }
}
```

## 4. Limitations
- **Data Resolution Limitations:** The historical rainfall is gridded reanalysis data (often ~9-11 km). While this is highly accurate at a regional basin scale, it is not a 1:1 match for physical rain gauges positioned precisely at latitude/longitude coordinates.
- **Future Forecasting/Recent Weather:** Because the Open-Meteo archive (ERA5) has an update lag of 2-5 days, querying for a `target_date` representing "today" might result in insufficient historical data for D-1 and D-2. In a future production iteration, real-time predictions will need a blended approach, pulling D-1/D-2 from the Open-Meteo *Forecast* API (which updates live) while pulling the deeper D-3 to D-10 window from the *Historical* API.

## 5. Strict Scientific Adherence
- **NO Fabrication:** Single rainfall values are not copied, multiplied, or propagated.
- **ML Independence:** This API serves data purely to satisfy the backend. The ML model (`ml/models/flood_severity_model.joblib`) was untouched during this process.
- **Water Levels & Geography:** Environmental factors like water level, elevation, routing, and risk-maps are outside the scope of this precipitation service.
