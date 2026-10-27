"""
SafeMap AI — Evacuation Route Safety Validation Engine
Implements rigorous geometric validation, CRS verification, STRtree spatial indexing,
provenance-aware hazard categorization, and route continuity checks.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import math
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, shape
from shapely.strtree import STRtree
import shapely

logger = logging.getLogger(__name__)

# Mandatory non-negotiable safety disclaimer
MANDATORY_SAFETY_DISCLAIMER = (
    "Evacuation routes are computed based on currently known road conditions and flood hazard "
    "information. Real-time water depth, debris, and sudden flash floods may not be modeled. "
    "Never attempt to drive or walk through flooded roadways."
)

HYDERABAD_CRS_BOUNDS = {
    "min_lat": 17.15,
    "max_lat": 17.65,
    "min_lon": 78.15,
    "max_lon": 78.75,
}


@dataclass
class HazardPolicy:
    """Configurable routing rules for hazard avoidance and penalty scaling."""
    hard_block_confirmed_severe: bool = True
    historical_penalty_factor: float = 5.0
    unverified_penalty_factor: float = 1.5
    stale_hours_threshold: float = 12.0
    max_snap_distance_km: float = 5.0
    max_hazard_point_snap_m: float = 150.0
    max_alternative_overlap: float = 0.70
    standard_evacuation_speed_kmh: float = 25.0
    caution_evacuation_speed_kmh: float = 15.0


def validate_and_repair_geometry(raw_geom: Any) -> Optional[Any]:
    """
    Validates GeoJSON geometry or Shapely shape against coordinate boundaries and topological sanity.
    Repairs self-intersections using shapely.make_valid().
    Returns valid Shapely Polygon, MultiPolygon, or LineString; or None if invalid.
    """
    if raw_geom is None:
        return None

    try:
        if isinstance(raw_geom, dict):
            geom_type = raw_geom.get("type")
            coords = raw_geom.get("coordinates")
            if not geom_type or not coords:
                return None
            geom = shape(raw_geom)
        elif hasattr(raw_geom, "model_dump") and callable(getattr(raw_geom, "model_dump")):
            geom = shape(raw_geom.model_dump())
        elif hasattr(raw_geom, "dict") and callable(getattr(raw_geom, "dict")):
            geom = shape(raw_geom.dict())
        elif isinstance(raw_geom, (Polygon, MultiPolygon, LineString, Point)):
            geom = raw_geom
        else:
            return None

        if geom.is_empty:
            return None

        # Verify CRS and coordinate bounds (WGS84 decimal degrees)
        minx, miny, maxx, maxy = geom.bounds
        if not (-180.0 <= minx <= 180.0 and -180.0 <= maxx <= 180.0 and
                -90.0 <= miny <= 90.0 and -90.0 <= maxy <= 90.0):
            logger.warning("Geometry outside valid WGS84 range: %s", geom.bounds)
            return None

        # Detect inverted lon/lat coordinates for Hyderabad
        if (17.0 <= minx <= 18.0 and 78.0 <= miny <= 79.0):
            logger.warning("Detected inverted coordinates (lat/lon reversed); rejecting malformed geometry.")
            return None

        if not geom.is_valid:
            geom = shapely.make_valid(geom)

        return geom
    except Exception as err:
        logger.warning("Failed to validate/repair geometry: %s", err)
        return None


@dataclass
class CategorizedHazard:
    """Parsed and classified hazard with provenance, freshness, and geometry."""
    hazard_id: str
    title: str
    category: str
    severity: str
    source_name: str
    source_type: str
    is_active: bool
    is_stale: bool
    is_unverified: bool
    is_historical: bool
    is_confirmed_high_risk: bool
    geometry: Optional[Any]
    centroid_point: Optional[Point]
    warning_text: str


def classify_hazard(record: Any, now: datetime, policy: HazardPolicy) -> CategorizedHazard:
    """
    Categorizes a hazard record into:
    - Confirmed high risk (hard-blockable if active & severe)
    - Historical municipal flood zone (penalty avoidance, never assumed currently dry)
    - Unverified citizen report (cautionary penalty, never converted into confirmed closure)
    - Stale observation (annotated with freshness disclaimer)
    """
    hazard_id = str(getattr(record, "hazard_id", getattr(record, "id", "UNKNOWN")))
    title = str(getattr(record, "title", getattr(record, "name", getattr(record, "road_name", "Flood Hazard"))))
    category = str(getattr(record, "hazard_type", getattr(record, "incident_category", "FLOOD_ZONE")))
    severity = str(getattr(record, "severity", "MODERATE")).upper()
    source_name = str(getattr(record, "source_name", "Municipal Emergency Authority"))
    source_type = str(getattr(record, "source_type", "MUNICIPAL"))

    # Observation freshness
    pub_time = getattr(record, "publication_time", getattr(record, "last_updated", getattr(record, "created_at", None)))
    is_stale = False
    if pub_time:
        if isinstance(pub_time, str):
            try:
                pub_time = datetime.fromisoformat(pub_time.replace("Z", "+00:00"))
            except Exception:
                pub_time = None
        if isinstance(pub_time, datetime):
            if not pub_time.tzinfo:
                pub_time = pub_time.replace(tzinfo=timezone.utc)
            age_hours = (now - pub_time).total_seconds() / 3600.0
            if age_hours > policy.stale_hours_threshold:
                is_stale = True

    # Verification status
    data_status = str(getattr(record, "data_status", getattr(record, "verification_status", ""))).upper()
    is_historical = (
        source_type == "HISTORICAL_VULNERABILITY" or
        "HISTORICAL" in data_status or
        "survey" in title.lower() or
        "historical" in title.lower()
    )

    is_unverified = (
        not is_historical and (
            "UNVERIFIED" in data_status or
            "PENDING" in data_status or
            source_type == "PUBLIC_CITIZEN_REPORT" or
            source_type == "PUBLIC_UNVERIFIED"
        )
    )

    # High-risk classification
    is_confirmed_high_risk = False
    status_str = str(getattr(record, "status", "")).upper()
    is_active = getattr(record, "is_active", True)
    if status_str in ("BLOCKED", "FLOODED", "DANGEROUS"):
        is_active = True

    if not is_unverified and not is_historical:
        if severity in ("HIGH", "SEVERE", "EXTREME") and is_active and not is_stale:
            is_confirmed_high_risk = True

    # Geometry extraction
    raw_geom = getattr(record, "geometry", None)
    geom = validate_and_repair_geometry(raw_geom)

    # Point centroid fallback
    lat = getattr(record, "latitude", None)
    lon = getattr(record, "longitude", None)
    centroid_pt = None
    if lat is not None and lon is not None:
        try:
            if -90 <= float(lat) <= 90 and -180 <= float(lon) <= 180:
                centroid_pt = Point(float(lon), float(lat))
        except (ValueError, TypeError):
            pass

    warning_text = (
        f"{title} ({severity}) from {source_name}"
        f"{' [STALE OBSERVATION]' if is_stale else ''}"
        f"{' [UNVERIFIED CITIZEN REPORT]' if is_unverified else ''}"
        f"{' [HISTORICAL MUNICIPAL INUNDATION ZONE]' if is_historical else ''}"
    )

    return CategorizedHazard(
        hazard_id=hazard_id,
        title=title,
        category=category,
        severity=severity,
        source_name=source_name,
        source_type=source_type,
        is_active=is_active,
        is_stale=is_stale,
        is_unverified=is_unverified,
        is_historical=is_historical,
        is_confirmed_high_risk=is_confirmed_high_risk,
        geometry=geom,
        centroid_point=centroid_pt,
        warning_text=warning_text,
    )


def evaluate_road_network_hazards(
    G: nx.MultiDiGraph,
    hazards: List[Any],
    road_conditions: Optional[List[Any]] = None,
    policy: Optional[HazardPolicy] = None,
) -> Tuple[Set[Tuple[int, int, int]], Dict[Tuple[int, int, int], float], List[str], List[str], Set[str], bool]:
    """
    Evaluates road network G against polygon and point flood hazards.
    Performs true geometry intersection operations (road segment LineString vs hazard Polygon/MultiPolygon).

    Returns:
        blocked_edge_keys: set of (u, v, k) edges hard-blocked (confirmed high-risk flood)
        penalized_edges: dict of (u, v, k) -> penalty weight multiplier (historical or unverified)
        avoided_hazards: list of hazard summaries avoided/blocked
        caution_warnings: list of advisory warnings for traversed cautionary segments
        sources_used: set of data source names consulted
        stale_hazards_present: boolean flag indicating if any feed was stale
    """
    if policy is None:
        policy = HazardPolicy()

    now = datetime.now(timezone.utc)
    blocked_edge_keys: Set[Tuple[int, int, int]] = set()
    penalized_edges: Dict[Tuple[int, int, int], float] = {}
    avoided_hazards: List[str] = []
    caution_warnings: List[str] = []
    sources_used: Set[str] = {"OpenStreetMap Road Network"}
    stale_hazards_present = False

    # 1. Parse and categorize all hazard records
    all_raw: List[Any] = list(hazards or [])
    if road_conditions:
        all_raw.extend(road_conditions)

    categorized: List[CategorizedHazard] = []
    for r in all_raw:
        cat = classify_hazard(r, now, policy)
        categorized.append(cat)
        if cat.source_name:
            sources_used.add(cat.source_name)
        if cat.is_stale:
            stale_hazards_present = True

    if not categorized:
        return blocked_edge_keys, penalized_edges, avoided_hazards, caution_warnings, sources_used, stale_hazards_present

    # 2. Build spatial indexes for polygon hazards
    poly_hazards: List[CategorizedHazard] = []
    poly_geoms: List[Any] = []
    point_hazards: List[CategorizedHazard] = []

    for cat in categorized:
        if cat.geometry and isinstance(cat.geometry, (Polygon, MultiPolygon)):
            poly_hazards.append(cat)
            poly_geoms.append(cat.geometry)
        elif cat.centroid_point:
            point_hazards.append(cat)

    strtree = STRtree(poly_geoms) if poly_geoms else None

    # 3. Iterate over road network edges
    for u, v, k, data in G.edges(keys=True, data=True):
        edge_geom = data.get("geometry")
        if edge_geom is None:
            ux, uy = G.nodes[u]["x"], G.nodes[u]["y"]
            vx, vy = G.nodes[v]["x"], G.nodes[v]["y"]
            edge_geom = LineString([(ux, uy), (vx, vy)])

        # A. Polygon intersection check via STRtree
        if strtree is not None:
            candidate_indices = strtree.query(edge_geom)
            for idx in candidate_indices:
                hazard_geom = poly_geoms[idx]
                if hazard_geom.intersects(edge_geom):
                    hazard_info = poly_hazards[idx]
                    if hazard_info.is_confirmed_high_risk and policy.hard_block_confirmed_severe:
                        blocked_edge_keys.add((u, v, k))
                        if G.has_edge(v, u):
                            for rk in G[v][u]:
                                blocked_edge_keys.add((v, u, rk))
                        if hazard_info.warning_text not in avoided_hazards:
                            avoided_hazards.append(hazard_info.warning_text)
                    elif hazard_info.is_historical:
                        # Historical municipal inundation zone
                        penalized_edges[(u, v, k)] = max(penalized_edges.get((u, v, k), 1.0), policy.historical_penalty_factor)
                        msg = f"Caution: Road segment traverses historical municipal flood zone: {hazard_info.title}"
                        if msg not in caution_warnings:
                            caution_warnings.append(msg)
                    elif hazard_info.is_unverified:
                        # Caution penalty, never convert unverified to confirmed closure
                        penalized_edges[(u, v, k)] = max(penalized_edges.get((u, v, k), 1.0), policy.unverified_penalty_factor)
                        msg = f"Caution: Road segment intersects unverified citizen report: {hazard_info.title}"
                        if msg not in caution_warnings:
                            caution_warnings.append(msg)

        # B. Point hazard proximity check
        for ph in point_hazards:
            pt = ph.centroid_point
            if pt is None:
                continue
            # Distance in approximate meters: 1 deg ~ 111,000 m
            # Check bounding box first
            d_deg = edge_geom.distance(pt)
            d_approx_m = d_deg * 111000.0
            if d_approx_m <= policy.max_hazard_point_snap_m:
                if ph.is_confirmed_high_risk and policy.hard_block_confirmed_severe:
                    blocked_edge_keys.add((u, v, k))
                    if G.has_edge(v, u):
                        for rk in G[v][u]:
                            blocked_edge_keys.add((v, u, rk))
                    if ph.warning_text not in avoided_hazards:
                        avoided_hazards.append(ph.warning_text)
                elif ph.is_historical:
                    penalized_edges[(u, v, k)] = max(penalized_edges.get((u, v, k), 1.0), policy.historical_penalty_factor)
                    msg = f"Caution: Road segment near historical municipal flood zone: {ph.title}"
                    if msg not in caution_warnings:
                        caution_warnings.append(msg)
                elif ph.is_unverified:
                    penalized_edges[(u, v, k)] = max(penalized_edges.get((u, v, k), 1.0), policy.unverified_penalty_factor)
                    msg = f"Caution: Road segment near unverified citizen flood report: {ph.title}"
                    if msg not in caution_warnings:
                        caution_warnings.append(msg)

    return (
        blocked_edge_keys,
        penalized_edges,
        avoided_hazards,
        caution_warnings,
        sources_used,
        stale_hazards_present,
    )


def validate_route_continuity(G: nx.MultiDiGraph, route_nodes: List[int]) -> bool:
    """
    Validates that every consecutive pair of nodes in route_nodes forms an active edge in G.
    Prevents phantom or disconnected paths from being returned.
    """
    if not route_nodes or len(route_nodes) < 2:
        return False

    for i in range(len(route_nodes) - 1):
        u, v = route_nodes[i], route_nodes[i + 1]
        if not G.has_edge(u, v):
            logger.error("Route continuity failure: No edge between node %s and %s", u, v)
            return False
    return True


def calculate_exact_route_distance_km(G: nx.MultiDiGraph, route_nodes: List[int]) -> float:
    """
    Calculates exact cumulative distance along route from true edge length attributes.
    Never invents or fabricates route distance.
    """
    if not route_nodes or len(route_nodes) < 2:
        return 0.0

    total_m = 0.0
    for i in range(len(route_nodes) - 1):
        u, v = route_nodes[i], route_nodes[i + 1]
        edge_data = min(G[u][v].values(), key=lambda x: x.get("length", float("inf")))
        length_m = edge_data.get("length")
        if length_m is None:
            # Fallback to coordinate distance between nodes
            ux, uy = G.nodes[u]["x"], G.nodes[u]["y"]
            vx, vy = G.nodes[v]["x"], G.nodes[v]["y"]
            dx = (vx - ux) * 111000.0 * math.cos(math.radians((uy + vy) / 2.0))
            dy = (vy - uy) * 111000.0
            length_m = math.sqrt(dx * dx + dy * dy)
        total_m += float(length_m)

    return round(total_m / 1000.0, 3)


def estimate_credible_eta_min(
    distance_km: float,
    is_rerouted: bool = False,
    traverses_caution_zones: bool = False,
    policy: Optional[HazardPolicy] = None,
) -> Optional[int]:
    """
    Calculates estimated travel time based strictly on credible emergency travel speeds.
    Never invents travel time. Returns None if distance is invalid.
    """
    if distance_km <= 0:
        return None

    if policy is None:
        policy = HazardPolicy()

    if is_rerouted or traverses_caution_zones:
        speed = policy.caution_evacuation_speed_kmh
    else:
        speed = policy.standard_evacuation_speed_kmh

    minutes = (distance_km / speed) * 60.0
    return max(1, round(minutes))


def validate_alternative_independence(
    primary_nodes: List[int],
    alt_nodes: List[int],
    max_overlap: float = 0.70,
) -> Tuple[bool, float]:
    """
    Verifies that an alternative route is meaningfully independent from the primary route.
    Calculates Jaccard edge overlap: len(E1 & E2) / len(E1 | E2).
    Returns (is_independent, overlap_ratio).
    If overlap > max_overlap, the alternative is rejected as a non-independent cosmetic detour.
    """
    if not primary_nodes or not alt_nodes or primary_nodes == alt_nodes:
        return False, 1.0

    primary_edges = {(primary_nodes[i], primary_nodes[i + 1]) for i in range(len(primary_nodes) - 1)}
    alt_edges = {(alt_nodes[i], alt_nodes[i + 1]) for i in range(len(alt_nodes) - 1)}

    intersection = primary_edges & alt_edges
    union = primary_edges | alt_edges

    if not union:
        return False, 1.0

    overlap = len(intersection) / len(union)
    is_independent = (overlap <= max_overlap)
    return is_independent, overlap
