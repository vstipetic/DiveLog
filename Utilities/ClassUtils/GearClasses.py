from attr import dataclass
from typing import Optional
from enum import Enum

class GloveSize(Enum):
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"
    
class GearPieces(Enum):
    Mask = "Mask"
    Suit = "Suit"
    Gloves = "Gloves"
    Boots = "Boots"
    BCD = "BCD"
    Fins = "Fins"

@dataclass
class Gear:
    total_dive_time: int

    """Total time this piece of gear has spent under water"""

    number_of_dives: int

    """Total number of dives this piece of gear has been on"""

    description: Optional[str]

    """A short description of this specific piece of gear"""

    is_rental: bool

    """Boolean flag to mark rental equipment. Statistics will not be calculated for rental gear, 
        but some propertis of the gear used on a specific dive are important for other trends, such 
        as suit thickness"""
    
    name : str

    """name of the piece of gear. This is the unique identifier that you will use to refer to this specific piece of gear"""


@dataclass
class Mask(Gear):
    pass


@dataclass
class Suit(Gear):
    thickness: int

    """Thickness of the suit in mm"""

    size: int

    """Size of the suit"""


@dataclass
class Gloves(Gear):
    thickness: int

    """Thickness of the gloves in mm"""

    size: GloveSize

    """Size of the gloves, S, M, L or XL"""


@dataclass
class Boots(Gear):
    thickness: int

    """Thickness of the suit in mm"""

    size: int

    """Size of the boots"""

@dataclass
class BCD(Gear):
    """To be implemented"""
    pass

@dataclass
class Fins(Gear):
    """To be implemented"""
    pass
