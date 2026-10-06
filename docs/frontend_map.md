# Interactive Disaster Management Map (Frontend)

This document outlines the implementation details for the Step 11 React frontend. 

## Design Philosophy & Scientific Rules
The frontend strictly adheres to visualizing only what the backend currently knows and provides. It explicitly rejects creating any synthetic or fabricated UI visualizations that attempt to hide the uncertainty of the underlying data. 

Key principles implemented:
1. **Uncertainty Transparency**: 
   - Preserves `MODEL_SUPPORTED` and `MODEL_UNSUPPORTED` status from the risk service.
   - Preserves `PUBLIC_UNVERIFIED` shelter status directly in the UI.
   - Shows road conditions as `UNKNOWN` rather than fabricating safety.
2. **Honest Routing**:
   - The route display explicitly labels paths as "Shortest available road-network route" or "OSM road-network route", entirely abandoning previously fabricated "Safe Route" terms.
   - Does not fabricate travel times; displays "Travel time unavailable" when the backend cannot provide it.
3. **Open-Source Tooling**:
   - Built exclusively with `react-leaflet`, `leaflet`, and OpenStreetMap tile layers. 
   - No API keys or commercial map provider dependencies are required or used.

## Map Visualization

The `RiskMap` component is responsible for:
- Rendering the user's location.
- Mapping the point-based predicted risk location and coloring it based on the `risk_level` (Red for High, Yellow for Medium, Green for Low).
- Mapping the top recommended shelter as a distinct marker with a `PUBLIC_UNVERIFIED` warning.
- Drawing the routing path returned by the `/evacuation-route` GeoJSON endpoint natively via Leaflet's `<Polyline>`.

## API Integration

The frontend uses standard `fetch` API methods hitting the FastAPI backend directly on standard endpoints:
- `GET /risk-map?latitude=X&longitude=Y` for geographic point risk (replaces old zone polygons).
- `GET /shelters/recommended?latitude=X&longitude=Y&radius_km=15.0&top_n=3` for the closest shelters.
- `POST /evacuation-route` which submits origin/destination coordinates natively and receives actual graph-based paths from OSMnx/NetworkX.

All legacy "fake" metrics were stripped out of the Operations dashboard, falling back on raw counts from the DB.
