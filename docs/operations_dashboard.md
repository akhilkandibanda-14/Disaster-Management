# Operations Dashboard Architecture & Documentation

## Purpose
The Operations Dashboard is an operational visualization tool designed for emergency-management users. It provides a consolidated view of the data available to SafeMap AI. Its primary goal is information visibility and operational awareness, without fabricating or implying unavailable data. 

## Architecture
The Operations Dashboard is built as a separate React component (`OperationsDashboard.jsx`) within the existing Vite + React frontend. 
It shares the same state management layer as the Citizen Dashboard but presents the data specifically for operational review.

### Components
- `OperationsDashboard.jsx`: The main view containing operational metrics, cards, and data source limitations.
- `OperationsMap` (internal to `OperationsDashboard.jsx`): A customized Leaflet map rendering all raw data points for spatial awareness.

### APIs Consumed
The dashboard consumes the following backend endpoints through the main `loadDashboard` function in `App.jsx`:
- `GET /health` - System health, API status, and demo mode flags.
- `GET /weather` - Rainfall data and weather condition from Open-Meteo.
- `GET /risk-map` - Core INDOFLOODS machine learning model response, risk level, severity probability, and model coverage status.
- `GET /shelters/recommended` - The subset of recommended shelters near the user/selected location.
- `GET /disaster-alerts` - Currently tracked disaster alerts.
- `GET /shelters` - Complete static dataset of local shelters.
- `GET /road-conditions` - Condition status of monitored roads.
- `GET /gauges` - Location coordinates for official INDOFLOODS gauges.
- `GET /hydrology/water-level` - Demonstrated hydrology data, explicitly labeled as DEMO data.

## Map Layers
The operational map (`OperationsMap`) renders the following layers:
- **OpenStreetMap TileLayer**: Base map tiles.
- **Selected Location**: User's active coordinate or selected map location.
- **Official Gauges**: INDOFLOODS official gauge locations, marked in orange.
- **Shelters**: Locations of tracked shelters from the local dataset, marked in green.
- **Risk Point**: A visual indicator around the selected location indicating the calculated ML model risk (if within supported coverage).
- **Route (OSM)**: The shortest available route on the road network to a selected destination.

## Model Coverage
The dashboard accurately reflects the INDOFLOODS model limitations:
- **Maximum Coverage Limit**: 50 km from an official INDOFLOODS gauge.
- **Coverage Status**: Explicitly displays `MODEL_SUPPORTED` or `MODEL_UNSUPPORTED`.
- It does not generate fake coverage polygons or claim risk levels in unsupported areas.

## Shelter Status
- **Shelter Count**: Dynamically calculated from the total shelter records returned by the backend.
- **Verification Status**: Clearly distinguishes between `VERIFIED` and `PUBLIC_UNVERIFIED` shelters.
- Unverified shelters carry the warning: "NOT VERIFIED AS AN EMERGENCY FLOOD SHELTER."
- No fake occupancy or capacity values are generated.

## Routing Status
- **Network**: Based on the local OpenStreetMap road graph.
- **Status**: The condition of the route and its roads is presented strictly as what is returned by the backend (typically `UNKNOWN`).
- It does not claim routes are guaranteed flood-safe or dynamic.

## Hydrology Demo Status
- The hydrology water-level API is a simulated demo. 
- The dashboard explicitly and prominently labels this data as **DEMO** with the disclaimer: "Water-level information is simulated for demonstration purposes."

## Data Sources
The dashboard explicitly attributes its data sources:
- **Flood model**: INDOFLOODS
- **Rainfall**: Open-Meteo Historical/Reanalysis
- **Shelters**: Local shelter dataset
- **Road network**: OpenStreetMap
- **Hydrology**: DEMO Provider

## Limitations
- **Data Completeness**: Live traffic, temporary road closures, dynamic flooded-road detection, and real-time hydrology are NOT integrated.
- **Decision Support**: The application is an academic/operational prototype and is not a substitute for official disaster management protocols.

## Authentication Limitation
- **No Real Authentication**: For the scope of this step, the Operations view is available via a simple UI toggle. No fake authentication, JWTs, or role verifications are implemented.
- A production deployment would require a robust authentication and authorization system to restrict access to this view.

## API Key Status
**API Key Required:** NO.
This step does not require any external paid API keys. It relies entirely on existing local datasets, open DEMO providers, and the Open-Meteo free API.
