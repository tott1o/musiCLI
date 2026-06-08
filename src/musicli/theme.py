"""
MusiCLI — Centralized Theme Configuration.

Every color used across the application is defined here.
Change a value in this file and the entire UI updates automatically.

Usage in Python (Rich markup):
    from .theme import ACCENT, TEXT_PRIMARY
    label = f"[bold {ACCENT}]▶[/] [{TEXT_PRIMARY}]{title}[/]"

Usage in DEFAULT_CSS (widget-level):
    from ..theme import ACCENT, BG_PRIMARY
    DEFAULT_CSS = f'''
    MyWidget {{
        background: {BG_PRIMARY};
        color: {ACCENT};
    }}
    '''

Usage in app-level CSS:
    from .theme import generate_css
    class MusiCLIApp(App):
        CSS = generate_css()
"""

# ═══════════════════════════════════════════════════════════════
#  Color Palette — edit these to re-theme the entire app
# ═══════════════════════════════════════════════════════════════

# ── Primary Accent ─────────────────────────────────────────────
ACCENT        = "#38bdf8"   # Cyan-blue — main brand / interactive color
ACCENT_ACTIVE = "#58a6ff"   # Lighter blue — active tabs

# ── YouTube Accent ─────────────────────────────────────────────
YT_ACCENT     = "#ff0000"   # YouTube red

# ── Semantic Colors ────────────────────────────────────────────
WARNING       = "#fbbf24"   # Amber — paused state, warnings
ERROR         = "#f87171"   # Red — errors, destructive actions
FAVORITE      = "#f1c40f"   # Gold — stars ★, hearts ♥

# ── Backgrounds (darkest → lightest) ──────────────────────────
BG_DEEPEST    = "#010409"   # Header bar, sidebar
BG_PRIMARY    = "#0d1117"   # Main content background
BG_ELEVATED   = "#161b22"   # Cards, elevated surfaces, panel labels
BG_SURFACE    = "#111118"   # Modal backgrounds
BG_HOVER      = "#1a2233"   # DataTable cursor / row highlight
BG_HIGHLIGHT  = "#1a1a2e"   # Sidebar option highlight
BG_BUTTON     = "#30363d"   # Button backgrounds, scrollbar
BG_BUTTON_DIM = "#4b5563"   # Stopped-state button bg

# ── Borders ────────────────────────────────────────────────────
BORDER        = "#1e1e2e"   # Primary border color
BORDER_SUBTLE = "#30363d"   # Secondary / subtle border

# ── Text ───────────────────────────────────────────────────────
TEXT_PRIMARY   = "#e6edf3"  # Main body text
TEXT_SECONDARY = "#8b949e"  # Muted labels, metadata
TEXT_HOVER     = "#c9d1d9"  # Hover state text
TEXT_DIM       = "#6e7681"  # Dim / inactive tab text
TEXT_DIMMER    = "#484f58"  # Dimmest text (tab bar default)
TEXT_LYRICS    = "#7c8aaa"  # Alternating lyrics color

# ── Confirm Modal ──────────────────────────────────────────────
DANGER_BG     = "#2d1616"   # Background for destructive buttons


# ═══════════════════════════════════════════════════════════════
#  CSS Generator — produces the app-level stylesheet
# ═══════════════════════════════════════════════════════════════

