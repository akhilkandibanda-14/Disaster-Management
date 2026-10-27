import networkx as nx
import osmnx as ox
from shapely.geometry import Point, LineString
from typing import Optional, Union, List, Any

from app.schemas.resources import ShelterResponse, RoadConditionResponse
from app.models.resources import RoadCondition
from app.schemas.route import AlternativeRoute, EvacuationRouteResponse
from app.services.road_network import road_network_service


MAX_SNAP_DISTANCE_KM = 5.0  # Limit snapping to 5 km
MAX_HAZARD_SNAP_DISTANCE_M = 150.0  # Maximum radius to snap hazard reports to road network
HAZARD_STATUSES = {"BLOCKED", "FLOODED", "DANGEROUS"}


def match_road_conditions(
    G: nx.MultiDiGraph, 
    road_conditions: List[Any]
) -> tuple[set[tuple[int, int, int]], list[str], list[str]]:
    """
    Conservatively maps road condition reports to affected graph edges in G.
    Returns:
        blocked_edge_keys: set of (u, v, k) 3-tuples for MultiDiGraph exclusion
        matched_hazards: human-readable summaries of positively identified hazards
        unmatched_hazards: warnings for ambiguous or out-of-range hazard reports
    """
    blocked_edge_keys = set()
    matched_hazards = []
    unmatched_hazards = []

    if not road_conditions:
        return blocked_edge_keys, matched_hazards, unmatched_hazards

    for road in road_conditions:
        status = getattr(road, 'status', None) or (road.get('status') if isinstance(road, dict) else '')
        if not status or str(status).upper() not in HAZARD_STATUSES:
            continue

        lat = getattr(road, 'latitude', None) or (road.get('latitude') if isinstance(road, dict) else None)
        lon = getattr(road, 'longitude', None) or (road.get('longitude') if isinstance(road, dict) else None)
        name = getattr(road, 'road_name', None) or (road.get('road_name') if isinstance(road, dict) else None)
        notes = getattr(road, 'notes', None) or (road.get('notes') if isinstance(road, dict) else '')

        if lat is None or lon is None or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            unmatched_hazards.append(f"Hazard report '{name or 'Unknown'}' has invalid coordinates.")
            continue

        try:
            nearest_node, dist_m = ox.distance.nearest_nodes(G, X=lon, Y=lat, return_dist=True)
        except Exception as e:
            unmatched_hazards.append(f"Spatial query failed for hazard '{name or 'Unknown'}': {e}")
            continue

        if dist_m > MAX_HAZARD_SNAP_DISTANCE_M:
            unmatched_hazards.append(
                f"Hazard report '{name or 'Unknown'}' at ({lat:.4f}, {lon:.4f}) is {dist_m:.0f}m from nearest road (threshold {MAX_HAZARD_SNAP_DISTANCE_M}m); could not match to graph."
            )
            continue

        # Collect incident edges connected to nearest_node
        pt = Point(lon, lat)
        incident_edges = []
        for v, edge_dict in G[nearest_node].items():
            for k, data in edge_dict.items():
                incident_edges.append((nearest_node, v, k, data))
        for u in G.pred[nearest_node]:
            for k, data in G.pred[nearest_node][u].items():
                incident_edges.append((u, nearest_node, k, data))

        if not incident_edges:
            unmatched_hazards.append(f"No connected road edges found for hazard '{name or 'Unknown'}' at node {nearest_node}.")
            continue

        # Check name matching if road_name is provided
        name_matched_edges = []
        if name and str(name).strip():
            clean_target = str(name).strip().lower()
            for u, v, k, data in incident_edges:
                edge_name = data.get("name")
                if edge_name:
                    if isinstance(edge_name, list):
                        if any(clean_target in str(en).lower() or str(en).lower() in clean_target for en in edge_name):
                            name_matched_edges.append((u, v, k))
                    else:
                        if clean_target in str(edge_name).lower() or str(edge_name).lower() in clean_target:
                            name_matched_edges.append((u, v, k))

        edges_to_exclude = []
        if name_matched_edges:
            edges_to_exclude = name_matched_edges
        else:
            # Check for name ambiguity: if candidate edges all have explicit names that conflict with target
            conflicting_names = set()
            for u, v, k, data in incident_edges:
                en = data.get("name")
                if en:
                    if isinstance(en, list):
                        conflicting_names.update(str(x) for x in en)
                    else:
                        conflicting_names.add(str(en))

            if name and conflicting_names and dist_m > 50.0:
                unmatched_hazards.append(
                    f"Ambiguous hazard report '{name}': nearest road node ({dist_m:.0f}m) has conflicting names {sorted(conflicting_names)}."
                )
                continue

            # Snap to closest edge geometry connected to the node
            best_edge = None
            min_edge_dist = float('inf')
            for u, v, k, data in incident_edges:
                geom = data.get("geometry")
                if geom is None:
                    geom = LineString([(G.nodes[u]['x'], G.nodes[u]['y']), (G.nodes[v]['x'], G.nodes[v]['y'])])
                d_pt = pt.distance(geom)
                if d_pt < min_edge_dist:
                    min_edge_dist = d_pt
                    best_edge = (u, v, k)

            if best_edge:
                u, v, k = best_edge
                edges_to_exclude.append((u, v, k))
                # Exclude reverse edge if present to prevent routing in either direction
                if G.has_edge(v, u):
                    for rk in G[v][u]:
                        edges_to_exclude.append((v, u, rk))

        if edges_to_exclude:
            for edge_key in edges_to_exclude:
                blocked_edge_keys.add(edge_key)
            label_prefix = "[DEMO] " if ("[demo]" in str(notes).lower() or "[demo]" in str(name).lower()) else ""
            matched_hazards.append(f"{label_prefix}{name or 'Road Segment'} ({status}) near ({lat:.4f}, {lon:.4f})")

    return blocked_edge_keys, matched_hazards, unmatched_hazards


