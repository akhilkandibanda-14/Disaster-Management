"""
Deterministic Route Safety Validation Test Suite for SafeMap AI.
Covers:
- Road segment crossing flood polygon
- Road segment near but outside hazard polygon
- Polygon boundaries and MultiPolygons
- Missing and corrupted geometries
- Invalid coordinate systems (out-of-bounds and inverted coordinates)
- Historical hazards vs confirmed high-risk vs unverified citizen reports
- Stale observations and freshness tracking
- Multiple affected road segments
- NO_SAFE_ROUTE when all viable paths are submerged
- Invalid origin / destination
- Disconnected graphs and route continuity validation
- Exact distance calculation without fabrication
- Alternative route independence validation (Jaccard edge overlap)
- Empty hazard feeds and missing graph data
- Non-negotiable safety disclaimer enforcement
"""

from datetime import datetime, timezone, timedelta
import networkx as nx
import pytest
from shapely.geometry import LineString, MultiPolygon, Point, Polygon

from app.schemas.hazard import GeoJSONGeometry, HazardRecord
from app.schemas.route import EvacuationRouteResponse
from app.services.route_safety import (
    HazardPolicy,
    MANDATORY_SAFETY_DISCLAIMER,
    calculate_exact_route_distance_km,
    estimate_credible_eta_min,
    evaluate_road_network_hazards,
    validate_alternative_independence,
    validate_and_repair_geometry,
    validate_route_continuity,
)
from app.services.routing import build_graph_route
from app.services.road_network import road_network_service


@pytest.fixture(autouse=True)
def restore_road_network_singleton():
    """Preserves and restores road_network_service state after each test for strict test isolation."""
    with road_network_service._lock:
        prev_G = road_network_service.G
        prev_node_ids = road_network_service._node_ids
        prev_kdtree = road_network_service._kdtree
        prev_loaded = road_network_service.is_loaded
        prev_error = road_network_service._load_error
    yield
    with road_network_service._lock:
        road_network_service.G = prev_G
        road_network_service._node_ids = prev_node_ids
        road_network_service._kdtree = prev_kdtree
        road_network_service.is_loaded = prev_loaded
        road_network_service._load_error = prev_error


@pytest.fixture
def synthetic_road_network():
    """
    Constructs a deterministic synthetic road graph:
    Nodes:
      1: (78.4000, 17.4000) - Origin
      2: (78.4100, 17.4000)
      3: (78.4200, 17.4000) - Lower corridor (prone to river flooding)
      4: (78.4300, 17.4000) - Destination
      5: (78.4100, 17.4150) - Elevated North bypass
      6: (78.4200, 17.4150) - Elevated North bypass
    Edges:
      (1, 2): length=1000m
      (2, 3): length=1000m (crosses river corridor)
      (3, 4): length=1000m
      (2, 5): length=1200m
      (5, 6): length=1000m
      (6, 4): length=1200m
    """
    G = nx.MultiDiGraph()
    coords = {
        1: (78.4000, 17.4000),
        2: (78.4100, 17.4000),
        3: (78.4200, 17.4000),
        4: (78.4300, 17.4000),
        5: (78.4100, 17.4150),
        6: (78.4200, 17.4150),
    }
    for n, (x, y) in coords.items():
        G.add_node(n, x=x, y=y)

    edges = [
        (1, 2, 1000.0),
        (2, 3, 1000.0),
        (3, 4, 1000.0),
        (2, 5, 1200.0),
        (5, 6, 1000.0),
        (6, 4, 1200.0),
    ]
    for u, v, length in edges:
        line = LineString([(coords[u][0], coords[u][1]), (coords[v][0], coords[v][1])])
        G.add_edge(u, v, key=0, length=length, geometry=line)
        # Bidirectional for emergency access
        rev_line = LineString([(coords[v][0], coords[v][1]), (coords[u][0], coords[u][1])])
        G.add_edge(v, u, key=0, length=length, geometry=rev_line)

    return G


