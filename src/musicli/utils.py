"""
Utility helpers for MusiCLI.

Small, pure functions that don't depend on any framework.
"""

import sys
from pathlib import Path

from .theme import ACCENT, BG_ELEVATED, BORDER_SUBTLE


def resolve_resource(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # In frozen state, base_path is the temporary folder created by PyInstaller.
        # If we used --add-data "musicli;musicli", resources are inside 'musicli' folder there.
        base_path = Path(sys._MEIPASS) / "musicli"
    else:
        # In development, look relative to the 'musicli' package directory
        base_path = Path(__file__).resolve().parent

    resource = base_path / relative_path
    return str(resource)


def format_duration(seconds: float) -> str:
    """Convert seconds → readable string (M:SS or H:MM:SS)."""
    if seconds < 0:
        return "0:00"
    total = int(seconds)
    hrs, remainder = divmod(total, 3600)
    mins, secs = divmod(remainder, 60)
    if hrs > 0:
        return f"{hrs}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


def truncate(text: str, max_len: int, suffix: str = "…") -> str:
    """Shorten *text* to *max_len* chars, appending *suffix* if trimmed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix


def make_progress_bar(
    current: float,
    total: float,
    width: int = 30,
    filled_char: str = "━",
    empty_char: str = "─",
    knob_char: str = "●",
    filled_color: str = ACCENT,
    empty_color: str = BORDER_SUBTLE,
    knob_color: str = ACCENT,
) -> str:
    """Build a Rich-markup progress bar string."""
    if total <= 0:
        ratio = 0.0
    else:
        ratio = max(0.0, min(1.0, current / total))

    filled_count = int(ratio * width)
    empty_count = width - filled_count - 1

    if filled_count >= width:
        filled_count = width - 1
        empty_count = 0

    bar = (
        f"[{filled_color}]{filled_char * filled_count}{knob_char}[/]"
        f"[{empty_color}]{empty_char * max(0, empty_count)}[/]"
    )
    return bar


def volume_bar(volume: float, width: int = 10) -> str:
    """Build a Rich-markup volume indicator."""
    filled = int(volume * width)
    empty = width - filled
    return (
        f"[{ACCENT}]{'█' * filled}[/]"
        f"[{BORDER_SUBTLE}]{'░' * empty}[/]"
    )


def modern_bar(value: float, width: int = 20) -> str:
    """A sleek, modern level bar with a subtle cyan-to-blue gradient."""
    value = max(0.0, min(1.0, value))
    filled_len = int(value * width)
    empty_len = width - filled_len

    # Gradient colors (from dark blue to bright cyan)
    colors = ["#1e3a8a", "#1d4ed8", "#2563eb", "#3b82f6", "#60a5fa", "#93c5fd", ACCENT, "#7dd3fc", "#bae6fd"]

    bar = ""
    for i in range(filled_len):
        # Pick color based on position
        color_idx = min(int((i / width) * len(colors)), len(colors) - 1)
        bar += f"[{colors[color_idx]}]█[/]"

    bar += f"[{BG_ELEVATED}]{'█' * empty_len}[/]"
    return bar

