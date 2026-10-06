# Static Road Network (Hyderabad)

## 1. Purpose
This module establishes a static road-network foundation for Hyderabad. It provides a real road graph representing the geographic topology of the region, which is essential for upcoming evacuation routing (Step 10) without relying on paid or rate-limited third-party routing APIs like Google Maps.

## 2. Source
The road network data is sourced from **OpenStreetMap (OSM)**, utilizing the `osmnx` and `networkx` Python libraries to extract, construct, and process the topological graph. 

## 3. Geographic Coverage
The extraction queries `"Hyderabad, Telangana, India"` to obtain the official boundary polygons and road segments inside it. The network type is limited to `"drive"` to ensure only drivable roads are included.

## 4. Extraction Method
- Script: `backend/scratch_download_osm.py` runs `osmnx.graph_from_place()` and saves the resulting NetworkX object.
- Stored as GraphML at `data/raw/roads/hyderabad_road_network.graphml`.

## 5. Graph Representation
- The graph is stored and queried as a `NetworkX MultiDiGraph`, enabling traversal that respects road directionality (if available).
- The coordinate reference system (CRS) is `epsg:4326`.

## 6. Node/Edge Counts
*(See backend script output for exact numbers. Generally expected to be in the tens of thousands for Hyderabad.)*
- Nodes represent intersections or endpoints.
- Edges represent road segments.

## 7. Available Attributes
Common attributes parsed from OSM include:
- `osmid`
- `highway` (e.g., primary, secondary, residential)
- `oneway` (boolean for one-way streets)
- `name` (street name)
- `length` (segment length in meters)

## 8. Nearest-Node Functionality
The `RoadNetworkService.find_nearest_node(lat, lon)` function maps arbitrary GPS coordinates (e.g., a user's location or a shelter) to the closest valid point (node) on the road graph. This is the first step before calculating graph shortest-paths.

## 9. Static vs Dynamic Distinction
**CRITICAL:** This data is strictly **STATIC**. 
It represents the physical roads that exist, but it **DOES NOT** represent live road conditions.
- Road flooding: `UNKNOWN`
- Road closures: `UNKNOWN`
- Traffic: `UNKNOWN`

## 10. Limitations
- Does not contain real-time speed data.
- Edges represent physical drivability, not necessarily emergency accessibility.
- Node snapping might be inaccurate in highly dense or overlapping infrastructure (e.g., flyovers vs underlying roads) without elevation data.

## 11. API Key Requirement
**No API key is required.** All data is openly queried from the Overpass API via OSMnx.

## 12. Future Dynamic Road-Condition Integration
If real-time road conditions (e.g., closures from police feeds or live flooded segments) become available from a free, unauthenticated source, they can be projected onto these static edges to alter their weights/traversability dynamically during routing.
