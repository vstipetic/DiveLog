"""
Geographic tools: build a region, then filter dives against it.

Two tools, deliberately split:

* ``build_region_polygon`` turns a primitive -- a radius around a point, or a
  bounding box -- into a GeoJSON polygon. Exact and deterministic, so the
  common "within N km of X" question never depends on the model recalling a
  coastline.
* ``filter_dives_by_region`` takes any polygon and keeps the dives inside it
  (or outside it). The polygon can come from the builder or straight from the
  model, which is what keeps open-ended regions like "the Mediterranean"
  answerable.

Dives with no GPS fix are always reported separately rather than silently
dropped: a third of the current log has no coordinates, so a geographic count
that quietly ignores them would badly understate reality.
"""

import json
from typing import Any, List, Optional, Tuple, Type

from pydantic import BaseModel, ConfigDict, Field

from Utilities.LLMProvider import Tool

from Utilities.ClassUtils.DiveClass import Dive
from Utilities.Geo import (
    bbox_ring,
    circle_ring,
    describe_ring,
    point_in_ring,
    ring_from_geojson,
    ring_to_geojson,
)
from Utilities.Schemas.ToolOutputs import DiveSummary
from Utilities.Tools.GeoState import GeoRegionState
from Utilities.Tools.ToolState import ToolState


def _dive_position(dive: Dive) -> Optional[Tuple[float, float]]:
    """A dive's (lat, lon), preferring the entry fix and falling back to exit."""
    return dive.location.entry or dive.location.exit


# =============================================================================
# REGION BUILDER
# =============================================================================

class BuildRegionPolygonInput(BaseModel):
    """Input schema for building a region polygon."""

    center_lat: Optional[float] = Field(
        None,
        description=(
            "Latitude of the circle centre in degrees. Provide with center_lon "
            "and radius_km, OR use place_name instead."
        )
    )
    center_lon: Optional[float] = Field(
        None,
        description="Longitude of the circle centre in degrees."
    )
    radius_km: Optional[float] = Field(
        None,
        description="Radius around the centre in kilometres, e.g. 5 for 'within 5km'."
    )
    place_name: Optional[str] = Field(
        None,
        description=(
            "Name of a dive site already in the log, used as the circle centre "
            "instead of explicit coordinates (case-insensitive partial match). "
            "Use this when the place is one the user has dived; supply "
            "center_lat/center_lon yourself for anywhere else."
        )
    )
    min_lat: Optional[float] = Field(
        None,
        description="Bounding-box mode: southern edge. Provide all four min/max values."
    )
    min_lon: Optional[float] = Field(None, description="Bounding-box mode: western edge.")
    max_lat: Optional[float] = Field(None, description="Bounding-box mode: northern edge.")
    max_lon: Optional[float] = Field(None, description="Bounding-box mode: eastern edge.")
    vertices: int = Field(
        32,
        description="Number of vertices for a circle (8-360). 32 is plenty; raise it only for very large radii."
    )


