from fitparse import FitFile
from datetime import datetime
from typing import Optional, List, Dict, Any, Set, Tuple
from Utilities.ClassUtils.DiveClass import DiveTimeline, DiveBasicInformation, Dive, People, Gasses, Location, UsedGear
from datetime import datetime, timedelta
import logging

# Set up logging for extraction debugging
logger = logging.getLogger(__name__)


def semicircles_to_degrees(semicircles: float) -> float:
    """Convert semicircles to degrees"""
    return round(semicircles * (180.0 / 2**31), 6)


def parse_dive_summary(fit_file: FitFile) -> Dict[str, Any]:
    """
    Extract dive summary data from the fit file.

    Available fields from dive_summary message:
        - dive_number: The dive number from the dive computer
        - avg_depth: Average depth in meters
        - max_depth: Maximum depth in meters
        - bottom_time: Bottom time in seconds
        - surface_interval: Time since last dive in seconds
        - start_n2, end_n2: Nitrogen loading at start/end
        - start_cns, end_cns: CNS loading at start/end
        - o2_toxicity: Oxygen toxicity percentage

    Returns:
        Dictionary with extracted dive summary data
    """
    summary = {}

    for message in fit_file.get_messages('dive_summary'):
        # Prefer the session-referenced summary over lap-referenced
        ref_mesg = message.get_value('reference_mesg')

        summary['dive_number'] = message.get_value('dive_number')
        summary['avg_depth'] = message.get_value('avg_depth')
        summary['max_depth'] = message.get_value('max_depth')
        summary['bottom_time'] = message.get_value('bottom_time')
        summary['surface_interval'] = message.get_value('surface_interval')
        summary['start_n2'] = message.get_value('start_n2')
        summary['end_n2'] = message.get_value('end_n2')
        summary['start_cns'] = message.get_value('start_cns')
        summary['end_cns'] = message.get_value('end_cns')
        summary['o2_toxicity'] = message.get_value('o2_toxicity')

        # If this is the session reference, use it (more complete)
        if ref_mesg == 'session':
            break

    return summary


def parse_dive_settings(fit_file: FitFile) -> Dict[str, Any]:
    """
    Extract dive settings from the fit file.

    Available fields from dive_settings message:
        - water_type: 'salt' or 'fresh'
        - water_density: Water density in kg/m³
        - gf_high, gf_low: Gradient factor settings
        - safety_stop_enabled: Boolean
        - safety_stop_time: Safety stop duration in seconds
        - po2_critical, po2_warn, po2_deco: PO2 limits

    Returns:
        Dictionary with extracted dive settings
    """
    settings = {}

    for message in fit_file.get_messages('dive_settings'):
        settings['water_type'] = message.get_value('water_type')
        settings['water_density'] = message.get_value('water_density')
        settings['gf_high'] = message.get_value('gf_high')
        settings['gf_low'] = message.get_value('gf_low')
        settings['safety_stop_enabled'] = message.get_value('safety_stop_enabled')
        settings['safety_stop_time'] = message.get_value('safety_stop_time')
        settings['po2_critical'] = message.get_value('po2_critical')
        settings['po2_warn'] = message.get_value('po2_warn')
        settings['po2_deco'] = message.get_value('po2_deco')
        break

    return settings


def parse_session_data(fit_file: FitFile) -> Dict[str, Any]:
    """
    Extract session-level data from the fit file.

    Available fields:
        - avg_temperature: Average water temperature in Celsius
        - max_temperature: Maximum water temperature in Celsius
        - avg_heart_rate: Average heart rate in bpm
        - max_heart_rate: Maximum heart rate in bpm
        - total_distance: Distance traveled in meters
        - total_calories: Calories burned
        - start_position_lat/long: Entry GPS coordinates

    Returns:
        Dictionary with extracted session data
    """
    session_data = {}

    for session in fit_file.get_messages('session'):
        session_data['avg_temperature'] = session.get_value('avg_temperature')
        session_data['max_temperature'] = session.get_value('max_temperature')
        session_data['avg_heart_rate'] = session.get_value('avg_heart_rate')
        session_data['max_heart_rate'] = session.get_value('max_heart_rate')
        session_data['total_distance'] = session.get_value('total_distance')
        session_data['total_calories'] = session.get_value('total_calories')
        break

    return session_data


