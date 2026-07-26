from attr import dataclass
from typing import Tuple, List, Optional, Set
from datetime import datetime
from Utilities.ClassUtils import GearClasses


@dataclass
class DiveTimeline:
    depths: List[float]

    """List containing depths in meters of the dive at each timestamp"""

    n2_load: List[int]

    """List containing N2 load at a given timestamp"""

    cns_load: List[int]

    """List containing N2 load at a given timestamp"""

    temperature: List[int]

    """List containing temperature in degrees Celsius at a given timestamp"""

    timestamps: List[float]

    """List containing the number of seconds that have passed since start of the dive"""

    ndl_time: Optional[List[Optional[float]]] = None

    """Remaining no-decompression limit in seconds at each timestamp. Reaches 0
    when a decompression obligation is incurred. None when the dive computer
    recorded no NDL data at all (shallow dives), and an individual entry may be
    None for samples where it was not reported."""

    next_stop_depth: Optional[List[float]] = None

    """Decompression ceiling in meters at each timestamp: the shallowest depth
    that may be ascended to. 0 means no ceiling (no decompression obligation).
    None when the dive computer recorded no ceiling data."""

    next_stop_time: Optional[List[float]] = None

    """Required time in seconds at the current decompression stop. 0 when there
    is no obligation. None when the dive computer recorded no stop data."""

    time_to_surface: Optional[List[float]] = None

    """Total time to surface in seconds at each timestamp, including any
    required decompression stops and ascent time."""


@dataclass
class People:
    buddy: str

    """My dive buddy for this dive"""

    divemaster: Optional[str]

    """The person that lead the die"""

    group: Optional[set[str]]

    """Set of all people in the group on the dive"""


@dataclass
class DiveBasicInformation:
    duration: float

    """Duration of the dive"""

    start_time: datetime

    """Time and date of the start of the dive, in the LOCAL time of the dive
    site: the wall-clock time the diver would say they entered the water. Naive
    (no tzinfo) so it stays comparable with every other datetime in the app; add
    utc_offset_hours to recover UTC."""

    end_time: datetime

    """Time and date of the end of the dive, local like start_time"""

    utc_offset_hours: Optional[float] = None

    """Hours the local time is ahead of UTC (e.g. 2.0 for Croatia in summer,
    3.0 for Egypt in summer). None on dives imported before local time was
    recorded, whose times are still stored as UTC."""

    start_time_utc: Optional[datetime] = None

    """The same instant as start_time, standardised to UTC. Local time is what
    the diver logged and what every question about the dive means, but UTC is
    the only way to order dives from different time zones on one absolute
    timeline. Naive, like start_time. None on dives imported before this was
    recorded."""

    end_time_utc: Optional[datetime] = None

    """The same instant as end_time, standardised to UTC."""


@dataclass
class Location:
    name: str
    """Name of the dive spot"""

    entry: Optional[Tuple[float, float]] = None
    """GPS coordinates of the dive entry"""

    exit: Optional[Tuple[float, float]] = None
    """GPS coordinates of the dive exit"""

    description: Optional[str] = None
    """Free-text note for the dive (e.g. Garmin Connect's dive Note), minus any
    structured lines (like "grupa: ...") that were parsed into other fields"""

    entry_type: Optional[str] = None
    """How the dive was entered, e.g. 'Boat' or 'Shore' (from Garmin Connect)"""


@dataclass
class Gasses:
    gas: str

    """The gas used for the dive"""

    start_pressure: int

    """Gas pressure at the start of the dive"""

    end_pressure: int

    """Gas pressure at the end of the dive"""


@dataclass
class UsedGear:
    suit: GearClasses.Suit

    """Suit used for the dive"""

    weights: float

    """The amount of lead weights used in kilograms"""

    mask: Optional[GearClasses.Mask]

    """Mask used for the dive"""

    gloves: Optional[GearClasses.Gloves]

    """Gloves used for the dive"""

    boots: Optional[GearClasses.Boots]

    """Boots used for the dive"""

    bcd: Optional[GearClasses.BCD]

    """BCD used for the dive"""

    fins: Optional[GearClasses.Fins]

    """Fins used for the dive"""


@dataclass
class Dive:
    people: People

    """Dataclass containing information about people present at the dive, including the dive buddy, divemaster and the rest of the group"""

    basics: DiveBasicInformation

    """Dataclass containing basic information about the dive, such as duration, start time and end time"""

    timeline: DiveTimeline

    """Dataclass containing all timestamp attributes of a dive. Depth, N2 loading, CNS loading, temperature and the timestamps"""

    location: Location

    """Dataclass containing information about the location including the coordinates of the dive entry and exit, name of the location and a description of the location"""

    gasses: Gasses

    """Dataclass containing information about the information about gasses used in the dive. Includes the gas and starting and ending pressures in the bottle."""

    gear: UsedGear

    """Dataclass containing information about gear used in the dive."""
