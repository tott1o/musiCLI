"""
Track list widget – displays songs in a sortable DataTable.

Supports highlighting the currently-playing track, inline favourite
indicators, and sorting by any column.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import DataTable, Static

from ..theme import (
    ACCENT,
    BG_ELEVATED,
    BG_PRIMARY,
    FAVORITE,
    TEXT_SECONDARY,
)
from ..utils import truncate

if TYPE_CHECKING:
    from ..models import Song


class TrackList(Vertical):
    """Main content area showing a list of songs."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("delete", "remove_track", "Remove from Playlist"),
        Binding("x", "remove_track", "Remove", show=False),
    ]

    DEFAULT_CSS = f"""
    TrackList {{
        background: {BG_PRIMARY};
        padding: 0;
    }}
    TrackList #view-header {{
        width: 100%;
        padding: 1 2 0 2;
        color: {ACCENT};
        text-style: bold;
    }}
    TrackList #view-subheader {{
        width: 100%;
        padding: 0 2 1 2;
        color: {TEXT_SECONDARY};
    }}
    TrackList DataTable {{
        background: {BG_PRIMARY};
        scrollbar-size: 1 1;
        height: 1fr;
        border: none;
    }}
    TrackList DataTable > .datatable--header {{
        background: {BG_PRIMARY};
        color: {TEXT_SECONDARY};
        text-style: bold;
    }}
    TrackList DataTable > .datatable--cursor {{
        background: {ACCENT};
        color: {BG_PRIMARY};
        text-style: bold;
    }}
    TrackList DataTable > .datatable--header-cursor {{
        background: {BG_PRIMARY};
        color: {ACCENT};
    }}
    TrackList DataTable > .datatable--hover {{
        background: {BG_ELEVATED};
    }}
    """

    class TrackSelected(Message):
        """User wants to play this song."""

        def __init__(self, song_path: str) -> None:
            super().__init__()
            self.song_path = song_path

    class TrackAddToQueue(Message):
        """User wants to enqueue this song."""

        def __init__(self, song_path: str) -> None:
            super().__init__()
            self.song_path = song_path

    class TrackToggleFavorite(Message):
        """User wants to favourite/unfavourite this song."""

        def __init__(self, song_path: str) -> None:
            super().__init__()
            self.song_path = song_path

    class TrackRemoveRequested(Message):
        """User wants to remove this song from the current playlist."""

        def __init__(self, song_path: str) -> None:
            super().__init__()
            self.song_path = song_path

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._songs: list[Song] = []
        self._current_playing_path: str | None = None
        self._view_title: str = "All Songs"
        self._favorites: set = set()
        self._sort_key: str | None = None
        self._sort_reverse: bool = False

    def compose(self) -> ComposeResult:
        yield Static("[b]ALL-SONGS[/b]", id="view-header")
        yield Static("0 tracks", id="view-subheader")
        yield DataTable(id="tracks-table")

    def on_mount(self) -> None:
        table = self.query_one("#tracks-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = False
        table.add_column("   ", key="status", width=3)
        table.add_column("Title", key="title")
        table.add_column("Artist", key="artist")
        table.add_column("Album", key="album")
        table.add_column("Duration", key="duration")

    def action_cursor_down(self) -> None:
        self.query_one("#tracks-table", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#tracks-table", DataTable).action_cursor_up()

    def action_remove_track(self) -> None:
        path = self._get_selected_path()
        if path:
            self.post_message(self.TrackRemoveRequested(path))

    # ── Public API ──────────────────────────────────────────────

    def update_tracks(
        self,
        songs: list[Song],
        title: str = "All Songs",
        favorites: set | None = None,
    ) -> None:
        """Replace displayed songs with *songs*."""
        self._songs = list(songs)
        self._view_title = title
        if favorites is not None:
            self._favorites = favorites

        # Reset scroll for new track list
        table = self.query_one("#tracks-table", DataTable)
        table.scroll_to(0, 0, animate=False)

        self._refresh_table(reset_cursor=True)
        self._update_header()

    def highlight_playing(self, song_path: str | None) -> None:
        """Mark the currently-playing track."""
        if self._current_playing_path == song_path:
            return
        self._current_playing_path = song_path
        self._refresh_table(reset_cursor=False)

    def set_favorites(self, favorites: set) -> None:
        self._favorites = favorites
        self._refresh_table(reset_cursor=False)

    def sort_by(self, key: str) -> None:
        """Sort tracks by column key. Toggles direction on repeat."""
        if self._sort_key == key:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_key = key
            self._sort_reverse = False

        key_funcs = {
            "title": lambda s: s.display_title.lower(),
            "artist": lambda s: s.display_artist.lower(),
            "album": lambda s: s.display_album.lower(),
            "duration": lambda s: s.duration,
            "type": lambda s: s.format,
        }
        func = key_funcs.get(key)
        if func:
            self._songs.sort(key=func, reverse=self._sort_reverse)
            self._refresh_table(reset_cursor=False)

    # ── Internal ────────────────────────────────────────────────

    def _update_header(self) -> None:
        header = self.query_one("#view-header", Static)
        header.update(f"  {self._view_title}")
        sub = self.query_one("#view-subheader", Static)
        count = len(self._songs)
        sub.update(f"  {count} track{'s' if count != 1 else ''}")

    def _refresh_table(self, reset_cursor: bool = False) -> None:
        table = self.query_one("#tracks-table", DataTable)

        # Save state
        cursor_coord = table.cursor_coordinate
        scroll_x, scroll_y = table.scroll_offset

        table.clear()
        for idx, song in enumerate(self._songs):
            # Styling title if it is currently playing
            title = truncate(song.display_title, 45)
            artist = truncate(song.display_artist, 30)
            album = truncate(song.display_album, 30)

            status = " "
            if song.path == self._current_playing_path:
                status = f"[bold {ACCENT}]▶[/]"
                title = f"[bold {ACCENT}]{title}[/]"
            elif song.path in self._favorites or getattr(song, 'is_stream', False):
                # For streaming songs, we check if they are starred in AppState
                # However, TrackList doesn't have access to AppState directly.
                # But when update_tracks is called for YouTube Stars, we can pass a special flag or just assume they are starred.
                if self._view_title == "YouTube Stars":
                    status = f"[{FAVORITE}]★[/]"
                elif song.path in self._favorites:
                    status = f"[{FAVORITE}]♥[/]"

            table.add_row(
                status,
                title,
                artist,
                album,
                song.duration_str,
                key=f"t_{idx}_{song.path}",
            )

        # Restore state
        if not reset_cursor and cursor_coord:
            row = min(cursor_coord.row, len(self._songs) - 1)
            if row >= 0:
                table.cursor_coordinate = (row, cursor_coord.column)
            table.scroll_to(scroll_x, scroll_y, animate=False)

    # ── Events ──────────────────────────────────────────────────

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        raw_key = str(event.row_key.value)
        # Strip "t_N_" prefix to get actual path
        path = raw_key.split("_", 2)[2] if raw_key.startswith("t_") else raw_key
        self.post_message(self.TrackSelected(path))

    def _get_selected_path(self) -> str | None:
        """Return the path of the currently-highlighted row."""
        table = self.query_one("#tracks-table", DataTable)
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            raw_key = str(row_key.value) if row_key else None
            if raw_key and raw_key.startswith("t_"):
                return raw_key.split("_", 2)[2]
            return raw_key
        except Exception:
            return None
