from Utilities.ClassUtils.DiveClass import Dive
from Utilities.Parsers.GarminDiveParser import parse_garmin_dive, get_fit_file_metadata
import pickle
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import shutil
import logging

logger = logging.getLogger(__name__)


def add_dive(fit_file_path: str,
            output_path: str,
            location_name: str = '',
            location_description: str = '',
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
            fins: Optional[str] = None,
            copy_fit_file: bool = False) -> Dive:
    """
    Create a Dive object from a .fit file and metadata, and save it as a pickle file.

    Auto-extraction:
        - Location name is auto-extracted from the filename if not provided
        - Entry GPS coordinates are auto-extracted from the .fit file
        - Gas type (air/nitrox/trimix) is auto-extracted from the .fit file

    Manual input still required for:
        - Buddy, divemaster, group members
        - Location description
        - Tank pressures (NOT in .fit files)
        - Gear selection
        - Weights

    Args:
        fit_file_path: Path to the .fit file containing dive data
        output_path: Path where to save the pickle file
        location_name: Name of dive location (auto-extracted from filename if empty)
        location_description: Description of the dive location
        buddy: Name of dive buddy
        divemaster: Name of divemaster
        group: Set of names of other people in dive group
        gas: Gas mixture used
        start_pressure: Starting gas pressure (bar)
        end_pressure: Ending gas pressure (bar)
        suit: Path to pickle file containing suit gear object
        weights: Weight in kg used
        mask: Path to pickle file containing mask gear object
        gloves: Path to pickle file containing gloves gear object
        boots: Path to pickle file containing boots gear object
        bcd: Path to pickle file containing BCD gear object
        fins: Path to pickle file containing fins gear object
        copy_fit_file: If True, copy the .fit file to FitFiles/ subfolder

    Returns:
        Dive object containing all dive information
    """
    metadata: Dict[str, Any] = {
        'location_name': location_name,
        'location_description': location_description,
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

    print(f"Parsing dive: {Path(fit_file_path).name}")
    dive = parse_garmin_dive(fit_file_path, metadata)

    # Save dive object
    output_path = Path(output_path)
    with open(output_path, 'wb') as f:
        pickle.dump(dive, f)

    # Optionally copy .fit file to FitFiles subfolder
    if copy_fit_file:
        fit_files_dir = output_path.parent / "FitFiles"
        fit_files_dir.mkdir(exist_ok=True)
        dest_path = fit_files_dir / Path(fit_file_path).name
        shutil.copy2(fit_file_path, dest_path)
        print(f"  Copied .fit file to: {dest_path}")

    return dive


def bulk_add_dives(fit_files_dir: str, output_dir: str,
                   copy_fit_files: bool = True,
                   verbose: bool = True) -> Tuple[List[Dive], List[Dict[str, Any]]]:
    """
    Create multiple Dive objects from all .fit files in a directory.

    This function is optimized for fully automated import with zero manual input.
    It auto-extracts all available data from .fit files:
        - Location name from filename (e.g., "87 Baron Gautsch.fit" -> "Baron Gautsch")
        - Entry GPS coordinates
        - Gas type (air/nitrox/trimix)
        - Timeline data (depth, temperature, N2/CNS loads)
        - Basic info (duration, start/end times)

    Fields NOT available in .fit files (will be empty/default):
        - Buddy, divemaster, group
        - Location description
        - Tank pressures
        - Gear selection
        - Weights

    Args:
        fit_files_dir: Directory containing .fit files
        output_dir: Directory where to save the pickle files
        copy_fit_files: If True, copy .fit files to FitFiles/ subfolder (default: True)
        verbose: If True, print detailed progress and extraction info (default: True)

    Returns:
        Tuple of:
            - List[Dive]: List of successfully created Dive objects
            - List[Dict]: List of extraction reports for each dive
    """
    fit_files_dir = Path(fit_files_dir)
    output_dir = Path(output_dir)

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create FitFiles subdirectory if copying
    if copy_fit_files:
        fit_files_dest = output_dir / "FitFiles"
        fit_files_dest.mkdir(exist_ok=True)

    created_dives = []
    extraction_reports = []

    # Get all .fit files
    fit_files = sorted(fit_files_dir.glob("*.fit"))

    if verbose:
        print(f"\n{'='*60}")
        print(f"BULK DIVE IMPORT")
        print(f"{'='*60}")
        print(f"Source: {fit_files_dir}")
        print(f"Destination: {output_dir}")
        print(f"Found {len(fit_files)} .fit files to import")
        print(f"{'='*60}\n")

    # Process all .fit files
    for i, fit_file in enumerate(fit_files):
        output_path = output_dir / f"{fit_file.stem}.pickle"

        try:
            # Get metadata preview for reporting
            metadata_preview = get_fit_file_metadata(str(fit_file))
            auto_extracted = metadata_preview['auto_extracted']

            if verbose:
                print(f"[{i+1}/{len(fit_files)}] {fit_file.name}")
                print(f"  Depth: {auto_extracted.get('max_depth', 0):.1f}m max, "
                      f"{auto_extracted.get('avg_depth', 0):.1f}m avg")
                print(f"  Duration: {auto_extracted.get('duration', 0)/60:.1f} min")
                print(f"  Gas: {auto_extracted.get('gas_type')} "
                      f"(O2: {auto_extracted.get('oxygen_content')}%)")
                if auto_extracted.get('entry_coordinates'):
                    lat, lon = auto_extracted['entry_coordinates']
                    print(f"  GPS: {lat:.4f}, {lon:.4f}")
                print()

            # Create dive with auto-extraction (no manual metadata)
            dive = parse_garmin_dive(str(fit_file))

            # Save dive
            with open(output_path, 'wb') as f:
                pickle.dump(dive, f)

            # Copy .fit file if requested
            if copy_fit_files:
                dest_path = fit_files_dest / fit_file.name
                shutil.copy2(fit_file, dest_path)

            created_dives.append(dive)
            extraction_reports.append({
                'filename': fit_file.name,
                'status': 'success',
                'auto_extracted': auto_extracted,
                'output_path': str(output_path)
            })

        except Exception as e:
            if verbose:
                print(f"  ERROR: {str(e)}")
            extraction_reports.append({
                'filename': fit_file.name,
                'status': 'error',
                'error': str(e)
            })

    # Print summary
    if verbose:
        success_count = sum(1 for r in extraction_reports if r['status'] == 'success')
        error_count = sum(1 for r in extraction_reports if r['status'] == 'error')

        print(f"\n{'='*60}")
        print(f"IMPORT COMPLETE")
        print(f"{'='*60}")
        print(f"Successful: {success_count}")
        print(f"Failed: {error_count}")

        # Summary of what was auto-extracted
        gps_extracted = sum(
            1 for r in extraction_reports
            if r['status'] == 'success' and r['auto_extracted'].get('entry_coordinates')
        )

        print(f"\nAuto-extracted data:")
        print(f"  - GPS coordinates: {gps_extracted}/{success_count} dives")

        print(f"\nFields NOT in .fit files (require manual input):")
        print(f"  - Location name")
        print(f"  - Buddy/divemaster/group")
        print(f"  - Location description")
        print(f"  - Tank pressures")
        print(f"  - Gear/weights")
        print(f"{'='*60}\n")

    return created_dives, extraction_reports


def preview_fit_file(fit_file_path: str) -> Dict[str, Any]:
    """
    Preview what data can be extracted from a .fit file before importing.

    This is useful for showing users what will be auto-extracted vs what
    they need to provide manually.

    Args:
        fit_file_path: Path to the .fit file

    Returns:
        Dictionary with 'auto_extracted' and 'needs_manual_input' sections
    """
    return get_fit_file_metadata(fit_file_path)
