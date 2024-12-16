from Utilities.ClassUtils.DiveClass import Dive
from Utilities.Parsers.GarminDiveParser import parse_garmin_dive
import pickle
from typing import Optional, Dict, Any
from pathlib import Path

def add_dive(fit_file_path: str, 
            output_path: str,
            location_name: str = '',
            location_description: str = '',
            coordinates: Optional[tuple[float, float]] = None,
            buddy: str = '',
            divemaster: Optional[str] = None,
            group: Optional[set[str]] = None,
            gas: str = '',
            start_pressure: int = 0,
            end_pressure: int = 0,
            suit: Optional[str] = None,
            weights: float = 0.0,
            mask: Optional[str] = None, 
            gloves: Optional[str] = None,
            boots: Optional[str] = None,
            bcd: Optional[str] = None,
            fins: Optional[str] = None) -> Dive:
    """
    Create a Dive object from a .fit file and metadata, and save it as a pickle file
    
    Args:
        fit_file_path: Path to the .fit file containing dive data
        output_path: Path where to save the pickle file
        location_name: Name of the dive location
        location_description: Description of the dive location
        coordinates: GPS coordinates of the dive location
        buddy: Name of dive buddy
        divemaster: Name of divemaster
        group: Set of names of other people in dive group
        gas: Gas mixture used
        start_pressure: Starting gas pressure
        end_pressure: Ending gas pressure
        suit: Path to pickle file containing suit gear object
        weights: Weight in kg used
        mask: Path to pickle file containing mask gear object
        gloves: Path to pickle file containing gloves gear object
        boots: Path to pickle file containing boots gear object
        bcd: Path to pickle file containing BCD gear object
        fins: Path to pickle file containing fins gear object
        
    Returns:
        Dive object containing all dive information
    """
    metadata: Dict[str, Any] = {
        'location_name': location_name,
        'location_description': location_description,
        'coordinates': coordinates,
        'buddy': buddy,
        'divemaster': divemaster,
        'group': group or set(),
        'gas': gas,
        'start_pressure': start_pressure,
        'end_pressure': end_pressure,
        'weights': weights
    }
    
    # Load gear objects if paths provided
    if suit:
        with open(suit, 'rb') as f:
            metadata['suit'] = pickle.load(f)
    if mask:
        with open(mask, 'rb') as f:
            metadata['mask'] = pickle.load(f)
    if gloves:
        with open(gloves, 'rb') as f:
            metadata['gloves'] = pickle.load(f)
    if boots:
        with open(boots, 'rb') as f:
            metadata['boots'] = pickle.load(f)
    if bcd:
        with open(bcd, 'rb') as f:
            metadata['bcd'] = pickle.load(f)
    if fins:
        with open(fins, 'rb') as f:
            metadata['fins'] = pickle.load(f)
            
    dive = parse_garmin_dive(fit_file_path, metadata)
    
    # Save dive object
    output_path = Path(output_path)
    with open(output_path, 'wb') as f:
        pickle.dump(dive, f)
        
    return dive