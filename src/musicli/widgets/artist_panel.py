"""
Artist panel – browse library by artist.
"""

from __future__ import annotations

from collections import defaultdict

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import DataTable, Static

from ..models import Song
from ..theme import ACCENT, BG_ELEVATED, BG_HOVER, BG_PRIMARY, BORDER, TEXT_SECONDARY
from ..utils import truncate


class ArtistPanel(Vertical):
    """View for browsing songs by artist."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("a", "add_to_queue", "Add to Queue"),
    ]

    DEFAULT_CSS = f"""
    ArtistPanel {{
        background: {BG_PRIMARY};
        padding: 0;
    }}
    ArtistPanel #artist-header {{
        width: 100%;
        padding: 1 2;
        color: {ACCENT};
        text-style: bold;
    }}
    ArtistPanel #artist-split-container {{
        layout: horizontal;
        height: 1fr;
    }}
    ArtistPanel #artist-list-container {{
        width: 35%;
        height: 1fr;
        border-right: solid {BORDER};
    }}
    ArtistPanel #artist-songs-container {{
        width: 65%;
        height: 1fr;
    }}
    ArtistPanel .panel-label {{
        padding: 0 2;
        background: {BG_ELEVATED};
        color: {TEXT_SECONDARY};
        text-style: bold;
        height: 1;
    }}
    ArtistPanel DataTable {{
        background: {BG_PRIMARY};
        scrollbar-size: 1 1;
        height: 1fr;
        max-width: 100%;
    }}
    ArtistPanel DataTable > .datatable--cursor {{
        background: {BG_HOVER};
        color: {ACCENT};
    }}
    """

    class ArtistSelected(Message):
        """Posted when an artist is highlighted to update the song list."""
        def __init__(self, artist_name: str) -> None:
            super().__init__()
            self.artist_name = artist_name

    class TrackSelected(Message):
        """Posted when a track is selected to be played."""
        def __init__(self, song_path: str) -> None:
            super().__init__()
            self.song_path = song_path

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._all_songs: list[Song] = []
        self._artists: list[str] = []
        self._current_artist: str | None = None
        self._current_playing_path: str | None = None

    def compose(self) -> ComposeResult:
        yield Static("Artists", id="artist-header")
        with Horizontal(id="artist-split-container"):
            with Vertical(id="artist-list-container"):
                yield Static("  ARTISTS", classes="panel-label")
                yield DataTable(id="artist-table")
            with Vertical(id="artist-songs-container"):
                yield Static("  SONGS", id="songs-label", classes="panel-label")
                yield DataTable(id="artist-songs-table")

    def on_mount(self) -> None:
        # Artist table
        at = self.query_one("#artist-table", DataTable)
        at.cursor_type = "row"
        at.add_columns("Artist", "Tracks")

        # Songs table
        st = self.query_one("#artist-songs-table", DataTable)
        st.cursor_type = "row"
        st.add_column("   ", key="status", width=3)
        st.add_column("Title", key="title")
        st.add_column("Album", key="album")
        st.add_column("Duration", key="duration")

    def action_cursor_down(self) -> None:
        # Focus-aware navigation
        if self.query_one("#artist-table").has_focus:
            self.query_one("#artist-table", DataTable).action_cursor_down()
        else:
            self.query_one("#artist-songs-table", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        if self.query_one("#artist-table").has_focus:
            self.query_one("#artist-table", DataTable).action_cursor_up()
        else:
            self.query_one("#artist-songs-table", DataTable).action_cursor_up()

    def get_selected_path(self) -> str | None:
        """Return the path of the currently selected song in the songs table."""
        table = self.query_one("#artist-songs-table", DataTable)
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            raw_key = str(row_key.value) if row_key else None
            if raw_key and raw_key.startswith("as_"):
                # Format: as_idx_path
                parts = raw_key.split("_", 2)
                return parts[2] if len(parts) > 2 else raw_key
        except Exception:
            pass
        return None

    def action_add_to_queue(self) -> None:
        """Let the app handle the 'a' key."""
        pass

    def update_artists(self, songs: list[Song]) -> None:
        """Group songs by artist and refresh the artist list."""
        self._all_songs = songs
        counts = defaultdict(int)
        for song in songs:
            counts[song.display_artist] += 1

        self._artists = sorted(counts.keys(), key=lambda x: x.lower())

        table = self.query_one("#artist-table", DataTable)
        table.clear()

        for artist in self._artists:
            table.add_row(
                truncate(artist, 30),
                str(counts[artist]),
                key=artist
            )

        if self._artists and self._current_artist is None:
            # Select first artist by default if none selected
            self._update_song_list(self._artists[0])

    def highlight_playing(self, song_path: str | None) -> None:
        """Mark the currently-playing track in the songs list."""
        if self._current_playing_path == song_path:
            return
        self._current_playing_path = song_path
        if self._current_artist:
            self._update_song_list(self._current_artist)

    def _update_song_list(self, artist_name: str) -> None:
        """Update the song list for the selected artist."""
        self._current_artist = artist_name
        songs = [s for s in self._all_songs if s.display_artist == artist_name]

        label = self.query_one("#songs-label", Static)
        label.update(f"  SONGS - {artist_name}")

        table = self.query_one("#artist-songs-table", DataTable)

        # Save state
        cursor_coord = table.cursor_coordinate
        scroll_x, scroll_y = table.scroll_offset

        table.clear()
        for idx, song in enumerate(songs):
            status = " "
            title = truncate(song.display_title, 50)
            album = truncate(song.display_album, 35)

            if song.path == self._current_playing_path:
                status = f"[bold {ACCENT}]▶[/]"
                title = f"[bold {ACCENT}]{title}[/]"

            table.add_row(
                status,
                title,
                album,
                song.duration_str,
                key=f"as_{idx}_{song.path}"
            )

        # Restore state
        if cursor_coord:
            row = min(cursor_coord.row, len(songs) - 1)
            if row >= 0:
                table.cursor_coordinate = (row, cursor_coord.column)
            table.scroll_to(scroll_x, scroll_y, animate=False)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Update song list when an artist is highlighted (navigated to)."""
        if event.data_table.id == "artist-table":
            artist_name = str(event.row_key.value)
            self._update_song_list(artist_name)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle selection in either table."""
        if event.data_table.id == "artist-table":
            # Switch focus to songs table on Enter
            self.query_one("#artist-songs-table").focus()
        elif event.data_table.id == "artist-songs-table":
            # Play the song
            raw_key = str(event.row_key.value)
            path = raw_key.split("_", 2)[2] if raw_key.startswith("as_") else raw_key
            self.post_message(self.TrackSelected(path))
