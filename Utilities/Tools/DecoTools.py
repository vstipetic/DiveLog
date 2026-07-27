"""
Decompression filtering tools.

The decompression series were parsed into DiveTimeline, but nothing exposed
them to the agent, so questions like "how many dives did I enter deco on" had
no tool to reach for and the model would fall back to re-deriving NDL from
dive tables -- an estimate, when the dive computer's own answer is on disk.

Two tools, matching the two questions people actually ask:

* ``filter_dives_by_deco_status`` - did the dive incur an obligation, and how
  long a stop did it require.
* ``filter_dives_by_ndl`` - how close did the dive get to the limit, for the
  "within 5 minutes of deco" question, which includes dives that never went
  into deco at all.

Both report dives whose computer recorded no decompression data separately,
rather than counting them as "no deco" -- shallow dives legitimately record no
NDL, and calling those a clean profile would be a fabrication.
"""

from typing import List, Optional, Type

from pydantic import BaseModel, ConfigDict, Field

from Utilities.LLMProvider import Tool

from Utilities.ClassUtils.DiveClass import Dive
from Utilities.DecoFunctions import (
    describe_deco,
    dive_entered_deco,
    has_ndl_data,
    max_ceiling_meters,
    max_stop_seconds,
    min_ndl_seconds,
)
from Utilities.Schemas.ToolOutputs import DiveSummary
from Utilities.Tools.ToolState import ToolState


def _summary_lines(matched: List[Dive], limit: int = 5) -> List[str]:
    """Per-dive lines with the decompression detail spelled out."""
    lines = ["\nDive summaries:"]
    for dive in matched[:limit]:
        summary = DiveSummary.from_dive(dive, "dive")
        lines.append(
            f"  - {summary.date.strftime('%Y-%m-%d')}: "
            f"{summary.max_depth_meters:.1f}m at {summary.location} "
            f"-- {describe_deco(dive)}"
        )
    if len(matched) > limit:
        lines.append(f"  ... and {len(matched) - limit} more dives")
    return lines


# =============================================================================
# DECO STATUS
# =============================================================================

class FilterDivesByDecoStatusInput(BaseModel):
    """Input schema for filtering by decompression obligation."""

    entered_deco: bool = Field(
        True,
        description=(
            "True (default) keeps dives that incurred a decompression "
            "obligation. False keeps dives that stayed within the "
            "no-decompression limit."
        )
    )
    min_stop_minutes: Optional[float] = Field(
        None,
        description=(
            "Only keep dives whose required decompression stop reached at "
            "least this many minutes, e.g. 2 for 'at least 2 minutes of deco'. "
            "Implies entered_deco=true."
        )
    )


