"""
Configuration constants for MusiCLI.

Centralizes all tunable values so the rest of the codebase stays
free of magic numbers and hardcoded paths.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ── Audio formats ───────────────────────────────────────────────
# Formats that are supported natively by our audio engine (VLC).
AUDIO_FORMATS = {".mp3", ".ogg", ".wav", ".flac", ".m4a", ".aac", ".wma", ".opus"}

# Union of both sets – used during folder scanning.
SUPPORTED_FORMATS = AUDIO_FORMATS

# ── App metadata ────────────────────────────────────────────────
APP_NAME = "MusiCLI"
APP_VERSION = "1.0.0"

# ── State persistence ──────────────────────────────────────────
STATE_DIR = Path(os.path.expanduser("~")) / ".musicli"
STATE_FILE = STATE_DIR / "state.json"
TEMP_DIR = STATE_DIR / "temp"          # for converted audio files
YT_DOWNLOADS_DIR = STATE_DIR / "youtube_downloads"

# ── Playback defaults ──────────────────────────────────────────
MAX_RECENT = 50                        # recently-played history cap
SEEK_STEP = 5                         # seconds per arrow-key seek
VOLUME_STEP = 0.05                    # per key-press volume delta
PROGRESS_INTERVAL = 0.1               # UI refresh rate (seconds)
DEFAULT_VOLUME = 0.7

# ── UI constants ────────────────────────────────────────────────
SIDEBAR_WIDTH = 32
NOTIFICATION_TIMEOUT = 3.0

# ── YouTube configuration ───────────────────────────────────────
# Loaded from .env file
YOUTUBE_COOKIES_FROM_BROWSER = os.getenv("YOUTUBE_COOKIES_FROM_BROWSER")
YOUTUBE_COOKIES_FILE = os.getenv("YOUTUBE_COOKIES_FILE")
YOUTUBE_SEARCH_LIMIT = 50
