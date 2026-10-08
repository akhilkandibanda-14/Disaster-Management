# Citizen Disaster-Management Dashboard

## Overview
The Citizen Dashboard is a specialized view within SafeMap AI designed to provide citizens with actionable, transparent, and honest information during a flood emergency. It focuses on answering four critical questions:
1. Where am I?
2. What does the system currently know about flood risk at my location?
3. Where can I go?
4. What route can I take?

## Architecture & Workflows

### Citizen Workflow
1. **Location Resolution**: The dashboard attempts to retrieve the user's live browser location. If unavailable, it falls back to a central Hyderabad location.
2. **Flood Prediction & Weather**: Retrieves the current weather and flood risk level for the location.
3. **Shelter Recommendation**: Automatically fetches the nearest open shelters.
4. **Evacuation Routing**: Users can click "Find OSM Road-Network Route" to calculate the shortest road path from their location to the recommended shelter.

### APIs Consumed
The frontend dashboard consumes the following backend FastAPI endpoints:
- `GET /health` - Validates API status and demo mode.
- `GET /weather` - Retrieves historical/reanalysis rainfall data from Open-Meteo.
- `GET /risk-map` - Uses the INDOFLOODS ML model to predict flood risk.
- `GET /shelters/recommended` - Identifies the nearest available shelters.
- `POST /evacuation-route` - Calculates a graph-based road-network route using local OpenStreetMap data.

## Honest Data Presentation & Limitations

To prevent dangerous misinformation, the Citizen Dashboard heavily emphasizes data transparency and known limitations:

### 1. Model Supported Behavior
The INDOFLOODS model operates within a strict 50 km geographic threshold.
- If the user is inside the coverage area: Displays the prediction, risk level, and model probability.
- If the user is outside the coverage area: Displays **Flood prediction unavailable** and `MODEL_UNSUPPORTED`. It explicitly does not fabricate a probability or risk score.

### 2. Hydrology Demo Status
Since real-time authoritative river gauges are not currently integrated, the system uses a demo hydrology provider. The dashboard prominently displays a **DEMO HYDROLOGY DATA** banner, advising users to follow official disaster-management instructions for real emergencies.

### 3. Shelter Verification Limitations
Shelters are sourced from public data and are marked as **PUBLIC_UNVERIFIED**. The UI actively tells users: *Safety not verified. Not confirmed as an emergency flood shelter.* It does not use the terms "safe" or "guaranteed".

### 4. Routing Limitations
The dashboard provides the *shortest available road-network route* using a static local OpenStreetMap graph. 
- It explicitly warns that **Live traffic and temporary road closures are not currently integrated.**
- The road condition status defaults to `UNKNOWN`.
- Routes are never labeled as "flood-safe".

## API-Key Status
**No API keys are required** to run this dashboard. It relies entirely on local backend ML, local OSM graph data, and free public providers (like Open-Meteo).

## Known Limitations
- Operations and authority dispatch functionalities are deliberately excluded from this view.
- SOS and live disaster alerts are not yet implemented.
- The map relies solely on the open-source Leaflet library without commercial map overlays (e.g., Google Maps).