class FilterDivesByDecoStatusTool(Tool):
    """Filter dives by whether they incurred a decompression obligation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "filter_dives_by_deco_status"
    description: str = (
        "Filter dives by decompression obligation, using the dive computer's own "
        "recorded ceiling and stop time -- never estimate this from dive tables. "
        "entered_deco=true (default) finds dives that went into deco; "
        "entered_deco=false finds dives that stayed within the no-decompression "
        "limit. Add min_stop_minutes to require a stop of at least that length, "
        "e.g. min_stop_minutes=2 for 'dives with at least 2 minutes of deco'. "
        "For 'how close did I get to deco without entering it', use "
        "filter_dives_by_ndl instead. "
        "The filtered results are automatically available for subsequent statistics."
    )
    args_schema: Type[BaseModel] = FilterDivesByDecoStatusInput

    dives: List[Dive] = Field(default_factory=list)

    def run(
        self,
        entered_deco: bool = True,
        min_stop_minutes: Optional[float] = None,
    ) -> str:
        """Filter by decompression status and return a formatted result."""
        if min_stop_minutes is not None and min_stop_minutes < 0:
            return "min_stop_minutes cannot be negative."

        matched: List[Dive] = []
        unknown: List[Dive] = []

        for dive in self.dives:
            status = dive_entered_deco(dive)
            if status is None:
                unknown.append(dive)
                continue

            if status != entered_deco:
                continue

            if min_stop_minutes is not None:
                stop = max_stop_seconds(dive)
                if stop is None or stop < min_stop_minutes * 60:
                    continue

            matched.append(dive)

        if min_stop_minutes is not None:
            desc = f"deco stop >= {min_stop_minutes:g} min"
        else:
            desc = "entered deco" if entered_deco else "stayed within NDL"
        ToolState.set_filtered_dives(matched, desc)

        known = len(self.dives) - len(unknown)
        lines: List[str] = []

        if not matched:
            lines.append(f"No dives found where the dive {desc}.")
        else:
            lines.append(f"Found {len(matched)} dives where the dive {desc}:")

        lines.append(f"- Checked {known} of {len(self.dives)} dives")
        if unknown:
            lines.append(
                f"- {len(unknown)} dives recorded no decompression data and were "
                "not counted either way"
            )

        if matched:
            stops = [s for s in (max_stop_seconds(d) for d in matched) if s]
            if stops:
                lines.append(
                    f"- Longest required stop: {max(stops) / 60:.1f} min"
                )
            ceilings = [c for c in (max_ceiling_meters(d) for d in matched) if c]
            if ceilings:
                lines.append(f"- Deepest ceiling: {max(ceilings):.0f}m")
            lines.extend(_summary_lines(matched))

        return "\n".join(lines)


# =============================================================================
# NDL PROXIMITY
# =============================================================================

class FilterDivesByNDLInput(BaseModel):
    """Input schema for filtering by how close a dive came to the NDL."""

    max_ndl_minutes: float = Field(
        description=(
            "Keep dives whose remaining no-decompression limit fell to this "
            "many minutes or less. Use 5 for 'dives where I got within 5 "
            "minutes of deco'; use 0 for dives that actually ran out of "
            "no-stop time. This includes dives that entered deco, since their "
            "NDL reached 0."
        )
    )


class FilterDivesByNDLTool(Tool):
    """Filter dives by the lowest no-decompression limit they reached."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "filter_dives_by_ndl"
    description: str = (
        "Filter dives by how close they came to the no-decompression limit, "
        "using the NDL the dive computer actually recorded -- never estimate it "
        "from dive tables. max_ndl_minutes=5 answers 'on how many dives did I "
        "hit 5 minutes to decompression'. Note this includes dives that went on "
        "to enter deco, because their NDL passed through that value on the way "
        "to 0; use filter_dives_by_deco_status to separate those. "
        "Shallow dives where the computer recorded no NDL are reported "
        "separately and not counted. "
        "The filtered results are automatically available for subsequent statistics."
    )
    args_schema: Type[BaseModel] = FilterDivesByNDLInput

    dives: List[Dive] = Field(default_factory=list)

    def run(self, max_ndl_minutes: float) -> str:
        """Filter by minimum NDL reached and return a formatted result."""
        if max_ndl_minutes < 0:
            return "max_ndl_minutes cannot be negative."

        threshold = max_ndl_minutes * 60
        matched: List[Dive] = []
        unknown: List[Dive] = []

        for dive in self.dives:
            if not has_ndl_data(dive):
                unknown.append(dive)
                continue
            if min_ndl_seconds(dive) <= threshold:
                matched.append(dive)

        desc = f"NDL fell to {max_ndl_minutes:g} min or less"
        ToolState.set_filtered_dives(matched, desc)

        known = len(self.dives) - len(unknown)
        lines: List[str] = []

        if not matched:
            lines.append(f"No dives found where the {desc}.")
        else:
            lines.append(f"Found {len(matched)} dives where the {desc}:")

        lines.append(f"- Checked {known} of {len(self.dives)} dives with NDL data")
        if unknown:
            lines.append(
                f"- {len(unknown)} dives recorded no NDL (typically too shallow "
                "for the computer to track it) and were not counted"
            )

        if matched:
            entered = sum(1 for d in matched if dive_entered_deco(d))
            lines.append(
                f"- Of these, {entered} went on to enter deco and "
                f"{len(matched) - entered} stayed within the limit"
            )
            lines.extend(_summary_lines(matched))

        return "\n".join(lines)