def build_graph_route(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    shelter: Optional[ShelterResponse] = None,
    road_conditions: Optional[List[Union[RoadConditionResponse, RoadCondition, dict]]] = None,
    compute_alternatives: bool = True
) -> EvacuationRouteResponse:
    
    # 1. Ensure the road network is loaded
    try:
        road_network_service.load_graph()
    except Exception as e:
        base_warn = [f"Graph loading failed: {str(e)}"]
        if road_conditions is None:
            base_warn.append("Live road flood/blockage conditions are not currently integrated.")
        return _build_error_response("NO_ROUTE", base_warn)
    
    G = road_network_service.G
    if G is None:
        base_warn = ["Road network graph is unavailable."]
        if road_conditions is None:
            base_warn.append("Live road flood/blockage conditions are not currently integrated.")
        return _build_error_response("NO_ROUTE", base_warn)

    # 2. Find nearest nodes
    try:
        origin_snap = road_network_service.find_nearest_node(origin_lat, origin_lon)
    except ValueError as e:
        base_warn = [f"Origin: {str(e)}"]
        if road_conditions is None:
            base_warn.append("Live road flood/blockage conditions are not currently integrated.")
        return _build_error_response("INVALID_ORIGIN", base_warn)
    
    try:
        dest_snap = road_network_service.find_nearest_node(dest_lat, dest_lon)
    except ValueError as e:
        base_warn = [f"Destination: {str(e)}"]
        if road_conditions is None:
            base_warn.append("Live road flood/blockage conditions are not currently integrated.")
        return _build_error_response("INVALID_DESTINATION", base_warn)

    if origin_snap["distance_km"] > MAX_SNAP_DISTANCE_KM:
        base_warn = ["Origin is too far from any known road."]
        if road_conditions is None:
            base_warn.append("Live road flood/blockage conditions are not currently integrated.")
        return _build_error_response("ORIGIN_OUTSIDE_NETWORK", base_warn)
    
    if dest_snap["distance_km"] > MAX_SNAP_DISTANCE_KM:
        base_warn = ["Destination is too far from any known road."]
        if road_conditions is None:
            base_warn.append("Live road flood/blockage conditions are not currently integrated.")
        return _build_error_response("DESTINATION_OUTSIDE_NETWORK", base_warn)

    orig_node = origin_snap["node_id"]
    dest_node = dest_snap["node_id"]

    warnings: list[str] = []

    # 3. Hazard edge evaluation & restricted view setup
    if road_conditions is None:
        road_condition_status = "UNKNOWN"
        warnings.append("Live road flood/blockage conditions are not currently integrated.")
        G_eval = G
        blocked_edges: set[tuple[int, int, int]] = set()
        matched_hazards: list[str] = []
    else:
        blocked_edges, matched_hazards, unmatched_hazards = match_road_conditions(G, road_conditions)
        warnings.extend(unmatched_hazards)
        if blocked_edges:
            G_eval = nx.restricted_view(G, nodes=[], edges=blocked_edges)
        else:
            G_eval = G
        road_condition_status = "CLEAR"

    # 4. Pathfinding on safe graph view
    try:
        route_nodes = nx.shortest_path(G_eval, orig_node, dest_node, weight='length')
        route_length = nx.shortest_path_length(G_eval, orig_node, dest_node, weight='length')
    except nx.NetworkXNoPath:
        # Check if an unconstrained path exists in G that was severed by hazards
        if blocked_edges and nx.has_path(G, orig_node, dest_node):
            from app.utils.observability import health_monitor
            health_monitor.record_route_failure(
                origin={"latitude": origin_lat, "longitude": origin_lon},
                destination={"latitude": dest_lat, "longitude": dest_lon},
                reason="NO_SAFE_ROUTE: All viable paths traverse reported flooded or blocked roads.",
            )
            return _build_error_response(
                status="NO_SAFE_ROUTE",
                warnings=[
                    "No safe evacuation route could be found. All viable paths traverse reported flooded or blocked roads."
                ] + [f"Avoided hazard: {h}" for h in matched_hazards] + warnings,
                road_condition_status="BLOCKED"
            )
        return _build_error_response(
            status="NO_ROUTE",
            warnings=["No path exists between the origin and destination."] + warnings,
            road_condition_status=road_condition_status
        )
    except nx.NodeNotFound:
        return _build_error_response("NO_ROUTE", ["Origin or destination node not found in the graph."])

    # 5. Assess if hazards were avoided
    if road_conditions is not None and blocked_edges:
        try:
            unconstrained_nodes = nx.shortest_path(G, orig_node, dest_node, weight='length')
            unconstrained_edges = {
                (u, v, k)
                for u, v in zip(unconstrained_nodes[:-1], unconstrained_nodes[1:])
                for k in G[u][v]
            }
            if (unconstrained_edges & blocked_edges) or route_nodes != unconstrained_nodes:
                road_condition_status = "HAZARDS_AVOIDED"
                warnings.append(
                    f"Route recalculated to safely avoid {len(matched_hazards)} hazardous/blocked road segment(s)."
                )
                for h in matched_hazards:
                    warnings.append(f"Avoided hazard: {h}")
            else:
                road_condition_status = "CLEAR"
                warnings.append("Evaluated road conditions: no reported hazards intersected this route.")
        except Exception:
            road_condition_status = "HAZARDS_AVOIDED"

    # 6. Route Geometry extraction
    # GeoJSON format is [longitude, latitude]
    geometry = []
    geometry.append([origin_lon, origin_lat])
    
    for i in range(len(route_nodes) - 1):
        u = route_nodes[i]
        v = route_nodes[i + 1]
        
        # Take shortest edge between u and v in G_eval
        edge_data = min(G_eval[u][v].values(), key=lambda x: x.get("length", float("inf")))
        
        if "geometry" in edge_data:
            geom_coords = list(edge_data["geometry"].coords)
            geometry.extend(geom_coords[:-1])
        else:
            geometry.append([G.nodes[u]['x'], G.nodes[u]['y']])
            
    geometry.append([G.nodes[dest_node]['x'], G.nodes[dest_node]['y']])
    geometry.append([dest_lon, dest_lat])
    
    route_distance_km = route_length / 1000.0
    is_rerouted = (road_condition_status == "HAZARDS_AVOIDED")
    if road_conditions is not None and route_distance_km > 0:
        speed_kmh = 18.0 if is_rerouted else 30.0
        estimated_duration_min = max(1, round((route_distance_km / speed_kmh) * 60))
    else:
        estimated_duration_min = None

    # Compute alternative evacuation path if requested
    alternatives: List[AlternativeRoute] = []
    if compute_alternatives and len(route_nodes) > 3:
        try:
            mid = len(route_nodes) // 2
            u_pen = route_nodes[mid]
            v_pen = route_nodes[mid + 1]
            edges_to_avoid = {(u_pen, v_pen, k) for k in G_eval[u_pen][v_pen]}
            if G_eval.has_edge(v_pen, u_pen):
                edges_to_avoid.update({(v_pen, u_pen, k) for k in G_eval[v_pen][u_pen]})
            G_alt = nx.restricted_view(G_eval, nodes=[], edges=edges_to_avoid)
            if nx.has_path(G_alt, orig_node, dest_node):
                alt_nodes = nx.shortest_path(G_alt, orig_node, dest_node, weight='length')
                alt_len = nx.shortest_path_length(G_alt, orig_node, dest_node, weight='length')
                alt_dist_km = round(alt_len / 1000.0, 2)
                if alt_nodes != route_nodes and alt_dist_km <= route_distance_km * 2.5:
                    alt_geom = [[origin_lon, origin_lat]]
                    for j in range(len(alt_nodes) - 1):
                        u_a, v_a = alt_nodes[j], alt_nodes[j + 1]
                        e_data = min(G_alt[u_a][v_a].values(), key=lambda x: x.get("length", float("inf")))
                        if "geometry" in e_data:
                            alt_geom.extend(list(e_data["geometry"].coords)[:-1])
                        else:
                            alt_geom.append([G.nodes[u_a]['x'], G.nodes[u_a]['y']])
                    alt_geom.append([G.nodes[dest_node]['x'], G.nodes[dest_node]['y']])
                    alt_geom.append([dest_lon, dest_lat])
                    alt_dur = max(1, round((alt_dist_km / 22.0) * 60)) if road_conditions is not None else None
                    alternatives.append(AlternativeRoute(
                        geometry=alt_geom,
                        route_distance_km=alt_dist_km,
                        estimated_duration_min=alt_dur,
                        road_condition_status="CLEAR" if not is_rerouted else "HAZARDS_AVOIDED",
                        description=f"Secondary arterial bypass route via {alt_dist_km:.2f} km" + (f" (~{alt_dur} min)." if alt_dur else ".")
                    ))
        except Exception:
            pass

    # Mandatory route safety warning
    safety_disclaimer_note = "Safety notice: Evacuation routes cannot be guaranteed 100% safe from dynamic rapid inundation; heed local emergency authority directions."
    if safety_disclaimer_note not in warnings:
        warnings.append(safety_disclaimer_note)

    shelter_id = getattr(shelter, 'id', None)
    shelter_name = getattr(shelter, 'name', None)
    facility_id = getattr(shelter, 'facility_id', None) or getattr(shelter, 'shelter_id', None)
    destination_name = getattr(shelter, 'name', None)
    destination_type = getattr(shelter, 'facility_type', None) or ("SHELTER" if shelter is not None else None)

    return EvacuationRouteResponse(
        geometry=geometry,
        route_distance_km=round(route_distance_km, 2),
        estimated_duration_min=estimated_duration_min,
        origin_node=orig_node,
        destination_node=dest_node,
        origin_snap_distance_km=round(origin_snap["distance_km"], 3),
        destination_snap_distance_km=round(dest_snap["distance_km"], 3),
        road_source="OpenStreetMap",
        route_status="ROUTE_AVAILABLE",
        road_condition_status=road_condition_status,
        shelter_id=shelter_id,
        shelter_name=shelter_name,
        facility_id=facility_id,
        destination_name=destination_name,
        destination_type=destination_type,
        is_rerouted=is_rerouted,
        warnings=warnings,
        alternatives=alternatives
    )


def _build_error_response(
    status: str, 
    warnings: list[str], 
    road_condition_status: str = "UNKNOWN",
    shelter_id: Optional[int] = None,
    shelter_name: Optional[str] = None,
    facility_id: Optional[str] = None,
    destination_name: Optional[str] = None,
    destination_type: Optional[str] = None,
) -> EvacuationRouteResponse:
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
        road_condition_status=road_condition_status,
        shelter_id=shelter_id,
        shelter_name=shelter_name,
        facility_id=facility_id,
        destination_name=destination_name,
        destination_type=destination_type,
        is_rerouted=False,
        warnings=warnings
    )
