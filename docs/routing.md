# Evacuation Routing

## OSM Graph Source
The routing service utilizes local OpenStreetMap (OSM) topological data. The road graph is not downloaded on the fly but is pre-extracted.

## Local Graph File
The graph is loaded from `data/raw/roads/hyderabad_road_network.graphml` using `NetworkX` via `OSMnx`. The service caches this graph in memory to answer routing queries optimally. Thread-safe initialization ensures concurrent requests cannot load multiple graph instances or mutate the underlying network.

## Pathfinding & Hazard Avoidance Algorithm
The service uses Dijkstra's shortest path algorithm (via `networkx.shortest_path`) over a dynamic, read-only graph view constructed with `networkx.restricted_view`.

### How Hazard Avoidance Works:
1. **Hazard Ingestion**: Active road conditions (e.g., from citizen reports, field updates, or simulated demo data) with impassable status (`FLOODED`, `BLOCKED`, `DANGEROUS`) are provided to `build_graph_route`.
2. **Safe Road Matching**:
   - Each hazard's `(latitude, longitude)` coordinate is snapped to the nearest road network node and incident edge segments.
   - If a `road_name` is provided, candidate edges are cross-referenced against the road name.
   - Ambiguous matches (where nearby edges explicitly conflict with reported names) are handled conservatively: the router does not claim a road was avoided unless its affected graph edges were identified.
   - Identified road segments (in both directions) are excluded from the pathfinding view.
3. **Detour Recalculation**:
   - The route is computed using `nx.restricted_view(G, nodes=[], edges=blocked_edges)`.
   - If the shortest unconstrained route intersected a hazard, the service safely recalculates an alternative route avoiding all blocked segments. The response sets `road_condition_status = "HAZARDS_AVOIDED"`.
4. **No-Safe-Route Guarantee**:
   - If all viable paths traverse reported flooded or blocked roads (raising `nx.NetworkXNoPath` on the restricted view while an unconstrained path exists), the API returns `route_status = "NO_SAFE_ROUTE"` and `road_condition_status = "BLOCKED"`.
   - The system **never** silently falls back to a route that crosses a known blocked or flooded road.

## Nearest-Node Snapping
Because users and shelters may not be located perfectly on a road node, their coordinates are snapped to the nearest road network node using spatial indexing in OSMnx. 
- A maximum snapping threshold of **5.0 km** is enforced. 
- If snapping exceeds this, the API returns an `ORIGIN_OUTSIDE_NETWORK` or `DESTINATION_OUTSIDE_NETWORK` error.

## GeoJSON Output
The returned route geometry strictly formats as `[longitude, latitude]` for each point, conforming to the GeoJSON LineString standard so that frontend maps can seamlessly render the route. Where an OSM edge contains intermediate curvature coordinates (LineString geometry), they are included.

## Route Distance
The distance returned is the precise physical length of the graph edges along the path (in km), NOT simply Euclidean distance.

## Duration Limitations
Because real-time speed data is not currently available, `estimated_duration_min` is explicitly returned as `null`. We do not fabricate average speeds or traffic data.

## API Key Requirement
No external API keys are required to use this routing system. It is fully disconnected from Mapbox, Google Maps, and Waze.

## Remaining Limitations
1. **Sparse / Static OSM Naming**: In OSM, some segments lack explicit `name` tags (e.g. minor links or service tracks). In such cases, proximity snapping within conservative thresholds is used.
2. **Elevation & Dynamic Hydrology Penalties**: Edge weights currently use binary exclusion (passable vs. blocked). Dynamic continuous cost weighting (e.g. `weight = length + (flood_depth * factor)`) can be integrated in future milestones when continuous hydrologic models are linked.
3. **Live Condition Sourcing**: In the absence of an active real-time municipal telemetry feed, road conditions are populated via the database or explicitly labeled `[DEMO]` data.
