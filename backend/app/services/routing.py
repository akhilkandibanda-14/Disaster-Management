import networkx as nx
from typing import Optional

from app.schemas.resources import ShelterResponse
from app.schemas.route import EvacuationRouteResponse
from app.services.road_network import road_network_service
from shapely.geometry import LineString


MAX_SNAP_DISTANCE_KM = 5.0  # Limit snapping to 5 km


def build_graph_route(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    shelter: Optional[ShelterResponse] = None
) -> EvacuationRouteResponse:
    
    # 1. Ensure the road network is loaded
    try:
        road_network_service.load_graph()
    except Exception as e:
        return _build_error_response("NO_ROUTE", [f"Graph loading failed: {str(e)}"])
    
    G = road_network_service.G

    # 2. Find nearest nodes
    try:
        origin_snap = road_network_service.find_nearest_node(origin_lat, origin_lon)
    except ValueError as e:
        return _build_error_response("INVALID_ORIGIN", [f"Origin: {str(e)}"])
    
    try:
        dest_snap = road_network_service.find_nearest_node(dest_lat, dest_lon)
    except ValueError as e:
        return _build_error_response("INVALID_DESTINATION", [f"Destination: {str(e)}"])

    if origin_snap["distance_km"] > MAX_SNAP_DISTANCE_KM:
        return _build_error_response("ORIGIN_OUTSIDE_NETWORK", ["Origin is too far from any known road."])
    
    if dest_snap["distance_km"] > MAX_SNAP_DISTANCE_KM:
        return _build_error_response("DESTINATION_OUTSIDE_NETWORK", ["Destination is too far from any known road."])

    orig_node = origin_snap["node_id"]
    dest_node = dest_snap["node_id"]

    # 3. Pathfinding (Dijkstra using 'length')
    try:
        route_nodes = nx.shortest_path(G, orig_node, dest_node, weight='length')
        route_length = nx.shortest_path_length(G, orig_node, dest_node, weight='length')
    except nx.NetworkXNoPath:
        return _build_error_response("NO_ROUTE", ["No path exists between the origin and destination."])
    except nx.NodeNotFound:
        return _build_error_response("NO_ROUTE", ["Origin or destination node not found in the graph."])

    # 4. Route Geometry extraction
    # Where edge geometry exists, use it. Otherwise, use node coordinates.
    # Note: GeoJSON is [longitude, latitude]
    geometry = []
    
    # Start with origin coordinate (or we could just start with the node)
    # Adding the original user coordinate first for a complete route visual
    geometry.append([origin_lon, origin_lat])
    
    for i in range(len(route_nodes) - 1):
        u = route_nodes[i]
        v = route_nodes[i + 1]
        
        # In a MultiDiGraph, there could be multiple edges between u and v
        # We take the shortest one
        edge_data = min(G[u][v].values(), key=lambda x: x.get("length", float("inf")))
        
        if "geometry" in edge_data:
            # edge_data["geometry"] is a Shapely LineString
            geom_coords = list(edge_data["geometry"].coords)
            # Add all except the last point (which is the first point of the next edge)
            geometry.extend(geom_coords[:-1])
        else:
            # Fallback to node coordinate
            geometry.append([G.nodes[u]['x'], G.nodes[u]['y']])
            
    # Add the final node coordinate
    geometry.append([G.nodes[dest_node]['x'], G.nodes[dest_node]['y']])
    
    # Add the final destination coordinate
    geometry.append([dest_lon, dest_lat])
    
    # Convert route_length (meters) to km
    route_distance_km = route_length / 1000.0

    # 5. Build response
    shelter_id = shelter.id if shelter else None
    shelter_name = shelter.name if shelter else None

    # We do not fabricate speed, so duration is null if we don't have accurate speed data
    
    return EvacuationRouteResponse(
        geometry=geometry,
        route_distance_km=round(route_distance_km, 2),
        estimated_duration_min=None,
        origin_node=orig_node,
        destination_node=dest_node,
        origin_snap_distance_km=round(origin_snap["distance_km"], 3),
        destination_snap_distance_km=round(dest_snap["distance_km"], 3),
        road_source="OpenStreetMap",
        route_status="ROUTE_AVAILABLE",
        road_condition_status="UNKNOWN",
        shelter_id=shelter_id,
        shelter_name=shelter_name,
        warnings=["Live road flood/blockage conditions are not currently integrated."]
    )

def _build_error_response(status: str, warnings: list[str]) -> EvacuationRouteResponse:
    return EvacuationRouteResponse(
        geometry=[],
        route_distance_km=0.0,
        estimated_duration_min=None,
        origin_node=None,
        destination_node=None,
        origin_snap_distance_km=None,
        destination_snap_distance_km=None,
        road_source="OpenStreetMap",
        route_status=status,
        road_condition_status="UNKNOWN",
        shelter_id=None,
        shelter_name=None,
        warnings=warnings + ["Live road flood/blockage conditions are not currently integrated."]
    )
