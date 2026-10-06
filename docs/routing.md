# Evacuation Routing

## OSM Graph Source
The routing service utilizes local OpenStreetMap (OSM) topological data. The road graph is not downloaded on the fly but is pre-extracted.

## Local Graph File
The graph is loaded from `data/raw/roads/hyderabad_road_network.graphml` using `NetworkX` via `OSMnx`. The service caches this graph in memory to answer routing queries optimally.

## Pathfinding Algorithm
The service uses Dijkstra's shortest path algorithm (via `networkx.shortest_path`) to find the optimal path through the directed road network graph. 

## Routing Objective
The current routing objective strictly minimizes **road network distance** (using the `length` attribute on graph edges). 

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

## Road-Condition Limitation
The routing service has a strict **STATIC** boundary constraint. It currently returns `road_condition_status = "UNKNOWN"`. 
**Why route is NOT currently a verified flood-safe route:**
- We do not know if the generated path crosses currently flooded areas.
- We do not penalize edges for high flood risk or reported blockages.
- The route represents the theoretically shortest physical path, not necessarily the safest path in an active disaster.

## API Key Requirement
No API keys are required to use this routing system. It is fully disconnected from Mapbox, Google Maps, and Waze.

## Future Dynamic Road-Condition Integration
To make the route flood-safe, Step 11+ could integrate dynamic traffic or hydrology indicators as additional weight penalties (e.g. `weight = length + (flood_severity * 1000)`). Until verified real-time road conditions exist, the router explicitly states conditions are unknown.