def generate_css() -> str:
    """Return the complete Textual CSS stylesheet with theme colors injected."""
    return f"""
/* ═══════════════════════════════════════════════════════════════
   MusiCLI – Auto-generated from theme.py
   ═══════════════════════════════════════════════════════════════ */

/* ── Global ─────────────────────────────────────────────────── */
Screen {{
    background: transparent;
    color: {TEXT_PRIMARY};
}}

/* ── Header ─────────────────────────────────────────────────── */
Header {{
    background: {BG_DEEPEST};
    color: {ACCENT};
    dock: top;
    height: 1;
}}
HeaderTitle {{
    color: {ACCENT};
    text-style: bold;
}}
HeaderClock {{
    color: {TEXT_SECONDARY};
    background: transparent;
}}

/* ── Footer ─────────────────────────────────────────────────── */
Footer {{
    background: transparent;
    color: {TEXT_SECONDARY};
}}
FooterKey {{
    background: transparent;
    color: {ACCENT};
}}

/* ── Main layout ────────────────────────────────────────────── */
#main-container {{
    width: 1fr;
    height: 1fr;
    background: transparent;
}}

#content-area {{
    width: 1fr;
    height: 1fr;
    background: transparent;
}}

#content-view {{
    width: 1fr;
    height: 1fr;
    background: transparent;
}}

/* ── Sidebar ────────────────────────────────────────────────── */
Sidebar {{
    width: 30;
    height: 1fr;
    background: rgba(1, 4, 9, 0.6);
    border-right: solid {BORDER};
    transition: offset 200ms in_out_cubic;
}}

Sidebar.-hidden {{
    offset-x: -30;
    width: 0;
}}

/* ── Album Art Panel ────────────────────────────────────────── */
AlbumArtPanel {{
    width: 42;
    height: 1fr;
    background: rgba(13, 17, 23, 0.4);
    border-left: solid {BORDER};
    transition: offset 200ms in_out_cubic;
}}

AlbumArtPanel.-hidden {{
    offset-x: 42;
    width: 0;
}}

/* ── Top Bar ────────────────────────────────────────────────── */
#top-bar {{
    height: 3;
    background: transparent;
    border-bottom: solid {BORDER};
    width: 100%;
    padding: 0 0;
    align: center middle;
}}

#nav-tabs {{
    width: 1fr;
    border: none;
    height: 1;
}}

/* ── Tabs ──────────────────────────────────────────────────── */
Tabs {{
    background: transparent;
    border: none;
    height: 1;
    min-height: 1;
    margin: 1 0 0 0;
}}
Tabs > Tab {{
    padding: 0 4;
    margin: 0;
    text-style: none;
    background: transparent;
    color: {TEXT_PRIMARY};
    border: none;
    height: 1;
    content-align: center middle;
    transition: color 150ms;
}}
Tabs > Tab:hover {{
    color: {ACCENT};
    background: transparent;
    text-style: none;
}}
Tabs > Tab.-active {{
    color: {BG_DEEPEST};
    background: {ACCENT};
    text-style: bold;
    border: none;
}}
Tabs > .textual-tabs--active {{
    color: {BG_DEEPEST};
    background: {ACCENT};
    text-style: bold;
}}
Tabs .textual-tabs--underline {{
    display: none;
}}

/* ── DataTables ────────────────────────────────────────────── */
DataTable {{
    background: transparent;
    color: {TEXT_PRIMARY};
    border: none;
    height: 1fr;
}}
DataTable > .datatable--header {{
    background: transparent;
    color: {TEXT_SECONDARY};
    text-style: bold;
}}
DataTable > .datatable--cursor {{
    background: {BG_HOVER};
    color: {ACCENT};
    text-style: bold;
}}
DataTable > .datatable--hover {{
    background: rgba(22, 27, 34, 0.5);
}}

/* ── Now Playing Bar ───────────────────────────────────────── */
NowPlayingBar {{
    height: 6;
    background: rgba(22, 27, 34, 0.85);
    border-top: solid {ACCENT};
    padding: 0 2;
    dock: bottom;
    transition: offset 200ms in_out_cubic;
}}

NowPlayingBar.-hidden {{
    offset-y: 6;
}}

/* ── Toast / Notifications ──────────────────────────────────── */
Toast {{
    background: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border: none;
    padding: 1 2;
    width: auto;
    min-width: 30;
    max-width: 60;
    margin: 0 1;
    outline: solid {BORDER_SUBTLE};
}}

Toast.-information {{
    border-left: thick {ACCENT};
}}

Toast.-warning {{
    border-left: thick {WARNING};
}}

Toast.-error {{
    border-left: thick {ERROR};
}}
"""
