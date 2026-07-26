"""Routes for the Add Gear tab."""

from flask import Blueprint, flash, redirect, request, url_for

from backend.services import gear_service

gear_bp = Blueprint("gear", __name__, url_prefix="/gear")


def _to_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@gear_bp.post("/add")
def add_gear():
    form = request.form
    try:
        output_path = gear_service.add_gear(
            gear_type=form.get("gear_type", ""),
            name=form.get("name", ""),
            description=form.get("description", ""),
            is_rental=form.get("is_rental") == "on",
            thickness=_to_int(form.get("thickness")),
            size=_to_int(form.get("size")),
            glove_size=form.get("glove_size"),
        )
        flash(
            f"Gear '{form.get('name', '').strip()}' saved successfully! "
            f"Saved to: {output_path}",
            "success",
        )
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        flash(f"Failed to save gear: {e}", "error")
    return redirect(url_for("pages.gear_page"))
