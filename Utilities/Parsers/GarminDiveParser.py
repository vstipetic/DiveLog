from fitparse import FitFile
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from Utilities.ClassUtils.DiveClass import DiveTimeline, DiveBasicInformation, Dive, People, Gasses, Location, UsedGear
from datetime import datetime, timedelta

def semicircles_to_degrees(semicircles: float) -> float:
    """Convert semicircles to degrees"""
    return round(semicircles * (180.0 / 2**31), 6)

def parse_timeline(fit_file: FitFile) -> tuple[DiveTimeline, datetime]:
    """Parse the timeline data from the fit file"""
    depths: List[float] = []
    temperatures: List[int] = []
    n2_loads: List[int] = []
    cns_loads: List[int] = []
    timestamps: List[float] = []
    
    start_time: Optional[datetime] = None
    
    for record in fit_file.get_messages('record'):
        values = record.get_values()
        
        if start_time is None:
            start_time = values.get('timestamp')
        
        depths.append(values.get('depth', 0.0))  # Depth is already in meters
        temperatures.append(values.get('temperature', 0))
        n2_loads.append(values.get('tissue_n2_load', 0))
        cns_loads.append(values.get('cns_load', 0))
        
        if start_time:
            elapsed = (values.get('timestamp') - start_time).total_seconds()
            timestamps.append(elapsed)

    timeline = DiveTimeline(
        depths=depths,
        temperature=temperatures,
        n2_load=n2_loads,
        cns_load=cns_loads,
        timestamps=timestamps
    )
    
    return timeline, start_time if start_time else datetime.now()

def parse_basic_info(timeline: DiveTimeline, start_time: datetime) -> DiveBasicInformation:
    """Create the basic dive information"""
    duration = timeline.timestamps[-1] if timeline.timestamps else 0.0
    end_time = start_time + timedelta(seconds=duration)
    return DiveBasicInformation(
        duration=duration,
        start_time=start_time,
        end_time=end_time
    )

def parse_people(metadata: Dict[str, Any]) -> People:
    """Parse the people information from metadata"""
    return People(
        buddy=metadata.get('buddy', ''),
        divemaster=metadata.get('divemaster'),
        group=set(metadata.get('group', []))
    )

def parse_location(fit_file: FitFile, metadata: Dict[str, Any]) -> Location:
    """
    Extract location information from the fit file and metadata
    
    Args:
        fit_file: FitFile object containing the dive data
        metadata: Dictionary containing additional location information
        
    Returns:
        Location object with name, description, and entry coordinates if available
    """
    entry_coords = None
    
    # Get entry coordinates from session data
    for session in fit_file.get_messages('session'):
        start_lat = session.get_value('start_position_lat')
        start_lon = session.get_value('start_position_long')
        if start_lat is not None and start_lon is not None:
            entry_coords = (
                semicircles_to_degrees(start_lat),
                semicircles_to_degrees(start_lon)
            )
        break
    
    return Location(
        name=metadata.get('location_name', ''),
        entry=entry_coords,
        exit=None,  # Always None for now, TODO: implement exit coordinates parsing
        description=metadata.get('location_description')
    )

def determine_gas_type(oxygen: int, helium: int) -> str:
    """
    Determine gas type based on O2 and He content
    
    Args:
        oxygen: Oxygen percentage
        helium: Helium percentage
    
    Returns:
        str: Gas type ('air', 'nitrox', or 'trimix')
    """
    if oxygen == 21 and helium == 0:
        return 'air'
    elif helium == 0:
        return 'nitrox'
    else:
        return 'trimix'

def parse_garmin_dive(file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dive:
    """Parse a .fit file from a Garmin dive computer and extract the dive information"""
    fit_file = FitFile(file_path)
    metadata = metadata or {}
    
    timeline, start_time = parse_timeline(fit_file)
    basic_info = parse_basic_info(timeline, start_time)
    people = parse_people(metadata)
    location = parse_location(fit_file, metadata)
    
    # Extract gas information
    gas_type = 'air'  # default value
    for message in fit_file.get_messages('dive_gas'):
        oxygen = message.get_value('oxygen_content')
        helium = message.get_value('helium_content')
        if oxygen is not None:  # Only update if we successfully got the values
            gas_type = determine_gas_type(oxygen, helium)
        break  # We only need the first gas for now
    
    return Dive(
        timeline=timeline,
        basics=basic_info,
        people=people,
        location=location,
        gasses=Gasses(
            gas=gas_type,
            start_pressure=metadata.get('start_pressure', 0),
            end_pressure=metadata.get('end_pressure', 0)
        ),
        gear=UsedGear(
            suit=metadata.get('suit'),
            weights=metadata.get('weights', 0.0),
            mask=metadata.get('mask'),
            gloves=metadata.get('gloves'),
            boots=metadata.get('boots'),
            bcd=metadata.get('bcd'),
            fins=metadata.get('fins')
        )
    )
