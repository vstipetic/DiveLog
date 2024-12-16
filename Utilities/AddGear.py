import Utilities.ClassUtils.GearClasses as Gear
import argparse
import pickle
from pathlib import Path
from typing import Optional

def add_mask(name: str,
            output_path: str,
            number_of_dives: int = 0,
            total_dive_time: int = 0,
            description: Optional[str] = None,
            is_rental: bool = False) -> None:
    """
    Create a Mask object and save it as a pickle file
    
    Args:
        name: Name/identifier for this piece of gear
        output_path: Path where to save the pickle file
        number_of_dives: Number of dives this gear has been used on
        total_dive_time: Total time in minutes this gear has spent underwater
        description: Optional description of the gear
        is_rental: Whether this is rental gear
    """
    mask = Gear.Mask(
        name=name,
        number_of_dives=number_of_dives,
        total_dive_time=total_dive_time,
        description=description,
        is_rental=is_rental
    )
    
    output_path = Path(output_path)
    with open(output_path, 'wb') as f:
        pickle.dump(mask, f)

def add_suit(name: str,
            thickness: int,
            size: int,
            output_path: str,
            number_of_dives: int = 0,
            total_dive_time: int = 0,
            description: Optional[str] = None,
            is_rental: bool = False) -> None:
    """
    Create a Suit object and save it as a pickle file
    
    Args:
        name: Name/identifier for this piece of gear
        thickness: Thickness of the suit in mm
        size: Size of the suit
        output_path: Path where to save the pickle file
        number_of_dives: Number of dives this gear has been used on
        total_dive_time: Total time in minutes this gear has spent underwater
        description: Optional description of the gear
        is_rental: Whether this is rental gear
    """
    suit = Gear.Suit(
        name=name,
        thickness=thickness,
        size=size,
        number_of_dives=number_of_dives,
        total_dive_time=total_dive_time,
        description=description,
        is_rental=is_rental
    )
    
    output_path = Path(output_path)
    with open(output_path, 'wb') as f:
        pickle.dump(suit, f)

def add_gloves(name: str,
              thickness: int,
              size: Gear.GloveSize,
              output_path: str,
              number_of_dives: int = 0,
              total_dive_time: int = 0,
              description: Optional[str] = None,
              is_rental: bool = False) -> None:
    """
    Create a Gloves object and save it as a pickle file
    
    Args:
        name: Name/identifier for this piece of gear
        thickness: Thickness of the gloves in mm
        size: Size of the gloves (S/M/L/XL)
        output_path: Path where to save the pickle file
        number_of_dives: Number of dives this gear has been used on
        total_dive_time: Total time in minutes this gear has spent underwater
        description: Optional description of the gear
        is_rental: Whether this is rental gear
    """
    gloves = Gear.Gloves(
        name=name,
        thickness=thickness,
        size=size,
        number_of_dives=number_of_dives,
        total_dive_time=total_dive_time,
        description=description,
        is_rental=is_rental
    )
    
    output_path = Path(output_path)
    with open(output_path, 'wb') as f:
        pickle.dump(gloves, f)

def add_boots(name: str,
             thickness: int,
             size: int,
             output_path: str,
             number_of_dives: int = 0,
             total_dive_time: int = 0,
             description: Optional[str] = None,
             is_rental: bool = False) -> None:
    """
    Create a Boots object and save it as a pickle file
    
    Args:
        name: Name/identifier for this piece of gear
        thickness: Thickness of the boots in mm
        size: Size of the boots
        output_path: Path where to save the pickle file
        number_of_dives: Number of dives this gear has been used on
        total_dive_time: Total time in minutes this gear has spent underwater
        description: Optional description of the gear
        is_rental: Whether this is rental gear
    """
    boots = Gear.Boots(
        name=name,
        thickness=thickness,
        size=size,
        number_of_dives=number_of_dives,
        total_dive_time=total_dive_time,
        description=description,
        is_rental=is_rental
    )
    
    output_path = Path(output_path)
    with open(output_path, 'wb') as f:
        pickle.dump(boots, f)
