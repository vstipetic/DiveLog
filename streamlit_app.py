"""
Streamlit UI for DiveLog - AI-powered dive statistics assistant.

This module provides a modern web interface for querying dive statistics
using natural language through the StatisticsAgent.

Run with: streamlit run streamlit_app.py
"""

import streamlit as st
import os
import pickle
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from Utilities.StatisticsAgent import StatisticsAgent
from Utilities.APIKeyDetector import detect_api_keys
from Utilities.Parsers.GarminDiveParser import parse_garmin_dive, get_fit_file_metadata
from Utilities.AddDive import add_dive, bulk_add_dives, preview_fit_file
from Utilities.ClassUtils.GearClasses import Gear, Mask, Suit, Gloves, Boots, BCD, Fins


# Page configuration
st.set_page_config(
    page_title="DiveLog - AI Assistant",
    page_icon="🤿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .dive-stat-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .example-query {
        background-color: #e1e5eb;
        padding: 0.5rem 1rem;
        border-radius: 0.25rem;
        margin: 0.25rem 0;
        cursor: pointer;
    }
    .example-query:hover {
        background-color: #d1d5db;
    }
    .auto-extracted {
        background-color: #d1fae5;
        padding: 0.5rem;
        border-radius: 0.25rem;
        border-left: 3px solid #10b981;
        margin-bottom: 0.5rem;
    }
    .manual-input {
        background-color: #fef3c7;
        padding: 0.5rem;
        border-radius: 0.25rem;
        border-left: 3px solid #f59e0b;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


def get_provider_from_key_name(key_name: str) -> str:
    """Map API key name to provider code."""
    provider_map = {
        "OpenAI": "openai",
        "Gemini": "gemini",
        "Claude": "claude",
        "Anthropic": "claude",
    }
    # Check for partial matches
    for name, provider in provider_map.items():
        if name.lower() in key_name.lower():
            return provider
    return "gemini"  # Default


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "api_key" not in st.session_state:
        st.session_state.api_key = None
    if "provider" not in st.session_state:
        st.session_state.provider = None
    if "storage_folder" not in st.session_state:
        st.session_state.storage_folder = "Storage/BulkDives"
    if "import_mode" not in st.session_state:
        st.session_state.import_mode = "Single Dive"
    if "import_messages" not in st.session_state:
        st.session_state.import_messages = []
    if "fit_preview" not in st.session_state:
        st.session_state.fit_preview = None


def create_agent(api_key: str, provider: str, dive_folder: str = None) -> StatisticsAgent:
    """Create or return cached agent."""
    if dive_folder is None:
        dive_folder = st.session_state.storage_folder

    # Check if we need to create a new agent
    if (st.session_state.agent is None or
        st.session_state.api_key != api_key or
        st.session_state.provider != provider):

        with st.spinner("Initializing AI agent..."):
            try:
                agent = StatisticsAgent(
                    api_key=api_key,
                    dive_folder=dive_folder,
                    provider=provider
                )
                st.session_state.agent = agent
                st.session_state.api_key = api_key
                st.session_state.provider = provider
            except Exception as e:
                st.error(f"Failed to initialize agent: {str(e)}")
                return None

    return st.session_state.agent


def load_gear_items() -> Dict[str, Dict[str, str]]:
    """Load all gear items from Storage/Gear folder."""
    gear_folder = Path("Storage/Gear")
    gear_items = {
        "Mask": {},
        "Suit": {},
        "Gloves": {},
        "Boots": {},
        "BCD": {},
        "Fins": {}
    }

    if not gear_folder.exists():
        return gear_items

    for gear_file in gear_folder.glob("*.pickle"):
        try:
            with open(gear_file, 'rb') as f:
                gear = pickle.load(f)
                if isinstance(gear, Mask):
                    gear_items["Mask"][gear.name] = str(gear_file)
                elif isinstance(gear, Suit):
                    gear_items["Suit"][gear.name] = str(gear_file)
                elif isinstance(gear, Gloves):
                    gear_items["Gloves"][gear.name] = str(gear_file)
                elif isinstance(gear, Boots):
                    gear_items["Boots"][gear.name] = str(gear_file)
                elif isinstance(gear, BCD):
                    gear_items["BCD"][gear.name] = str(gear_file)
                elif isinstance(gear, Fins):
                    gear_items["Fins"][gear.name] = str(gear_file)
        except Exception as e:
            continue

    return gear_items


def refresh_agent():
    """Refresh the agent with current storage folder."""
    st.session_state.agent = None
    st.cache_resource.clear()


def format_duration(seconds: float) -> str:
    """Format duration in seconds to mm:ss or hh:mm:ss."""
    if seconds is None:
        return "N/A"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes >= 60:
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours}h {minutes}m {secs}s"
    return f"{minutes}m {secs}s"


