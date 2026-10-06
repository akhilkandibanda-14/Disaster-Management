# Hydrology Integration Architecture

## Overview
The SafeMap AI platform includes a Hydrological Service intended to provide water-level and discharge telemetry data as an independent decision-support layer.

**CRITICAL NOTE:** Hydrological data is currently demonstrated using explicitly labelled demo data. It is not a real-time observed water-level feed.

## Why Demo Data is Being Used
During the source evaluation and architecture phase, it was determined that no suitable, free, unauthenticated real-time JSON API for observed Indian water levels is available for public integration. 
Specifically:
- **India-WRIS / NWIC:** Provides highly accurate observed telemetry, but requires web registration, authentication, and an API key. We are strictly forbidden from introducing new API keys or credentials.
- **Central Water Commission (CWC ffs):** While official, it lacks a public JSON API for developers, meaning programmatic access would rely on unstable web scraping.
- **Open-Meteo Flood API (GloFAS):** Provides data without authentication, but the data is simulated *river discharge* (m³/s) at 5km resolution, rather than actual observed *water levels* (meters).

Due to these constraints, we rely on a deterministic demo dataset to demonstrate the architecture of the hydrology endpoints without fabricating live telemetry data.

## Demo Data Limitations
- **Data Status:** The data returned by `/hydrology/water-level` explicitly specifies `"data_status": "DEMO"` and `"data_source": "SafeMap AI Demo Hydrological Dataset"`.
- **Not Real-time:** The values are fixed and serve only as reference markers for testing.
- **Frontend Safety:** This data must **NEVER** be labelled in any frontend interface as "LIVE", "REAL-TIME", or "OBSERVED".

## Independence from Machine Learning
- **Not an ML Feature:** `water_level` is **NOT** one of the 118 raw features utilized by the trained INDOFLOODS machine learning model.
- **Not used for probabilities:** Water level data retrieved from the Hydrological Service is purely an independent informational overlay. It is **NOT** connected to `/predict/integrated` and is **NOT** used to calculate flood probability or severity.

## Future Replacement Path
The service architecture uses a `HydrologyProvider` abstraction. Currently, `DemoHydrologyProvider` is injected as the dependency for the API endpoints. In the future, when an official verified hydrological provider with a stable API (and appropriate credentials) is available, a new class (e.g., `OfficialHydrologyProvider`) can be created implementing the `HydrologyProvider` interface, allowing a seamless replacement without modifying the API contract.
