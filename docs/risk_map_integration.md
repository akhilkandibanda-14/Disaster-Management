# Risk Map Integration

This document outlines the architecture and implementation details for the Geographic Risk Map Backend in SafeMap AI, which is built on top of the original INDOFLOODS machine learning model.

## Overview

The legacy 3x3 fixed grid for risk visualization has been replaced by a dynamic, geographically-aware service that integrates directly with the INDOFLOODS flood severity model. The new API endpoints evaluate any geographic coordinate provided by a client and strictly enforce the model's geographic coverage limitations.

## Key Constraints Enforced

1.  **ML Model Integrity:** The underlying `flood_severity_model.joblib` was preserved without any retraining or modification.
2.  **Feature Contract:** The ML model requires exactly 118 raw features (static catchment properties and antecedent rainfall `T1d` to `T10d`). No new inputs (e.g., live water levels) were injected into the model prediction path.
3.  **Geographic Coverage (50 km Threshold):** The model relies on static characteristics associated with official INDOFLOODS gauges. A prediction is only generated if a queried location is within 50 km of an official INDOFLOODS gauge.
4.  **No APIs for Geocoding:** The backend exclusively operates on latitude and longitude provided by the frontend. No external geocoding, mapping (Google Maps/Mapbox), or paid APIs were added.
5.  **Hydrology Independence:** Hydrology data (water levels) is intentionally isolated from the risk prediction model to preserve the integrity of the ML logic. The model's "predicted class" strictly relies on rainfall patterns and catchment properties.

## Architecture

### 1. Endpoint: `GET /risk-map`
Accepts `latitude` and `longitude`.
- Uses `GaugeReferenceService` to calculate the Haversine distance to all known INDOFLOODS gauge coordinates.
- If the nearest gauge is **> 50 km** away, the response explicitly returns `prediction_available: false` and `coverage_status: "MODEL_UNSUPPORTED"`. (e.g., Hyderabad at ~71.77 km distance).
- If the nearest gauge is **<= 50 km** away, the service uses `IntegrationService` to query Open-Meteo for recent rainfall (T1d–T10d), assembles the 118 required features, executes the model prediction, and returns the risk level (LOW, MEDIUM, HIGH) with `coverage_status: "MODEL_SUPPORTED"`.

### 2. Endpoint: `GET /risk-map/gauges`
Returns a list of all official INDOFLOODS gauges with their `latitude` and `longitude`. This can be used by frontend applications to visually indicate model coverage zones to users before they click.

## Testing & Validation

The risk map integration includes comprehensive unit tests verifying:
- **Supported Geographies:** Locations near gauges return valid model predictions.
- **Unsupported Geographies:** Distant locations (e.g. Hyderabad) gracefully refuse prediction and return `MODEL_UNSUPPORTED`.
- **Determinism:** Repeated queries for the same coordinates yield identical results.
- **Hydrology Independence:** The prediction pipeline explicitly does not invoke the standalone hydrology service.
- **ML Contract:** The model receives exactly the expected 118 raw features.

## Future Recommendations

- To expand the geographic coverage of the model (e.g., to fully cover Hyderabad), the INDOFLOODS model would need to be retrained or expanded to include catchments and gauge data encompassing that area.
- If authoritative, programmatic API endpoints for real-time water levels become available (e.g. via CWC with automated credentials), the current isolated `HydrologyProvider` interface can be upgraded from demo data to live data without impacting the risk map model.
