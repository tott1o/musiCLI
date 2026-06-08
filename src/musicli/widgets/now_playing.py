"""
Now-playing bar – always docked to the bottom.

Premium edition with a clean layout and prominent progress bar.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Grid, Vertical
from textual.widget import Widget
from textual.widgets import Static

from ..theme import (
    ACCENT,
    BG_BUTTON_DIM,
    BG_PRIMARY,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    WARNING,
)
from ..utils import format_duration, make_progress_bar, volume_bar


class NowPlayingBar(Widget):
    """Bottom bar with track info, progress bar, and controls."""

    DEFAULT_CSS = f"""
    NowPlayingBar {{
        dock: bottom;
        height: 6;
        background: rgba(22, 27, 34, 0.85);
        border-top: solid {ACCENT};
        padding: 0 2;
        transition: offset 200ms in_out_cubic;
    }}
    
    NowPlayingBar.-hidden {{
        offset-y: 6;
    }}
    
    #np-grid {{
        grid-size: 3;
        grid-columns: 1fr 2fr 1fr;
        height: 100%;
    }}

    /* ── Left: Info Bay ─────────────────────────────────────── */
    #np-info-bay {{
        height: 100%;
        content-align: left middle;
        padding-left: 1;
    }}
    #np-status-tag {{
        color: {BG_PRIMARY};
        background: {ACCENT};
        width: auto;
        padding: 0 1;
        text-style: bold;
        margin-bottom: 0;
    }}
    #np-track-name {{
        color: {TEXT_PRIMARY};
        text-style: bold;
        height: 1;
        margin-top: 1;
    }}
    #np-artist-name {{
        color: {TEXT_SECONDARY};
        text-style: italic;
    }}

    /* ── Center: Performance Bay ─────────────────────────────── */
    #np-performance-bay {{
        height: 100%;
        content-align: center middle;
    }}
    #np-time-row {{
        width: 100%;
        color: {TEXT_SECONDARY};
        text-align: center;
        margin-top: 1;
    }}
    #np-progress {{
        width: 100%;
        text-align: center;
    }}

    /* ── Right: Control Bay ──────────────────────────────────── */
    #np-control-bay {{
        height: 100%;
        content-align: right middle;
        padding-right: 1;
    }}
    #np-modes {{
        color: {TEXT_PRIMARY};
        margin-bottom: 1;
        text-style: bold;
    }}
    #np-volume-container {{
        color: {ACCENT};
        text-align: right;
    }}
    """

    def compose(self) -> ComposeResult:
        with Grid(id="np-grid"):
            # Left
            with Vertical(id="np-info-bay"):
                yield Static("STOPPED", id="np-status-tag")
                yield Static("No track loaded", id="np-track-name")
                yield Static("", id="np-artist-name")

            # Center
            with Vertical(id="np-performance-bay"):
                yield Static("", id="np-progress")
                yield Static("", id="np-time-row")
            # Right
            with Vertical(id="np-control-bay"):
                yield Static("", id="np-modes")
                yield Static("Vol 0%", id="np-volume-container")

    # ── Public API ──────────────────────────────────────────────

    def update_display(
        self,
        title: str = "",
        artist: str = "",
        playlist: str = "",
        position: float = 0.0,
        duration: float = 0.0,
        is_playing: bool = False,
        is_paused: bool = False,
        shuffle: bool = False,
        repeat: str = "off",
        vol: float = 0.7,
        bass: float = 0.0,
    ) -> None:
        """Refresh every element of the premium now-playing bar."""

        # 1. Left: Info Bay
        status_tag = self.query_one("#np-status-tag", Static)
        if is_playing:
            status_tag.update(" PLAYING ")
            status_tag.styles.background = ACCENT
        elif is_paused:
            status_tag.update(" PAUSED ")
            status_tag.styles.background = WARNING
        else:
            status_tag.update(" STOPPED ")
            status_tag.styles.background = BG_BUTTON_DIM

        track_label = self.query_one("#np-track-name", Static)
        if title:
            track_label.update(title)
            self.query_one("#np-artist-name", Static).update(artist)
        else:
            track_label.update("No track loaded")
            self.query_one("#np-artist-name", Static).update("")

        # 2. Center: Performance Bay
        time_row = self.query_one("#np-time-row", Static)
        time_cur = format_duration(position)
        time_tot = format_duration(duration)
        time_row.update(f"[bold {TEXT_PRIMARY}]{time_cur}[/]  [dim]/  {time_tot}[/]")

        progress_label = self.query_one("#np-progress", Static)

        # Calculate a responsive width for the progress bar
        bar_width = 30
        if self.size.width > 100:
            bar_width = 40
        elif self.size.width < 60:
            bar_width = 20

        bar = make_progress_bar(position, duration, width=bar_width)
        progress_label.update(bar)

        # 3. Right: Control Bay
        modes_label = self.query_one("#np-modes", Static)
        shuf = f"[{ACCENT}]SHUFFLE[/]" if shuffle else "[dim]SHUFFLE[/dim]"
        rep_map = {
            "off": "[dim]REPEAT[/dim]",
            "all": f"[{ACCENT}]REP-ALL[/]",
            "one": f"[{WARNING}]REP-ONE[/]",
        }
        rep = rep_map.get(repeat, "[dim]REPEAT[/dim]")

        modes_label.update(f"{shuf}  |  {rep}")

        vol_label = self.query_one("#np-volume-container", Static)
        vol_label.update(f"VOLUME  {volume_bar(vol, 12)}  {int(vol * 100)}%")

