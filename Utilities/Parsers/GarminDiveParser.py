from fitparse import FitFile
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from Utilities.ClassUtils.DiveClass import DiveTimeline, DiveBasicInformation, Dive, People, Gasses, Location, UsedGear

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
        
        depths.append(values.get('depth', 0.0) / 1000.0)  # Convert from mm to meters
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
    return DiveBasicInformation(
        duration=timeline.timestamps[-1] if timeline.timestamps else 0.0,
        start_time=start_time
    )

def parse_people(metadata: Dict[str, Any]) -> People:
    """Parse the people information from metadata"""
    return People(
        buddy=metadata.get('buddy', ''),
        divemaster=metadata.get('divemaster'),
        group=set(metadata.get('group', []))
    )

def parse_garmin_dive(file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dive:
    """
    Parse a .fit file from a Garmin dive computer and extract the dive information
    
    Args:
        file_path: Path to the .fit file containing the dive data
        metadata: Optional dictionary containing additional dive information like people
        
    Returns:
        Dive object containing all dive information
    """
    fit_file = FitFile(file_path)
    metadata = metadata or {}
    
    timeline, start_time = parse_timeline(fit_file)
    basic_info = parse_basic_info(timeline, start_time)
    people = parse_people(metadata)
    
    return Dive(
        timeline=timeline,
        basics=basic_info,
        people=people,
        location=Location(
            name=metadata.get('location_name', ''),
            description=metadata.get('location_description', ''),
            coordinates=metadata.get('coordinates')
        ),
        gasses=Gasses(
            gas=metadata.get('gas', ''),
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