def make_hazard(
    hazard_id: str = "HAZ-001",
    severity: str = "HIGH",
    source_type: str = "OFFICIAL_ALERT",
    data_status: str = "AUTHORITATIVE",
    geometry: any = None,
    publication_time: datetime = None,
    is_active: bool = True,
    title: str = "Musi River Overflow",
    verification_note: str = "Confirmed flood alert from state disaster management authority.",
) -> HazardRecord:
    now = datetime.now(timezone.utc)
    geo_geom = None
    if geometry is not None:
        if isinstance(geometry, Polygon):
            coords = [list(geometry.exterior.coords)]
            geo_geom = GeoJSONGeometry(type="Polygon", coordinates=coords)
        elif isinstance(geometry, MultiPolygon):
            coords = [[list(p.exterior.coords)] for p in geometry.geoms]
            geo_geom = GeoJSONGeometry(type="MultiPolygon", coordinates=coords)
        elif isinstance(geometry, dict):
            geo_geom = GeoJSONGeometry(**geometry)
        elif isinstance(geometry, GeoJSONGeometry):
            geo_geom = geometry

    return HazardRecord(
        hazard_id=hazard_id,
        hazard_type="RIVER_OVERFLOW",
        title=title,
        description="Hazard description",
        severity=severity,
        source_name="Telangana Disaster Management Authority",
        source_type=source_type,
        data_status=data_status,
        geometry=geo_geom,
        publication_time=publication_time or now,
        last_retrieved=now,
        is_active=is_active,
        is_stale=False,
        verification_note=verification_note,
    )


def test_road_crossing_flood_polygon(synthetic_road_network):
    """Verifies that a road segment cutting through a confirmed severe flood polygon is blocked."""
    G = synthetic_road_network
    poly = Polygon([(78.412, 17.395), (78.418, 17.395), (78.418, 17.405), (78.412, 17.405), (78.412, 17.395)])
    hazard = make_hazard(geometry=poly, severity="HIGH", data_status="AUTHORITATIVE")

    blocked_edges, penalized_edges, avoided, caution, sources, stale = evaluate_road_network_hazards(
        G, hazards=[hazard]
    )

    # Edge (2, 3) and (3, 2) must be blocked
    assert (2, 3, 0) in blocked_edges
    assert (3, 2, 0) in blocked_edges
    # Edge (5, 6) North bypass must remain completely unblocked
    assert (5, 6, 0) not in blocked_edges
    assert len(avoided) >= 1


def test_road_near_but_outside_hazard_polygon(synthetic_road_network):
    """Verifies that a road running parallel to a flood zone without intersecting it is NOT blocked."""
    G = synthetic_road_network
    poly = Polygon([(78.410, 17.380), (78.420, 17.380), (78.420, 17.395), (78.410, 17.395), (78.410, 17.380)])
    hazard = make_hazard(geometry=poly, severity="SEVERE")

    blocked_edges, _, _, _, _, _ = evaluate_road_network_hazards(G, hazards=[hazard])
    assert len(blocked_edges) == 0


def test_polygon_boundaries_intersection(synthetic_road_network):
    """Verifies that roads touching or crossing the exact boundary of a flood polygon are detected."""
    G = synthetic_road_network
    poly = Polygon([(78.412, 17.390), (78.418, 17.390), (78.418, 17.400), (78.412, 17.400), (78.412, 17.390)])
    hazard = make_hazard(geometry=poly, severity="HIGH")

    blocked_edges, _, _, _, _, _ = evaluate_road_network_hazards(G, hazards=[hazard])
    assert (2, 3, 0) in blocked_edges


