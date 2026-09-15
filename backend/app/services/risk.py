from datetime import datetime, timezone
from app.config import settings
from app.schemas.risk import RiskLevel, RiskMapResponse, RiskZone

DEFAULT_BOUNDS = (17.35, 78.45, 17.42, 78.53)


def _polygon(west: float, south: float, east: float, north: float) -> list[list[float]]:
    return [[west, south], [east, south], [east, north], [west, north], [west, south]]


def _demo_risk(row: int, column: int) -> tuple[float, RiskLevel]:
    # Fixed demo geometry: the simulated flood source is along the southern edge.
    probability = ((2 - row) * 0.28) + (0.18 if column == 1 else 0.0)
    probability = round(min(0.91, max(0.12, probability)), 2)
    level: RiskLevel = "LOW" if probability < 0.35 else "MEDIUM" if probability <= 0.70 else "HIGH"
    return probability, level


def generate_risk_map(
    south: float = DEFAULT_BOUNDS[0],
    west: float = DEFAULT_BOUNDS[1],
    north: float = DEFAULT_BOUNDS[2],
    east: float = DEFAULT_BOUNDS[3],
) -> RiskMapResponse:
    if not south < north or not west < east:
        raise ValueError("Map bounds must be ordered south < north and west < east.")
    now = datetime.now(timezone.utc)
    zones: list[RiskZone] = []
    rows, columns = 3, 3
    latitude_step = (north - south) / rows
    longitude_step = (east - west) / columns
    source = "DEMO / SIMULATED DATA"

    for row in range(rows):
        for column in range(columns):
            cell_south = south + row * latitude_step
            cell_north = cell_south + latitude_step
            cell_west = west + column * longitude_step
            cell_east = cell_west + longitude_step
            probability, risk_level = _demo_risk(row, column)
            zones.append(RiskZone(
                id=f"demo-{row}-{column}",
                risk_level=risk_level,
                flood_probability=probability,
                polygon=_polygon(cell_west, cell_south, cell_east, cell_north),
                source=source,
                updated_at=now,
            ))
    return RiskMapResponse(disaster_type="FLOOD", bounds=[south, west, north, east], zones=zones, source=source, updated_at=now)