def format_surface_interval(seconds: float) -> str:
    """Format surface interval to human readable."""
    if seconds is None:
        return "N/A"
    hours = seconds / 3600
    if hours >= 24:
        days = hours / 24
        return f"{days:.1f} days"
    elif hours >= 1:
        return f"{hours:.1f} hours"
    else:
        return f"{seconds/60:.0f} minutes"


def render_import_tab():
    """Render the Import Dives tab."""
    st.header("Import Dives")

    # Storage folder selection
    st.subheader("Storage Settings")
    col1, col2 = st.columns([3, 1])

    with col1:
        new_folder = st.text_input(
            "Storage Folder",
            value=st.session_state.storage_folder,
            help="Path to the folder where dive files will be stored"
        )

    with col2:
        if st.button("Apply", use_container_width=True):
            folder_path = Path(new_folder)
            if not folder_path.exists():
                try:
                    folder_path.mkdir(parents=True, exist_ok=True)
                    st.success(f"Created folder: {new_folder}")
                except Exception as e:
                    st.error(f"Failed to create folder: {e}")
                    return
            st.session_state.storage_folder = new_folder
            refresh_agent()
            st.success(f"Storage folder updated to: {new_folder}")
            st.rerun()

    # Validate folder exists
    storage_path = Path(st.session_state.storage_folder)
    if not storage_path.exists():
        st.warning(f"Folder '{st.session_state.storage_folder}' does not exist. Click 'Apply' to create it.")

    st.divider()

    # Import mode selection
    st.subheader("Import Mode")
    import_mode = st.radio(
        "Select import mode:",
        ["Single Dive", "Bulk Import"],
        horizontal=True,
        index=0 if st.session_state.import_mode == "Single Dive" else 1
    )
    st.session_state.import_mode = import_mode

    st.divider()

    if import_mode == "Single Dive":
        render_single_dive_import()
    else:
        render_bulk_import()

    st.divider()

    # Refresh functionality
    st.subheader("Refresh Dives")
    col1, col2 = st.columns([2, 2])

    with col1:
        if st.button("Reload All Dives", use_container_width=True, type="primary"):
            refresh_agent()
            st.success("Agent cache cleared. Dives will be reloaded on next query.")

            # Count dives in storage folder
            storage_path = Path(st.session_state.storage_folder)
            if storage_path.exists():
                dive_count = len(list(storage_path.glob("*.pickle")))
                st.info(f"Found {dive_count} dive files in storage folder.")
            st.rerun()

    with col2:
        storage_path = Path(st.session_state.storage_folder)
        if storage_path.exists():
            dive_count = len(list(storage_path.glob("*.pickle")))
            st.metric("Dives in Storage", dive_count)