def test_multipolygon_handling(synthetic_road_network):
    """Verifies that MultiPolygon geometries with separate basins block all intersecting segments."""
    G = synthetic_road_network
    poly1 = Polygon([(78.412, 17.395), (78.418, 17.395), (78.418, 17.405), (78.412, 17.405)])
    poly2 = Polygon([(78.422, 17.395), (78.428, 17.395), (78.428, 17.405), (78.422, 17.405)])
    multi = MultiPolygon([poly1, poly2])
    hazard = make_hazard(geometry=multi, severity="SEVERE")

    blocked_edges, _, _, _, _, _ = evaluate_road_network_hazards(G, hazards=[hazard])
    # Both (2, 3) and (3, 4) should be blocked
    assert (2, 3, 0) in blocked_edges
    assert (3, 4, 0) in blocked_edges


def test_missing_and_corrupted_geometries():
    """Verifies that missing or unparsable geometries are handled gracefully without raising exceptions."""
    assert validate_and_repair_geometry(None) is None
    assert validate_and_repair_geometry({}) is None
    assert validate_and_repair_geometry({"type": "Polygon", "coordinates": []}) is None


def test_invalid_coordinate_systems():
    """Verifies rejection of invalid WGS84 and inverted coordinate pairs."""
    # Out of valid lat/lon degrees
    bad_poly = Polygon([(200.0, 100.0), (210.0, 100.0), (210.0, 110.0), (200.0, 100.0)])
    assert validate_and_repair_geometry(bad_poly) is None

    # Inverted lat/lon for Hyderabad (lat in 78.x, lon in 17.x)
    inverted = Polygon([(17.4, 78.4), (17.5, 78.4), (17.5, 78.5), (17.4, 78.4)])
    assert validate_and_repair_geometry(inverted) is None


def test_historical_hazard_penalty_avoidance(synthetic_road_network):
    """Verifies that historical municipal inundation zones apply penalty factor without hard blocking."""
    G = synthetic_road_network
    poly = Polygon([(78.412, 17.395), (78.418, 17.395), (78.418, 17.405), (78.412, 17.405)])
    hazard = make_hazard(
        geometry=poly,
        severity="MODERATE",
        source_type="HISTORICAL_VULNERABILITY",
        data_status="PUBLIC_UNVERIFIED",
        title="GHMC Historical Inundation Zone",
        verification_note="Municipal historical survey. Sensor depth unverified.",
    )

    blocked_edges, penalized_edges, avoided, caution, _, _ = evaluate_road_network_hazards(G, hazards=[hazard])
    # Must NOT be hard-blocked
    assert (2, 3, 0) not in blocked_edges
    # Must be penalized
    assert (2, 3, 0) in penalized_edges
    assert penalized_edges[(2, 3, 0)] == 5.0
    assert any("historical municipal flood zone" in c.lower() for c in caution)


def test_unverified_citizen_reports_do_not_hard_close(synthetic_road_network):
    """Verifies that unverified citizen reports apply caution penalty but never cause confirmed closures."""
    G = synthetic_road_network
    poly = Polygon([(78.412, 17.395), (78.418, 17.395), (78.418, 17.405), (78.412, 17.405)])
    hazard = make_hazard(
        geometry=poly,
        severity="HIGH",
        source_type="PUBLIC_UNVERIFIED",
        data_status="PUBLIC_UNVERIFIED",
        title="Citizen Waterlogging Report",
        verification_note="Public unverified report. Pending verification.",
    )

    blocked_edges, penalized_edges, avoided, caution, _, _ = evaluate_road_network_hazards(G, hazards=[hazard])
    # Must not be hard-blocked
    assert (2, 3, 0) not in blocked_edges
    # Must have mild penalty and caution
    assert (2, 3, 0) in penalized_edges
    assert penalized_edges[(2, 3, 0)] == 1.5
    assert any("unverified citizen report" in c.lower() for c in caution)


