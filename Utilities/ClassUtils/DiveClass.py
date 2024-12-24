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

    """Time and date of the start of the dive"""

    end_time: datetime

    """Time and date of the end of the dive"""


@dataclass
class Location:
    name: str
    """Name of the dive spot"""

    entry: Optional[Tuple[float, float]] = None
    """GPS coordinates of the dive entry"""

    exit: Optional[Tuple[float, float]] = None
    """GPS coordinates of the dive exit"""

    description: Optional[str] = None
    """Description of the dive location"""


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
