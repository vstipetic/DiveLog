"""
Geometry helpers for geographic dive filtering.

Deliberately dependency-free: everything here is a few lines of trigonometry,
and the only question the dive log asks of geometry is "is this point inside
that ring", which does not justify pulling in shapely.

COORDINATE ORDER -- the one thing to get right:

* ``Dive.location.entry`` is ``(latitude, longitude)``.
* GeoJSON is ``[longitude, latitude]``.

Every function here takes and returns **(lat, lon)** tuples. Conversion to and
from GeoJSON's reversed order happens only in :func:`ring_from_geojson` and
:func:`ring_to_geojson`, so the flip lives in exactly two places.
"""

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Mean Earth radius (km), the usual spherical approximation.
EARTH_RADIUS_KM = 6371.0088

# A ring is a closed list of (lat, lon) vertices.
Ring = List[Tuple[float, float]]


# =============================================================================
# VALIDATION
# =============================================================================

def valid_coordinate(lat: float, lon: float) -> bool:
    """True if the pair is a plausible WGS84 coordinate."""
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def _require_coordinate(lat: float, lon: float, what: str) -> None:
    if not valid_coordinate(lat, lon):
        raise ValueError(
            f"{what} ({lat}, {lon}) is out of range: latitude must be -90..90 "
            f"and longitude -180..180. Remember the order is (latitude, longitude)."
        )


def close_ring(ring: Sequence[Tuple[float, float]]) -> Ring:
    """Return the ring with its first vertex repeated at the end if needed."""
    points = [(float(lat), float(lon)) for lat, lon in ring]
    if len(points) >= 1 and points[0] != points[-1]:
        points.append(points[0])
    return points


# =============================================================================
# GEOJSON CONVERSION (the only place the lat/lon order flips)
# =============================================================================

def ring_to_geojson(ring: Sequence[Tuple[float, float]]) -> Dict[str, Any]:
    """Convert a ring of (lat, lon) vertices to a GeoJSON Polygon."""
    closed = close_ring(ring)
    return {
        "type": "Polygon",
        "coordinates": [[[round(lon, 6), round(lat, 6)] for lat, lon in closed]],
    }


def ring_from_geojson(geometry: Any) -> Ring:
    """
    Extract a ring of (lat, lon) vertices from assorted GeoJSON-ish input.

    Accepts a Polygon, a Feature wrapping one, a bare coordinates array, or a
    plain list of ``[lon, lat]`` pairs -- an agent will produce any of these.
    Only the outer ring is used; holes are ignored.

    Raises:
        ValueError: If no usable ring can be found or it is degenerate.
    """
    if geometry is None:
        raise ValueError("No polygon provided.")

    # Feature -> geometry
    if isinstance(geometry, dict) and geometry.get("type") == "Feature":
        geometry = geometry.get("geometry")

    coordinates: Any
    if isinstance(geometry, dict):
        geom_type = (geometry.get("type") or "").lower()
        if geom_type and geom_type not in ("polygon", "multipolygon"):
            raise ValueError(
                f"Unsupported geometry type '{geometry.get('type')}'. "
                "Provide a Polygon."
            )
        coordinates = geometry.get("coordinates")
        if coordinates is None:
            raise ValueError("Polygon has no 'coordinates'.")
        if geom_type == "multipolygon":
            # Outer ring of the first polygon.
            coordinates = coordinates[0]
    else:
        coordinates = geometry

    # Peel nesting until we reach a list of [lon, lat] pairs.
    for _ in range(3):
        if (
            isinstance(coordinates, (list, tuple))
            and coordinates
            and isinstance(coordinates[0], (list, tuple))
            and coordinates[0]
            and isinstance(coordinates[0][0], (list, tuple))
        ):
            coordinates = coordinates[0]
        else:
            break

    if not isinstance(coordinates, (list, tuple)) or len(coordinates) < 3:
        raise ValueError(
            "A polygon needs at least 3 points, as [[lon, lat], [lon, lat], ...]."
        )

    ring: Ring = []
    for point in coordinates:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            raise ValueError(f"Bad polygon point: {point!r}. Expected [lon, lat].")
        lon, lat = float(point[0]), float(point[1])
        _require_coordinate(lat, lon, "Polygon point")
        ring.append((lat, lon))

    closed = close_ring(ring)
    if len(closed) < 4:  # 3 distinct vertices + repeated first
        raise ValueError("A polygon needs at least 3 distinct points.")
    return closed


# =============================================================================
# POINT IN POLYGON
# =============================================================================