def parse_user_profile(fit_file: FitFile) -> Dict[str, Any]:
    """
    Extract user profile data from the fit file.

    Available fields:
        - weight: User weight in kg
        - height: User height in meters
        - dive_count: Total dive count (cumulative)

    Returns:
        Dictionary with extracted user profile data
    """
    profile = {}

    for message in fit_file.get_messages('user_profile'):
        profile['weight'] = message.get_value('weight')
        profile['height'] = message.get_value('height')
        profile['dive_count'] = message.get_value('dive_count')
        break

    return profile


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
    Extract location information from the fit file and metadata.

    Note: Location NAME is NOT stored in .fit files - it must be provided via metadata.
    Only GPS coordinates are extracted from the .fit file.

    Args:
        fit_file: FitFile object containing the dive data
        metadata: Dictionary containing location information (name, description)

    Returns:
        Location object with name, description, and entry coordinates if available
    """
    entry_coords = None
    exit_coords = None

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
        exit=exit_coords,  # TODO: implement exit coordinates parsing
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
    """
    Parse a .fit file from a Garmin dive computer and extract the dive information.

    Auto-extracted from .fit file:
        - Timeline data (depths, temperatures, N2/CNS loads, timestamps)
        - Basic info (duration, start/end times)
        - Entry GPS coordinates
        - Gas type (air/nitrox/trimix) and O2/He percentages
        - Location name (from filename if not in metadata)

    Additional data extracted but not stored in Dive class (logged only):
        - Dive number, surface interval, water type
        - Heart rate, calories, distance
        - Gradient factors, PO2 settings

    Requires manual input (via metadata):
        - Buddy, divemaster, group members
        - Location description
        - Gas start/end pressures (NOT in .fit files)
        - Gear selection (suit, mask, etc.)
        - Weight belt weight

    Args:
        file_path: Path to the .fit file
        metadata: Optional dictionary with manual metadata overrides:
            - location_name: Override auto-extracted location
            - location_description: Description of the dive site
            - buddy: Name of dive buddy
            - divemaster: Name of divemaster
            - group: List of group member names
            - start_pressure: Tank start pressure (bar)
            - end_pressure: Tank end pressure (bar)
            - suit, mask, gloves, boots, bcd, fins: Gear objects
            - weights: Weight belt weight in kg

    Returns:
        Dive object containing all dive information
    """
    fit_file = FitFile(file_path)
    metadata = metadata or {}

    # Extract all available data from .fit file
    dive_summary = parse_dive_summary(fit_file)
    dive_settings = parse_dive_settings(fit_file)
    session_data = parse_session_data(fit_file)
    user_profile = parse_user_profile(fit_file)

    # Log extracted data for debugging
    logger.info(f"Parsing dive from: {file_path}")
    logger.debug(f"  Dive Summary: dive_number={dive_summary.get('dive_number')}, "
                 f"max_depth={dive_summary.get('max_depth')}m, "
                 f"bottom_time={dive_summary.get('bottom_time')}s")
    logger.debug(f"  Dive Settings: water_type={dive_settings.get('water_type')}, "
                 f"GF={dive_settings.get('gf_low')}/{dive_settings.get('gf_high')}")
    logger.debug(f"  Session Data: avg_temp={session_data.get('avg_temperature')}°C, "
                 f"avg_hr={session_data.get('avg_heart_rate')}bpm")
    logger.debug(f"  User Profile: weight={user_profile.get('weight')}kg")

    # Parse core timeline and basic info
    timeline, start_time = parse_timeline(fit_file)
    basic_info = parse_basic_info(timeline, start_time)
    people = parse_people(metadata)
    location = parse_location(fit_file, metadata)

    # Log what was auto-extracted vs manual
    auto_extracted = []
    manual_input = []

    if location.entry:
        auto_extracted.append(f"entry_coords={location.entry}")

    if location.name:
        manual_input.append(f"location_name='{location.name}'")

    if people.buddy:
        manual_input.append(f"buddy='{people.buddy}'")

    if metadata.get('start_pressure') or metadata.get('end_pressure'):
        manual_input.append(f"pressures={metadata.get('start_pressure')}/{metadata.get('end_pressure')}")

    if auto_extracted:
        logger.info(f"  Auto-extracted: {', '.join(auto_extracted)}")
    if manual_input:
        logger.info(f"  Manual input: {', '.join(manual_input)}")

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


def get_fit_file_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract all available metadata from a .fit file for preview/display.

    This function extracts ALL available data from the .fit file, useful for
    showing users what was auto-extracted before confirming import.

    Args:
        file_path: Path to the .fit file

    Returns:
        Dictionary containing all extracted metadata
    """
    fit_file = FitFile(file_path)

    # Parse all data
    dive_summary = parse_dive_summary(fit_file)
    dive_settings = parse_dive_settings(fit_file)
    session_data = parse_session_data(fit_file)
    user_profile = parse_user_profile(fit_file)
    timeline, start_time = parse_timeline(fit_file)

    # Extract entry coordinates
    entry_coords = None
    for session in fit_file.get_messages('session'):
        start_lat = session.get_value('start_position_lat')
        start_lon = session.get_value('start_position_long')
        if start_lat is not None and start_lon is not None:
            entry_coords = (
                semicircles_to_degrees(start_lat),
                semicircles_to_degrees(start_lon)
            )
        break

    # Extract gas type
    gas_type = 'air'
    oxygen_content = 21
    helium_content = 0
    for message in fit_file.get_messages('dive_gas'):
        oxygen_content = message.get_value('oxygen_content') or 21
        helium_content = message.get_value('helium_content') or 0
        gas_type = determine_gas_type(oxygen_content, helium_content)
        break

    return {
        # Auto-extracted from .fit file
        'auto_extracted': {
            'entry_coordinates': entry_coords,
            'dive_number': dive_summary.get('dive_number'),
            'start_time': start_time,
            'duration': timeline.timestamps[-1] if timeline.timestamps else 0,
            'max_depth': max(timeline.depths) if timeline.depths else dive_summary.get('max_depth', 0),
            'avg_depth': dive_summary.get('avg_depth'),
            'bottom_time': dive_summary.get('bottom_time'),
            'gas_type': gas_type,
            'oxygen_content': oxygen_content,
            'helium_content': helium_content,
            'water_type': dive_settings.get('water_type'),
            'avg_temperature': session_data.get('avg_temperature'),
            'max_temperature': session_data.get('max_temperature'),
            'avg_heart_rate': session_data.get('avg_heart_rate'),
            'max_heart_rate': session_data.get('max_heart_rate'),
            'total_calories': session_data.get('total_calories'),
            'surface_interval': dive_summary.get('surface_interval'),
            'gf_low': dive_settings.get('gf_low'),
            'gf_high': dive_settings.get('gf_high'),
            'user_weight': user_profile.get('weight'),
        },
        # Fields that need manual input (NOT in .fit files)
        'needs_manual_input': {
            'location_name': None,       # NOT in .fit files!
            'location_description': None,
            'buddy': None,
            'divemaster': None,
            'group': None,
            'start_pressure': None,      # NOT in .fit files!
            'end_pressure': None,        # NOT in .fit files!
            'suit': None,
            'mask': None,
            'gloves': None,
            'boots': None,
            'bcd': None,
            'fins': None,
            'weights': None,
        }
    }