def render_single_dive_import():
    """Render the single dive import form."""
    st.subheader("Single Dive Import")

    # File uploader
    uploaded_file = st.file_uploader(
        "Upload .fit file",
        type=["fit"],
        help="Select a Garmin .fit file containing dive data"
    )

    if uploaded_file is None:
        st.info("Upload a .fit file to begin importing a dive.")
        st.session_state.fit_preview = None
        return

    st.success(f"File loaded: {uploaded_file.name}")

    # Save to temp and get preview
    with tempfile.NamedTemporaryFile(delete=False, suffix=".fit") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name

    # Get auto-extracted preview
    try:
        preview = get_fit_file_metadata(tmp_file_path)
        auto_data = preview['auto_extracted']
        st.session_state.fit_preview = preview
    except Exception as e:
        st.error(f"Failed to parse .fit file: {e}")
        os.unlink(tmp_file_path)
        return

    # Show auto-extracted data
    st.subheader("Auto-Extracted Data")
    st.markdown('<div class="auto-extracted">', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Dive #", auto_data.get('dive_number', 'N/A'))
    with col2:
        st.metric("Max Depth", f"{auto_data.get('max_depth', 0):.1f}m")
    with col3:
        st.metric("Duration", format_duration(auto_data.get('duration', 0)))
    with col4:
        st.metric("Gas", f"{auto_data.get('gas_type', 'air').title()}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        start_time = auto_data.get('start_time')
        if start_time:
            st.metric("Date", start_time.strftime("%Y-%m-%d"))
    with col2:
        st.metric("Avg Depth", f"{auto_data.get('avg_depth', 0):.1f}m")
    with col3:
        st.metric("Water Temp", f"{auto_data.get('avg_temperature', 'N/A')}°C")
    with col4:
        st.metric("Water Type", str(auto_data.get('water_type', 'unknown')).title())

    # GPS coordinates if available
    if auto_data.get('entry_coordinates'):
        lat, lon = auto_data['entry_coordinates']
        st.caption(f"📍 GPS: {lat:.6f}, {lon:.6f}")

    # Surface interval
    if auto_data.get('surface_interval'):
        st.caption(f"⏱️ Surface interval: {format_surface_interval(auto_data['surface_interval'])}")

    st.markdown('</div>', unsafe_allow_html=True)

    # Show what still needs manual input
    st.subheader("Manual Input Required")
    st.markdown('<div class="manual-input">', unsafe_allow_html=True)
    st.caption("The following fields are NOT stored in .fit files and require manual entry:")
    st.caption("• Buddy, divemaster, group • Location description • Tank pressures • Gear/weights")
    st.markdown('</div>', unsafe_allow_html=True)

    # Metadata form
    st.subheader("Dive Metadata")

    # People section
    with st.expander("People", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            buddy = st.text_input("Buddy Name", help="Name of your dive buddy")
        with col2:
            divemaster = st.text_input("Divemaster (optional)", help="Name of the divemaster")

        group_input = st.text_input(
            "Group Members (optional)",
            help="Comma-separated list of other people in the dive group"
        )

    # Location section
    with st.expander("Location", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            location_name = st.text_input(
                "Location Name",
                help="Name of the dive site (NOT stored in .fit files)"
            )
        with col2:
            pass  # Placeholder for symmetry

        location_description = st.text_area(
            "Location Description (optional)",
            help="Additional details about the dive location"
        )

    # Gas section
    with st.expander("Tank Pressures", expanded=True):
        st.caption("⚠️ Tank pressures are NOT stored in .fit files - you must enter them manually")
        col1, col2 = st.columns(2)
        with col1:
            start_pressure = st.number_input(
                "Start Pressure (bar)",
                min_value=0,
                max_value=300,
                value=200,
                help="Starting tank pressure in bar"
            )
        with col2:
            end_pressure = st.number_input(
                "End Pressure (bar)",
                min_value=0,
                max_value=300,
                value=50,
                help="Ending tank pressure in bar"
            )

    # Gear section
    with st.expander("Gear Selection", expanded=True):
        gear_items = load_gear_items()

        col1, col2 = st.columns(2)

        with col1:
            # Suit selection (required)
            suit_options = ["None"] + list(gear_items["Suit"].keys())
            selected_suit = st.selectbox(
                "Suit",
                suit_options,
                help="Select your wetsuit/drysuit"
            )

            # Mask selection
            mask_options = ["None"] + list(gear_items["Mask"].keys())
            selected_mask = st.selectbox(
                "Mask (optional)",
                mask_options,
                help="Select your mask"
            )

            # BCD selection
            bcd_options = ["None"] + list(gear_items["BCD"].keys())
            selected_bcd = st.selectbox(
                "BCD (optional)",
                bcd_options,
                help="Select your BCD"
            )

        with col2:
            # Gloves selection
            gloves_options = ["None"] + list(gear_items["Gloves"].keys())
            selected_gloves = st.selectbox(
                "Gloves (optional)",
                gloves_options,
                help="Select your gloves"
            )

            # Boots selection
            boots_options = ["None"] + list(gear_items["Boots"].keys())
            selected_boots = st.selectbox(
                "Boots (optional)",
                boots_options,
                help="Select your boots"
            )

            # Fins selection
            fins_options = ["None"] + list(gear_items["Fins"].keys())
            selected_fins = st.selectbox(
                "Fins (optional)",
                fins_options,
                help="Select your fins"
            )

        weights = st.number_input(
            "Weights (kg)",
            min_value=0.0,
            max_value=30.0,
            value=0.0,
            step=0.5,
            help="Weight in kilograms"
        )

        if not gear_items["Suit"] and not gear_items["Mask"]:
            st.info("No gear found in Storage/Gear/. You can still import the dive without gear.")

    # Import button
    st.divider()

    if st.button("Import Dive", type="primary", use_container_width=True):
        try:
            # Prepare output path
            storage_path = Path(st.session_state.storage_folder)
            storage_path.mkdir(parents=True, exist_ok=True)
            output_filename = Path(uploaded_file.name).stem + ".pickle"
            output_path = storage_path / output_filename

            # Parse group members
            group = None
            if group_input.strip():
                group = set(name.strip() for name in group_input.split(",") if name.strip())

            # Get gear paths
            suit_path = gear_items["Suit"].get(selected_suit) if selected_suit != "None" else None
            mask_path = gear_items["Mask"].get(selected_mask) if selected_mask != "None" else None
            gloves_path = gear_items["Gloves"].get(selected_gloves) if selected_gloves != "None" else None
            boots_path = gear_items["Boots"].get(selected_boots) if selected_boots != "None" else None
            bcd_path = gear_items["BCD"].get(selected_bcd) if selected_bcd != "None" else None
            fins_path = gear_items["Fins"].get(selected_fins) if selected_fins != "None" else None

            # Create dive using add_dive function
            dive = add_dive(
                fit_file_path=tmp_file_path,
                output_path=str(output_path),
                location_name=location_name,
                location_description=location_description if location_description else None,
                buddy=buddy,
                divemaster=divemaster if divemaster else None,
                group=group,
                start_pressure=int(start_pressure),
                end_pressure=int(end_pressure),
                suit=suit_path,
                weights=float(weights),
                mask=mask_path,
                gloves=gloves_path,
                boots=boots_path,
                bcd=bcd_path,
                fins=fins_path,
                copy_fit_file=True
            )

            # Clean up temp file
            os.unlink(tmp_file_path)

            # Show success
            st.success(f"Dive imported successfully!")

            # Display dive details
            with st.expander("Dive Details", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Duration", f"{dive.basics.duration / 60:.1f} min")
                with col2:
                    if dive.timeline.depths:
                        st.metric("Max Depth", f"{max(dive.timeline.depths):.1f} m")
                with col3:
                    st.metric("Location", location_name or "Unknown")

                st.caption(f"Saved to: {output_path}")

            # Refresh agent to include new dive
            refresh_agent()

        except Exception as e:
            st.error(f"Failed to import dive: {str(e)}")
            import traceback
            st.code(traceback.format_exc())


def render_bulk_import():
    """Render the bulk import interface."""
    st.subheader("Bulk Import")

    # Info about auto-extraction
    st.markdown("""
    <div class="auto-extracted">
    <strong>✨ Auto-Extracted from .fit Files</strong><br>
    <ul>
        <li><strong>GPS coordinates</strong> from session data</li>
        <li><strong>Gas type</strong> (air/nitrox/trimix) and O2%</li>
        <li><strong>All timeline data</strong> (depth, temperature, N2/CNS loads)</li>
        <li><strong>Dive summary</strong> (dive number, surface interval, etc.)</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="manual-input">
    <strong>⚠️ Not Available in .fit Files</strong><br>
    These fields will be empty after bulk import:
    <ul>
        <li><strong>Location name</strong> (NOT stored by Garmin!)</li>
        <li>Location description</li>
        <li>Buddy, divemaster, group members</li>
        <li>Tank pressures (NOT stored by Garmin)</li>
        <li>Gear and weights</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    # Folder input for .fit files
    fit_folder = st.text_input(
        "Folder containing .fit files",
        value="",
        help="Enter the path to a folder containing .fit files to import"
    )

    if not fit_folder:
        st.warning("Enter a folder path to scan for .fit files.")
        return

    fit_folder_path = Path(fit_folder)

    if not fit_folder_path.exists():
        st.error(f"Folder does not exist: {fit_folder}")
        return

    if not fit_folder_path.is_dir():
        st.error(f"Path is not a folder: {fit_folder}")
        return

    # Find all .fit files
    fit_files = sorted(fit_folder_path.glob("*.fit"))

    if not fit_files:
        st.warning(f"No .fit files found in: {fit_folder}")
        return

    # Display file list with preview
    st.success(f"Found {len(fit_files)} .fit files")

    with st.expander("Preview files to import", expanded=False):
        # Show first 10 files with auto-extracted data
        for i, fit_file in enumerate(fit_files[:10]):
            try:
                preview = get_fit_file_metadata(str(fit_file))
                auto_data = preview['auto_extracted']
                depth = auto_data.get('max_depth', 0)
                duration = auto_data.get('duration', 0) / 60
                gas = auto_data.get('gas_type', 'air')
                st.text(f"{i+1}. {fit_file.name}")
                st.caption(f"   → Max depth: {depth:.1f}m, Duration: {duration:.0f}min, Gas: {gas}")
            except:
                st.text(f"{i+1}. {fit_file.name}")
                st.caption(f"   → (preview failed)")

        if len(fit_files) > 10:
            st.text(f"... and {len(fit_files) - 10} more files")

    # Import button
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        copy_fit_files = st.checkbox("Copy .fit files to storage", value=True,
                                     help="Keep a copy of original .fit files alongside the pickle files")

    if st.button("Import All Files", type="primary", use_container_width=True):
        storage_path = Path(st.session_state.storage_folder)
        storage_path.mkdir(parents=True, exist_ok=True)

        progress_bar = st.progress(0)
        status_text = st.empty()

        success_count = 0
        error_count = 0
        errors = []
        gps_extracted = 0

        for i, fit_file in enumerate(fit_files):
            progress = (i + 1) / len(fit_files)
            progress_bar.progress(progress)
            status_text.text(f"Processing: {fit_file.name} ({i+1}/{len(fit_files)})")

            try:
                # Get preview for statistics
                preview = get_fit_file_metadata(str(fit_file))
                auto_data = preview['auto_extracted']

                if auto_data.get('entry_coordinates'):
                    gps_extracted += 1

                output_path = storage_path / f"{fit_file.stem}.pickle"

                # Parse dive with auto-extraction
                dive = parse_garmin_dive(str(fit_file))

                # Save dive
                with open(output_path, 'wb') as f:
                    pickle.dump(dive, f)

                # Copy .fit file if requested
                if copy_fit_files:
                    fit_files_dest = storage_path / "FitFiles"
                    fit_files_dest.mkdir(exist_ok=True)
                    import shutil
                    shutil.copy2(fit_file, fit_files_dest / fit_file.name)

                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append((fit_file.name, str(e)))

        progress_bar.progress(1.0)
        status_text.text("Import complete!")

        # Show results
        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Successful Imports", success_count)
        with col2:
            st.metric("Failed Imports", error_count)

        # Show extraction statistics
        st.subheader("Auto-Extraction Summary")
        st.metric("GPS Coordinates Extracted", f"{gps_extracted}/{success_count}")

        if errors:
            with st.expander("Error Details", expanded=True):
                for filename, error in errors:
                    st.error(f"**{filename}**: {error}")

        # Refresh agent
        refresh_agent()
        st.success("Agent cache cleared. New dives will be loaded on next query.")


def render_sidebar():
    """Render the sidebar with settings and info."""
    with st.sidebar:
        st.header("⚙️ Settings")

        # API Key detection
        api_keys = detect_api_keys()

        if not api_keys:
            st.error("No API keys found!")
            st.info(
                "Set one of these environment variables:\n"
                "- `OPENAI_API_KEY`\n"
                "- `GEMINI_API_KEY`\n"
                "- `ANTHROPIC_API_KEY`"
            )
            return None, None

        # Select API provider
        selected_api = st.selectbox(
            "Select LLM Provider",
            list(api_keys.keys()),
            help="Choose which AI model to use for queries"
        )

        api_key = api_keys[selected_api]
        provider = get_provider_from_key_name(selected_api)

        st.divider()

        # Show current provider info
        provider_info = {
            "gemini": ("🔵 Google Gemini", "gemini-1.5-flash"),
            "openai": ("🟢 OpenAI", "gpt-4o-mini"),
            "claude": ("🟣 Anthropic Claude", "claude-sonnet-4-20250514"),
        }
        info = provider_info.get(provider, ("Unknown", "Unknown"))
        st.caption(f"Using: {info[0]}")
        st.caption(f"Model: {info[1]}")

        st.divider()

        # Quick actions
        st.subheader("Quick Actions")

        if st.button("🔄 Reload Dives", use_container_width=True):
            if st.session_state.agent:
                st.session_state.agent.reload_dives()
                st.success("Dives reloaded!")

        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            if st.session_state.agent:
                st.session_state.agent.clear_history()
            st.rerun()

        st.divider()

        # Help section
        with st.expander("❓ Help"):
            st.markdown("""
            **How to use:**
            1. Make sure you have dive data in `Storage/Dives/`
            2. Ask questions in natural language
            3. The AI will analyze your dives and respond

            **Example questions:**
            - "What's my average depth?"
            - "How many dives did I do this year?"
            - "Show me my deepest dives"
            - "Who is my most common buddy?"
            """)

        return api_key, provider


def render_quick_stats(agent: StatisticsAgent):
    """Render quick statistics cards."""
    if not agent or not agent.dives:
        return

    with st.expander("📊 Quick Stats", expanded=True):
        col1, col2, col3, col4 = st.columns(4)

        total_dives = len(agent.dives)
        total_time = sum(d.basics.duration for d in agent.dives) / 60

        depths = [max(d.timeline.depths) for d in agent.dives if d.timeline.depths]
        avg_depth = sum(depths) / len(depths) if depths else 0
        max_depth = max(depths) if depths else 0

        with col1:
            st.metric("Total Dives", f"{total_dives}")

        with col2:
            st.metric("Total Time", f"{total_time/60:.1f} hours")

        with col3:
            st.metric("Avg Depth", f"{avg_depth:.1f}m")

        with col4:
            st.metric("Max Depth", f"{max_depth:.1f}m")


def render_example_queries():
    """Render clickable example queries."""
    examples = [
        "What's my average dive depth?",
        "How many dives did I do in 2024?",
        "Show me all dives deeper than 20 meters",
        "What's my total dive time?",
        "Who is my most common dive buddy?",
        "List my 5 deepest dives",
        "How much time have I spent below 15 meters?",
        "Show me dives at [location name]",
    ]

    with st.expander("💡 Example Questions", expanded=False):
        cols = st.columns(2)
        for i, example in enumerate(examples):
            col = cols[i % 2]
            with col:
                if st.button(example, key=f"example_{i}", use_container_width=True):
                    return example
    return None


def render_chat_interface(agent: StatisticsAgent):
    """Render the main chat interface."""
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask about your dives..."):
        process_query(agent, prompt)


def process_query(agent: StatisticsAgent, query: str):
    """Process a user query and display the response."""
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing your dives..."):
            try:
                response = agent.process_query(query)
            except Exception as e:
                response = f"Error: {str(e)}"
        st.markdown(response)

    # Add assistant response to chat
    st.session_state.messages.append({"role": "assistant", "content": response})


def render_chat_tab(agent: StatisticsAgent):
    """Render the AI Chat tab content."""
    # Show dive count
    if agent and agent.dives:
        st.success(f"Loaded {len(agent.dives)} dives from your log")
        render_quick_stats(agent)
    else:
        st.warning(
            "No dives found. Add some dives using the Import Dives tab "
            "or import .fit files to `Storage/Dives/`"
        )

    # Example queries (can trigger input)
    example_query = render_example_queries()

    # Main chat interface
    st.subheader("Ask about your dives")
    render_chat_interface(agent)

    # Process example query if clicked
    if example_query:
        process_query(agent, example_query)
        st.rerun()


def main():
    """Main application entry point."""
    # Initialize session state
    init_session_state()

    # Title
    st.title("DiveLog - AI Dive Statistics Assistant")

    # Render sidebar and get configuration
    result = render_sidebar()
    if result is None:
        st.warning("Please configure an API key to continue.")
        return

    api_key, provider = result

    # Create/get agent
    agent = create_agent(api_key, provider)

    if agent is None:
        st.error("Failed to initialize the agent. Please check your API key.")
        return

    # Create tabs
    tab_chat, tab_import = st.tabs(["AI Chat", "Import Dives"])

    with tab_chat:
        render_chat_tab(agent)

    with tab_import:
        render_import_tab()


if __name__ == "__main__":
    main()