def point_in_ring(lat: float, lon: float, ring: Sequence[Tuple[float, float]]) -> bool:
    """
    Ray-casting point-in-polygon test in lat/lon space.

    Edges are treated as straight in lat/lon (the standard GeoJSON reading),
    which is what you want for the coarse regions this is used for.

    Not antimeridian-aware: a ring that crosses +/-180 longitude must be split
    into two rings by the caller. No such region is currently in use.
    """
    inside = False
    count = len(ring)
    if count < 3:
        return False

    j = count - 1
    for i in range(count):
        lat_i, lon_i = ring[i]
        lat_j, lon_j = ring[j]

        # Does the edge straddle the test latitude, and if so is the crossing
        # longitude to the east of the point?
        if (lat_i > lat) != (lat_j > lat):
            delta_lat = lat_j - lat_i
            if delta_lat != 0:
                crossing_lon = lon_i + (lat - lat_i) / delta_lat * (lon_j - lon_i)
                if lon < crossing_lon:
                    inside = not inside
        j = i

    return inside


def ring_bounds(ring: Sequence[Tuple[float, float]]) -> Tuple[float, float, float, float]:
    """Bounding box of a ring as (min_lat, min_lon, max_lat, max_lon)."""
    lats = [lat for lat, _ in ring]
    lons = [lon for _, lon in ring]
    return min(lats), min(lons), max(lats), max(lons)


# =============================================================================
# DISTANCE
# =============================================================================

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points, in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


# =============================================================================
# REGION BUILDERS
# =============================================================================

def circle_ring(
    center_lat: float,
    center_lon: float,
    radius_km: float,
    vertices: int = 32,
) -> Ring:
    """
    Approximate a circle of ``radius_km`` around a point as a polygon ring.

    Vertices are placed with the spherical destination-point formula, so the
    shape stays correct at high latitudes and for large radii, where a flat
    "degrees per km" approximation visibly distorts.

    The polygon is inscribed in the true circle, so it very slightly
    under-covers between vertices: the worst-case shortfall is
    ``radius * (1 - cos(pi / vertices))``, which at the default 32 vertices is
    0.5% -- 24 m on a 5 km radius.

    Args:
        center_lat: Centre latitude in degrees
        center_lon: Centre longitude in degrees
        radius_km: Radius in kilometres, must be positive
        vertices: Number of polygon vertices (8-360)

    Returns:
        Closed ring of (lat, lon) vertices

    Raises:
        ValueError: On an invalid centre, radius or vertex count
    """
    _require_coordinate(center_lat, center_lon, "Circle centre")

    if radius_km <= 0:
        raise ValueError(f"radius_km must be greater than 0, got {radius_km}.")
    if radius_km > 20015:  # half the Earth's circumference
        raise ValueError(
            f"radius_km {radius_km} covers more than half the planet; "
            "use a region polygon instead."
        )
    if not 8 <= vertices <= 360:
        raise ValueError(f"vertices must be between 8 and 360, got {vertices}.")

    phi1 = math.radians(center_lat)
    lambda1 = math.radians(center_lon)
    angular = radius_km / EARTH_RADIUS_KM

    ring: Ring = []
    for i in range(vertices):
        bearing = 2 * math.pi * i / vertices

        phi2 = math.asin(
            math.sin(phi1) * math.cos(angular)
            + math.cos(phi1) * math.sin(angular) * math.cos(bearing)
        )
        lambda2 = lambda1 + math.atan2(
            math.sin(bearing) * math.sin(angular) * math.cos(phi1),
            math.cos(angular) - math.sin(phi1) * math.sin(phi2),
        )

        lat = math.degrees(phi2)
        # Wrap longitude back into -180..180.
        lon = (math.degrees(lambda2) + 540) % 360 - 180
        ring.append((lat, lon))

    return close_ring(ring)


def bbox_ring(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
) -> Ring:
    """
    Build a rectangular ring from a bounding box.

    Args:
        min_lat, min_lon, max_lat, max_lon: Box corners in degrees

    Returns:
        Closed ring of (lat, lon) vertices

    Raises:
        ValueError: If the corners are out of range or inverted
    """
    _require_coordinate(min_lat, min_lon, "Bounding box minimum")
    _require_coordinate(max_lat, max_lon, "Bounding box maximum")

    if min_lat >= max_lat:
        raise ValueError(f"min_lat ({min_lat}) must be less than max_lat ({max_lat}).")
    if min_lon >= max_lon:
        raise ValueError(
            f"min_lon ({min_lon}) must be less than max_lon ({max_lon}). "
            "Boxes crossing the antimeridian are not supported."
        )

    return close_ring([
        (min_lat, min_lon),
        (min_lat, max_lon),
        (max_lat, max_lon),
        (max_lat, min_lon),
    ])


def describe_ring(ring: Sequence[Tuple[float, float]]) -> str:
    """Compact human-readable summary of a ring, for tool output."""
    min_lat, min_lon, max_lat, max_lon = ring_bounds(ring)
    # The closing vertex repeats the first, so it is not a distinct point.
    distinct = len(ring) - 1
    return (
        f"{distinct} vertices, bounds lat {min_lat:.4f}..{max_lat:.4f}, "
        f"lon {min_lon:.4f}..{max_lon:.4f}"
    )