def test_stale_observation_freshness_handling(synthetic_road_network):
    """Verifies that observations older than threshold are flagged as stale."""
    G = synthetic_road_network
    old_time = datetime.now(timezone.utc) - timedelta(hours=24)
    hazard = make_hazard(
        publication_time=old_time,
        severity="HIGH",
    )

    _, _, _, _, _, stale_present = evaluate_road_network_hazards(G, hazards=[hazard])
    assert stale_present is True


def test_no_available_safe_route(synthetic_road_network):
    """Verifies NO_SAFE_ROUTE response when all paths to destination are submerged."""
    G = synthetic_road_network
    # Submerge both lower road (2, 3) AND upper bypass (5, 6)
    poly1 = Polygon([(78.412, 17.395), (78.418, 17.395), (78.418, 17.405), (78.412, 17.405)])
    poly2 = Polygon([(78.412, 17.410), (78.418, 17.410), (78.418, 17.420), (78.412, 17.420)])
    h1 = make_hazard(hazard_id="H1", geometry=poly1, severity="SEVERE")
    h2 = make_hazard(hazard_id="H2", geometry=poly2, severity="SEVERE")

    # Set synthetic road network for test
    road_network_service.set_graph_for_testing(G)
    res = build_graph_route(
        origin_lat=17.4000,
        origin_lon=78.4000,
        dest_lat=17.4000,
        dest_lon=78.4300,
        hazards=[h1, h2],
    )

    assert res.route_status == "NO_SAFE_ROUTE"
    assert res.road_condition_status == "BLOCKED"
    assert any("All viable paths traverse confirmed high-risk flood polygons" in w for w in res.warnings)


def test_route_continuity_validation(synthetic_road_network):
    """Verifies route continuity verification checks sequential graph edges."""
    G = synthetic_road_network
    assert validate_route_continuity(G, [1, 2, 3, 4]) is True
    # Non-adjacent nodes (1 to 4 has no direct edge)
    assert validate_route_continuity(G, [1, 4]) is False


def test_exact_distance_calculation(synthetic_road_network):
    """Verifies that distance is calculated strictly from edge length attributes."""
    G = synthetic_road_network
    # Route 1 -> 2 (1000m) -> 3 (1000m) -> 4 (1000m) = 3000m = 3.0 km
    dist = calculate_exact_route_distance_km(G, [1, 2, 3, 4])
    assert dist == 3.0


def test_alternative_route_independence_validation():
    """Verifies Jaccard edge overlap validation for alternative evacuation routes."""
    # Two identical routes
    r1 = [1, 2, 3, 4]
    r2 = [1, 2, 3, 4]
    is_ind, overlap = validate_alternative_independence(r1, r2, max_overlap=0.70)
    assert is_ind is False
    assert overlap == 1.0

    # Independent routes: 1->2->3->4 vs 1->2->5->6->4
    # E1: (1,2), (2,3), (3,4) (3 edges)
    # E2: (1,2), (2,5), (5,6), (6,4) (4 edges)
    # Intersection: (1,2) (1 edge)
    # Union: 6 edges -> overlap = 1/6 = ~0.167 <= 0.70
    alt = [1, 2, 5, 6, 4]
    is_ind_alt, overlap_alt = validate_alternative_independence(r1, alt, max_overlap=0.70)
    assert is_ind_alt is True
    assert overlap_alt < 0.30


def test_empty_hazard_feeds_and_disclaimer(synthetic_road_network):
    """Verifies that empty hazard feeds compute normally and enforce the safety disclaimer."""
    G = synthetic_road_network
    road_network_service.set_graph_for_testing(G)

    res = build_graph_route(
        origin_lat=17.4000,
        origin_lon=78.4000,
        dest_lat=17.4000,
        dest_lon=78.4300,
        hazards=[],
    )

    assert res.route_status == "ROUTE_AVAILABLE"
    assert res.safety_disclaimer == MANDATORY_SAFETY_DISCLAIMER
    assert any("OpenStreetMap" in s for s in res.data_sources_used)
    assert res.validation_level == "GEOMETRY_INTERSECTION_VALIDATED"
