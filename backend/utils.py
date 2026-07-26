"""Small formatting helpers shared by backend services and Jinja templates."""

from typing import Optional


def format_duration(seconds: Optional[float]) -> str:
    """Format duration in seconds to 'Xm Ys' or 'Xh Ym Zs'."""
    if seconds is None:
        return "N/A"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes >= 60:
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours}h {minutes}m {secs}s"
    return f"{minutes}m {secs}s"


def format_surface_interval(seconds: Optional[float]) -> str:
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
