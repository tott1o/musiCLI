"""
YouTube panel – search and play music from YouTube.
"""

from __future__ import annotations

import socket
import threading
from typing import List, Optional

from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.message import Message
from textual.widgets import DataTable, Static, Input, Button, LoadingIndicator

from ..utils import truncate

from ..models import Song
from ..config import YOUTUBE_COOKIES_FROM_BROWSER, YOUTUBE_COOKIES_FILE, YOUTUBE_SEARCH_LIMIT
from ..theme import YT_ACCENT, FAVORITE, BG_PRIMARY, BG_HOVER, TEXT_SECONDARY

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


class YoutubePanel(Vertical):
    """View for searching and playing YouTube music."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("enter", "play_selected", "Play"),
        Binding("f", "add_to_playlist", "Add to Playlist"),
        Binding("a", "add_to_queue", "Add to Queue"),
        Binding("n", "next_page", "Next Results"),
    ]

    DEFAULT_CSS = f"""
    YoutubePanel {{
        background: {BG_PRIMARY};
        padding: 0;
    }}
    YoutubePanel #yt-header {{
        width: 100%;
        padding: 1 2;
        color: {YT_ACCENT};
        text-style: bold;
        background: {BG_PRIMARY};
    }}
    YoutubePanel #yt-search-container {{
        height: auto;
        padding: 0 2 1 2;
        background: {BG_PRIMARY};
        align: left middle;
    }}
    YoutubePanel #yt-search-input {{
        width: 1fr;
        border: tall #333;
    }}
    YoutubePanel #yt-search-input:focus {{
        border: tall {YT_ACCENT};
    }}
    YoutubePanel Button {{
        margin-left: 1;
        min-width: 10;
        height: 3;
        border: tall #333;
    }}
    YoutubePanel #yt-info {{
        width: 100%;
        padding: 0 2 1 2;
        color: {TEXT_SECONDARY};
        background: {BG_PRIMARY};
    }}
    YoutubePanel DataTable {{
        background: {BG_PRIMARY};
        scrollbar-size: 1 1;
        max-width: 100%;
    }}
    YoutubePanel DataTable > .datatable--cursor {{
        background: {BG_HOVER};
        color: {YT_ACCENT};
    }}
    YoutubePanel LoadingIndicator {{
        height: 1;
        margin: 0 2;
        color: {YT_ACCENT};
    }}
    """

    class YoutubeTrackSelected(Message):
        """Posted when a YouTube track is selected to play."""
        def __init__(self, song: Song) -> None:
            super().__init__()
            self.song = song

    class YoutubeTrackAddToPlaylist(Message):
        """Posted when the user wants to add a YouTube track to a playlist."""
        def __init__(self, song: Song) -> None:
            super().__init__()
            self.song = song

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._results: List[Song] = []
        self._is_searching: bool = False
        self._current_playing_path: Optional[str] = None
        self._starred_paths: List[str] = []
        self._current_query: str = ""
        self._search_offset: int = 0

    def set_starred(self, paths: List[str]) -> None:
        """Update the list of starred YouTube paths."""
        self._starred_paths = paths
        if self._results:
            self._refresh_table()

    def compose(self) -> ComposeResult:
        yield Static("[b] ▶ YOUTUBE-MUSIC[/b]", id="yt-header")
        with Horizontal(id="yt-search-container"):
            yield Input(placeholder="Search YouTube...", id="yt-search-input")
            yield Button("Search", id="yt-search-btn", variant="primary")
            yield Button("Next", id="yt-next-btn", variant="default")
        yield Static("Search for songs, artists, or albums", id="yt-info")
        yield LoadingIndicator(id="yt-loading")
        yield DataTable(id="yt-table")

    def on_mount(self) -> None:
        self.query_one("#yt-loading").display = False
        table = self.query_one("#yt-table", DataTable)
        table.cursor_type = "row"
        table.add_column("   ", key="status", width=3)
        table.add_column("Title", key="title")
        table.add_column("Artist", key="artist")
        table.add_column("Duration", key="duration")

    @on(Input.Submitted, "#yt-search-input")
    def handle_search(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if not query or self._is_searching:
            return

        if not yt_dlp:
            self.app.notify("yt-dlp not installed. Please install it with 'pip install yt-dlp'.", severity="error")
            return

        # Always reset offset when submitting a search via Enter
        # unless we explicitly want "Enter on same query = Next"
        # The user said "it should be reset after enter search", 
        # implying Enter should start fresh.
        self._current_query = query
        self._search_offset = 0
        self._start_search(self._current_query, self._search_offset)

    @on(Button.Pressed, "#yt-search-btn")
    def on_search_button(self) -> None:
        query = self.query_one("#yt-search-input").value.strip()
        if query:
            self._current_query = query
            self._search_offset = 0
            self._start_search(self._current_query, self._search_offset)

    @on(Button.Pressed, "#yt-next-btn")
    def on_next_button(self) -> None:
        self.action_next_page()

    def action_next_page(self) -> None:
        """Load the next set of YouTube search results."""
        if not self._current_query or self._is_searching:
            return
        self._search_offset += YOUTUBE_SEARCH_LIMIT
        self._start_search(self._current_query, self._search_offset)

    def _start_search(self, query: str, offset: int = 0) -> None:
        self._is_searching = True
        self.query_one("#yt-loading").display = True
        self.query_one("#yt-table").display = False
        
        msg = f"Searching for '{query}'..."
        if offset > 0:
            msg = f"Searching for '{query}' (Results {offset + 1}-{offset + YOUTUBE_SEARCH_LIMIT})..."
        self.query_one("#yt-info").update(msg)

        # Run search in a thread to avoid blocking UI
        thread = threading.Thread(target=self._run_youtube_search, args=(query, offset))
        thread.daemon = True
        thread.start()

    @staticmethod
    def _has_internet(timeout_s: float = 1.5) -> bool:
        """Best-effort check for internet connectivity.

        We avoid making HTTP requests and just attempt a short TCP connection.
        """
        try:
            sock = socket.create_connection(("1.1.1.1", 53), timeout=timeout_s)
            sock.close()
            return True
        except OSError:
            return False

    def _run_youtube_search(self, query: str, offset: int = 0) -> None:
        if not self._has_internet():
            self.app.call_from_thread(
                self.app.notify,
                "You're offline. Connect to the internet to search YouTube.",
                title="YouTube",
                severity="warning",
            )
            self.app.call_from_thread(self._finish_search, [])
            return

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'skip_download': True,
            'extractor_args': {'youtube': {'player_client': ['android_vr', 'ios', 'android', 'mweb', 'web']}},
            'playliststart': offset + 1,
            'playlistend': offset + YOUTUBE_SEARCH_LIMIT,
        }
        
        if YOUTUBE_COOKIES_FROM_BROWSER:
            ydl_opts['cookiesfrombrowser'] = (YOUTUBE_COOKIES_FROM_BROWSER,)
        elif YOUTUBE_COOKIES_FILE:
            ydl_opts['cookiefile'] = YOUTUBE_COOKIES_FILE
        
        results = []
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # search for results - using 1000 as a large limit for pagination
                search_query = f"ytsearch1000:{query}"
                info = ydl.extract_info(search_query, download=False)
                
                if 'entries' in info:
                    for entry in info['entries']:
                        if not entry: continue
                        song = Song(
                            path=entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}",
                            filename=entry.get('title', 'Unknown'),
                            title=entry.get('title', 'Unknown'),
                            artist=entry.get('uploader', 'Unknown Artist'),
                            album="YouTube",
                            duration=entry.get('duration', 0.0),
                            format="web",
                            playlist_name="YouTube Search",
                            is_stream=True,
                            thumbnail=entry.get('thumbnail', '')
                        )
                        results.append(song)
        except Exception as e:
            # ... (error handling)
            err_msg = str(e)
            if "confirm you're not a bot" in err_msg.lower():
                err_msg = "YouTube bot detection triggered. Try setting YOUTUBE_COOKIES_FROM_BROWSER in .env"
            offline_markers = (
                "temporary failure in name resolution",
                "name or service not known",
                "nodename nor servname provided",
                "getaddrinfo failed",
                "network is unreachable",
                "no route to host",
                "connection timed out",
                "failed to establish a new connection",
            )
            if any(m in err_msg.lower() for m in offline_markers):
                self.app.call_from_thread(
                    self.app.notify,
                    "You're offline. Connect to the internet to search YouTube.",
                    title="YouTube",
                    severity="warning",
                )
            else:
                self.app.call_from_thread(self.app.notify, f"Search failed: {err_msg}", severity="error")

        self.app.call_from_thread(self._finish_search, results)

    def highlight_playing(self, song_path: Optional[str]) -> None:
        """Mark the currently-playing track in the search results."""
        if self._current_playing_path == song_path:
            return
        self._current_playing_path = song_path
        if self._results:
            self._refresh_table()

    def _refresh_table(self) -> None:
        """Refresh the results table with current highlighting."""
        table = self.query_one("#yt-table", DataTable)
        
        # Save state
        cursor_coord = table.cursor_coordinate
        scroll_x, scroll_y = table.scroll_offset

        table.clear()
        for idx, song in enumerate(self._results):
            status = " "
            title = truncate(song.display_title, 50)
            artist = truncate(song.display_artist, 40)
            
            if song.path == self._current_playing_path:
                status = f"[bold {YT_ACCENT}]▶[/]"
                title = f"[bold {YT_ACCENT}]{title}[/]"
            elif song.path in self._starred_paths:
                status = f"[{FAVORITE}]★[/]"

            table.add_row(
                status,
                title,
                artist,
                song.duration_str,
                key=f"yt_{idx}"
            )

        # Restore state
        if cursor_coord:
            row = min(cursor_coord.row, len(self._results) - 1)
            if row >= 0:
                table.cursor_coordinate = (row, cursor_coord.column)
            table.scroll_to(scroll_x, scroll_y, animate=False)

    def action_add_to_playlist(self) -> None:
        """Add the currently-selected song to a YouTube playlist."""
        song = self.get_selected_song()
        if song:
            self.post_message(self.YoutubeTrackAddToPlaylist(song))

    def action_play_selected(self) -> None:
        """Play the currently-selected song."""
        song = self.get_selected_song()
        if song:
            self.post_message(self.YoutubeTrackSelected(song))

    def action_add_to_queue(self) -> None:
        """Add the currently-selected song to the play queue."""
        # We can just let the app handle the global 'a' binding if we update _get_selected_track_path
        # But for clarity, we can also post a message.
        # Actually, let's just let the app handle it.
        pass

    def _finish_search(self, results: List[Song]) -> None:
        self._is_searching = False
        self._results = results
        
        self.query_one("#yt-loading").display = False
        self.query_one("#yt-table").display = True
        
        self._refresh_table()
        
        if not results:
            self.query_one("#yt-info").update("No more results found.")
        else:
            start = self._search_offset + 1
            end = self._search_offset + len(results)
            self.query_one("#yt-info").update(f"Showing results {start}-{end} for '{self._current_query}'")
        
        table = self.query_one("#yt-table", DataTable)
        table.focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        idx_str = str(event.row_key.value)
        if idx_str.startswith("yt_"):
            idx = int(idx_str[3:])
            if 0 <= idx < len(self._results):
                self.post_message(self.YoutubeTrackSelected(self._results[idx]))

    def get_selected_song(self) -> Optional[Song]:
        """Return the song currently highlighted in the table."""
        table = self.query_one("#yt-table", DataTable)
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            idx_str = str(row_key.value) if row_key else None
            if idx_str and idx_str.startswith("yt_"):
                idx = int(idx_str[3:])
                if 0 <= idx < len(self._results):
                    return self._results[idx]
        except Exception:
            pass
        return None

    def action_cursor_down(self) -> None:
        self.query_one("#yt-table", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#yt-table", DataTable).action_cursor_up()
