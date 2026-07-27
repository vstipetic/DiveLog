"""
Gear service: list existing gear pickles and create new gear items.

Wraps the untouched Utilities layer (AddGear, GearClasses).
"""

import pickle
from pathlib import Path
from typing import Dict, Optional

from Utilities.AddGear import add_mask, add_suit, add_gloves, add_boots
from Utilities.ClassUtils.GearClasses import (
    Mask, Suit, Gloves, Boots, BCD, Fins, GloveSize,
)

GEAR_FOLDER = Path("Storage/Gear")

GEAR_TYPES = ["Mask", "Suit", "Gloves", "Boots"]
GLOVE_SIZES = ["S", "M", "L", "XL"]


def load_gear_items() -> Dict[str, Dict[str, str]]:
    """Load all gear items from Storage/Gear, keyed by type then name -> path."""
    gear_items = {
        "Mask": {},
        "Suit": {},
        "Gloves": {},
        "Boots": {},
        "BCD": {},
        "Fins": {},
    }

    if not GEAR_FOLDER.exists():
        return gear_items

    for gear_file in GEAR_FOLDER.glob("*.pickle"):
        try:
            with open(gear_file, "rb") as f:
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
        except Exception:
            continue

    return gear_items


def add_gear(
    gear_type: str,
    name: str,
    description: Optional[str],
    is_rental: bool,
    thickness: Optional[int],
    size: Optional[int],
    glove_size: Optional[str],
) -> str:
    """
    Create and persist a new gear item. Returns the output path.

    Raises ValueError on invalid input or name collision.
    """
    if gear_type not in GEAR_TYPES:
        raise ValueError(f"Invalid gear type: {gear_type}")
    if not name or not name.strip():
        raise ValueError("Please enter a name for the gear.")

    GEAR_FOLDER.mkdir(parents=True, exist_ok=True)

    safe_name = name.strip().replace(" ", "_").replace("/", "-").replace("\\", "-")
    output_path = GEAR_FOLDER / f"{safe_name}.pickle"

    if output_path.exists():
        raise ValueError(
            f"Gear with name '{name}' already exists. Choose a different name."
        )

    common_args = {
        "name": name.strip(),
        "output_path": str(output_path),
        "number_of_dives": 0,
        "total_dive_time": 0,
        "description": description.strip() if description and description.strip() else None,
        "is_rental": is_rental,
    }

    if gear_type == "Mask":
        add_mask(**common_args)
    elif gear_type == "Suit":
        add_suit(thickness=thickness, size=size, **common_args)
    elif gear_type == "Gloves":
        if glove_size not in GLOVE_SIZES:
            raise ValueError(f"Invalid glove size: {glove_size}")
        add_gloves(thickness=thickness, size=GloveSize[glove_size], **common_args)
    elif gear_type == "Boots":
        add_boots(thickness=thickness, size=size, **common_args)

    return str(output_path)