class BuildRegionPolygonTool(Tool):
    """Build a GeoJSON region polygon from a radius-around-a-point or a bounding box."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "build_region_polygon"
    description: str = (
        "Build a GeoJSON polygon describing a geographic region, then pass it to "
        "filter_dives_by_region. Two modes: "
        "(1) CIRCLE - give radius_km plus either center_lat/center_lon or a "
        "place_name that appears in the dive log. Use this for 'within 5km of Vis', "
        "'near Karlobag', 'around Dahab'. "
        "(2) BOUNDING BOX - give min_lat, min_lon, max_lat, max_lon for a "
        "rectangular area. "
        "This computes the geometry exactly, so prefer it over writing circle "
        "coordinates yourself. For irregular named regions (a sea, a country, a "
        "continent) skip this tool and pass your own polygon straight to "
        "filter_dives_by_region."
    )
    args_schema: Type[BaseModel] = BuildRegionPolygonInput

    dives: List[Dive] = Field(default_factory=list)

    def run(
        self,
        center_lat: Optional[float] = None,
        center_lon: Optional[float] = None,
        radius_km: Optional[float] = None,
        place_name: Optional[str] = None,
        min_lat: Optional[float] = None,
        min_lon: Optional[float] = None,
        max_lat: Optional[float] = None,
        max_lon: Optional[float] = None,
        vertices: int = 32,
    ) -> str:
        """Build the region and return it as GeoJSON."""
        bbox_values = (min_lat, min_lon, max_lat, max_lon)
        wants_bbox = any(v is not None for v in bbox_values)
        wants_circle = radius_km is not None or place_name is not None

        if wants_bbox and wants_circle:
            return (
                "Provide either a circle (radius_km with a centre) or a bounding "
                "box (min_lat/min_lon/max_lat/max_lon), not both."
            )

        try:
            if wants_bbox:
                if any(v is None for v in bbox_values):
                    return (
                        "Bounding-box mode needs all four of min_lat, min_lon, "
                        "max_lat and max_lon."
                    )
                ring = bbox_ring(min_lat, min_lon, max_lat, max_lon)
                label = (
                    f"box lat {min_lat}..{max_lat}, lon {min_lon}..{max_lon}"
                )
            elif wants_circle:
                if radius_km is None:
                    return "Circle mode needs radius_km."

                origin = ""
                if place_name:
                    resolved = self._resolve_place(place_name)
                    if resolved is None:
                        return (
                            f"No dive site matching '{place_name}' has coordinates in "
                            "the log. Supply center_lat and center_lon instead."
                        )
                    center_lat, center_lon, matched, dive_count = resolved
                    origin = (
                        f" centred on '{matched}' "
                        f"({center_lat:.5f}, {center_lon:.5f}), "
                        f"averaged from {dive_count} logged dive(s)"
                    )
                elif center_lat is None or center_lon is None:
                    return (
                        "Circle mode needs either place_name, or both center_lat "
                        "and center_lon."
                    )
                else:
                    origin = f" centred on ({center_lat:.5f}, {center_lon:.5f})"

                ring = circle_ring(center_lat, center_lon, radius_km, vertices)
                label = f"{radius_km}km radius{origin}"
            else:
                return (
                    "Nothing to build. Give radius_km with a centre (center_lat/"
                    "center_lon or place_name) for a circle, or min_lat/min_lon/"
                    "max_lat/max_lon for a bounding box."
                )
        except ValueError as e:
            return f"Could not build the region: {e}"

        GeoRegionState.set_region(ring, label)

        geojson = ring_to_geojson(ring)
        return (
            f"Region built: {label}\n"
            f"Geometry: {describe_ring(ring)}\n"
            "Stored as the current region -- call filter_dives_by_region with no "
            "polygon argument to use it.\n\n"
            f"GeoJSON:\n{json.dumps(geojson)}"
        )

    def _resolve_place(
        self, place_name: str
    ) -> Optional[Tuple[float, float, str, int]]:
        """
        Find a dive site by name in the log and average its coordinates.

        Returns (lat, lon, matched_names, dive_count), or None when nothing with
        coordinates matches.
        """
        needle = place_name.strip().lower()
        matches = [
            d for d in self.dives
            if d.location.name
            and needle in d.location.name.lower()
            and _dive_position(d)
        ]
        if not matches:
            return None

        positions = [_dive_position(d) for d in matches]
        avg_lat = sum(p[0] for p in positions) / len(positions)
        avg_lon = sum(p[1] for p in positions) / len(positions)

        names = sorted({d.location.name for d in matches})
        matched = names[0] if len(names) == 1 else f"{len(names)} sites: {', '.join(names[:3])}"
        return avg_lat, avg_lon, matched, len(matches)


# =============================================================================
# REGION FILTER
# =============================================================================

class FilterDivesByRegionInput(BaseModel):
    """Input schema for filtering dives against a region polygon."""

    polygon: Optional[str] = Field(
        None,
        description=(
            "The region as GeoJSON, given as a JSON string. Either a full Polygon "
            '(\'{"type":"Polygon","coordinates":[[[lon,lat],...]]}\') or just the '
            "ring (\'[[lon,lat],[lon,lat],...]\'). NOTE the GeoJSON order is "
            "[longitude, latitude]. Omit this to reuse the region from the most "
            "recent build_region_polygon call."
        )
    )
    inside: bool = Field(
        True,
        description=(
            "True (default) keeps dives inside the region; False keeps dives "
            "outside it, for questions like 'dives outside Europe'."
        )
    )
    region_name: Optional[str] = Field(
        None,
        description="Optional label for the region, used in the output, e.g. 'Croatia'."
    )


class FilterDivesByRegionTool(Tool):
    """Filter dives to those inside (or outside) a region polygon."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "filter_dives_by_region"
    description: str = (
        "Filter dives by geographic region, keeping those inside the given polygon "
        "or (with inside=false) those outside it. Use inside=false for questions "
        "like 'dives outside Europe'. "
        "The polygon is GeoJSON in [longitude, latitude] order; omit it to reuse "
        "the region from the last build_region_polygon call. "
        "For a radius or a box, call build_region_polygon first rather than writing "
        "the coordinates yourself. For a named region (a sea, country or continent) "
        "supply your own approximate polygon here -- a dozen points tracing the "
        "outline is enough. "
        "Dives with no GPS fix are excluded from both sides and reported separately. "
        "Results are available to subsequent statistics calculations."
    )
    args_schema: Type[BaseModel] = FilterDivesByRegionInput

    dives: List[Dive] = Field(default_factory=list)

    def run(
        self,
        polygon: Optional[str] = None,
        inside: bool = True,
        region_name: Optional[str] = None,
    ) -> str:
        """Filter dives against the region and return a formatted result."""
        ring, source = self._resolve_ring(polygon)
        if ring is None:
            return source  # source carries the error message

        label = region_name or GeoRegionState.get_description() or "the region"
        direction = "inside" if inside else "outside"

        matched: List[Dive] = []
        no_position: List[Dive] = []

        for dive in self.dives:
            position = _dive_position(dive)
            if position is None:
                no_position.append(dive)
                continue
            lat, lon = position
            if point_in_ring(lat, lon, ring) == inside:
                matched.append(dive)

        ToolState.set_filtered_dives(matched, f"{direction} {label}")

        lines = []
        if not matched:
            lines.append(f"No dives found {direction} {label}.")
        else:
            lines.append(f"Found {len(matched)} dives {direction} {label}:")

        located = len(self.dives) - len(no_position)
        lines.append(
            f"- Checked {located} of {len(self.dives)} dives "
            f"({source})"
        )
        if no_position:
            lines.append(
                f"- {len(no_position)} dives have no GPS coordinates and were not "
                "considered on either side"
            )

        if matched:
            summaries = [
                DiveSummary.from_dive(d, f"dive_{i}") for i, d in enumerate(matched)
            ]
            dates = [s.date for s in summaries]
            lines.append(
                f"- Date range: {min(dates).strftime('%Y-%m-%d')} to "
                f"{max(dates).strftime('%Y-%m-%d')}"
            )

            sites = sorted({s.location for s in summaries if s.location})
            if sites:
                shown = ", ".join(sites[:6])
                more = f" (+{len(sites) - 6} more)" if len(sites) > 6 else ""
                lines.append(f"- Sites: {shown}{more}")

            lines.append("\nDive summaries:")
            for summary, dive in list(zip(summaries, matched))[:5]:
                lat, lon = _dive_position(dive)
                lines.append(
                    f"  - {summary.date.strftime('%Y-%m-%d')}: "
                    f"{summary.max_depth_meters:.1f}m at {summary.location} "
                    f"({lat:.4f}, {lon:.4f})"
                )
            if len(summaries) > 5:
                lines.append(f"  ... and {len(summaries) - 5} more dives")

        return "\n".join(lines)

    def _resolve_ring(self, polygon: Optional[str]) -> Tuple[Optional[List], str]:
        """
        Get the ring to test against, from the argument or from GeoRegionState.

        Returns (ring, source_description); on failure returns (None, message).
        """
        if polygon is None or (isinstance(polygon, str) and not polygon.strip()):
            stored = GeoRegionState.get_region()
            if stored is None:
                return None, (
                    "No polygon given and no region has been built yet. Either "
                    "call build_region_polygon first, or pass a GeoJSON polygon "
                    "in the polygon argument."
                )
            return stored, f"region from build_region_polygon: {describe_ring(stored)}"

        geometry: Any = polygon
        if isinstance(polygon, str):
            try:
                geometry = json.loads(polygon)
            except json.JSONDecodeError as e:
                return None, (
                    f"Could not parse the polygon as JSON: {e}. Provide GeoJSON "
                    'like {"type":"Polygon","coordinates":[[[lon,lat],...]]}.'
                )

        try:
            ring = ring_from_geojson(geometry)
        except (ValueError, TypeError) as e:
            return None, f"Invalid polygon: {e}"

        GeoRegionState.set_region(ring, "supplied polygon")
        return ring, f"supplied polygon: {describe_ring(ring)}"
