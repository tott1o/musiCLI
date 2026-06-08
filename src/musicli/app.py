"""
MusiCLI – main Textual application.

Orchestrates the player engine, state persistence, and all UI
widgets.  Keyboard bindings live here.
"""

from __future__ import annotations

import sys
import threading
import hashlib
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from textual import events, on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Tabs, Tab, DataTable, Input, Button, Static

from .config import PROGRESS_INTERVAL, SEEK_STEP, NOTIFICATION_TIMEOUT, YOUTUBE_COOKIES_FROM_BROWSER, YOUTUBE_COOKIES_FILE
from .models import Song, Playlist
from .player import MusicPlayer, RepeatMode, PlayerState
from .scanner import scan_root_folder, get_all_songs
from .state import AppState
from .utils import resolve_resource
from .theme import generate_css
from .widgets.sidebar import Sidebar
from .widgets.track_list import TrackList
from .widgets.now_playing import NowPlayingBar
from .widgets.queue_panel import QueuePanel
from .widgets.artist_panel import ArtistPanel
from .widgets.youtube_panel import YoutubePanel
from .widgets.youtube_playlists_modal import YoutubePlaylistModal
from .widgets.new_yt_playlist_modal import NewYoutubePlaylistModal
from .widgets.search_modal import SearchModal
from .widgets.add_library_modal import AddLibraryModal
from .widgets.audio_settings_modal import AudioSettingsModal
from .widgets.album_art import AlbumArtPanel
from .widgets.confirm_modal import ConfirmModal


class MusiCLIApp(App):
    """A Spotify-like terminal music player."""

    TITLE = "MusiCLI"
    SUB_TITLE = "TUI Music Player"
    CSS = generate_css()

    BINDINGS = [
        # ── Playback ────────────────────────────────────────────
        Binding("space", "toggle_play", "Play / Pause", priority=True),
        Binding("n", "next_track", "Next"),
        Binding("b", "prev_track", "Previous"),
        Binding("s", "toggle_shuffle", "Shuffle"),
        Binding("r", "cycle_repeat", "Repeat"),
        Binding("right", "seek_fwd", "Seek →", show=False),
        Binding("left", "seek_bwd", "Seek ←", show=False),
        # ── Volume ──────────────────────────────────────────────
        Binding("right_square_bracket", "vol_up", "Vol Up"),
        Binding("left_square_bracket", "vol_down", "Vol Down"),
        Binding("e", "open_audio_settings", "Audio Settings"),
        # ── Navigation ──────────────────────────────────────────
        Binding("slash", "open_search", "Search"),
        Binding("f", "toggle_fav", "Favorite"),
        Binding("a", "add_to_queue", "Add to Queue"),
        Binding("l", "add_library", "Add Library"),
        Binding("ctrl+right", "next_tab", "Next Tab", show=False),
        Binding("ctrl+left", "prev_tab", "Prev Tab", show=False),
        # ── Layout ──────────────────────────────────────────────
        Binding("ctrl+b", "toggle_sidebar", "Sidebar"),
        Binding("ctrl+j", "toggle_album_art", "Info"),
        # ── Sort ────────────────────────────────────────────────
        Binding("1", "sort_title", "Sort: Title", show=False),
        Binding("2", "sort_artist", "Sort: Artist", show=False),
        Binding("3", "sort_album", "Sort: Album", show=False),
        Binding("4", "sort_duration", "Sort: Duration", show=False),
        Binding("5", "sort_type", "Sort: Type", show=False),
        # ── App ─────────────────────────────────────────────────
        Binding("ctrl+q", "quit_app", "Quit"),
        Binding("escape", "go_back", "Back", show=False),
        Binding("backspace", "go_back", "Back", show=False),
    ]

    def __init__(self, root_path: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.root_path = root_path
        self.player = MusicPlayer()
        self.app_state = AppState()
        self.playlists: List[Playlist] = []
        self.all_songs: List[Song] = []
        self._current_view: str = "all"
        self._last_yt_playlist: Optional[str] = None

    # ────────────────────────────────────────────────────────────
    #  Compose
    # ────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-container"):
            yield Sidebar(id="sidebar")
            with Vertical(id="content-area"):
                with Horizontal(id="top-bar"):
                    yield Tabs(
                        Tab("ALL-SONGS", id="all"),
                        Tab("ARTISTS", id="artists"),
                        Tab("YOUTUBE", id="youtube"),
                        Tab("YT-PLAYLISTS", id="yt-playlists"),
                        Tab("FAVORITES", id="favorites"),
                        Tab("RECENT", id="recent"),
                        Tab("QUEUE", id="queue"),
                        id="nav-tabs"
                    )
                with Horizontal(id="content-view"):
                    yield TrackList(id="track-list")
                    yield QueuePanel(id="queue-panel")
                    yield ArtistPanel(id="artist-panel")
                    yield YoutubePanel(id="youtube-panel")
            yield AlbumArtPanel(id="album-art")
        yield NowPlayingBar(id="now-playing")
        yield Footer()

    # ────────────────────────────────────────────────────────────
    #  Lifecycle
    # ────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        # Prune non-existent libraries
        self.app_state.prune_saved_roots()

        # Enable focus for top tabs to allow tab-navigation
        self.query_one("#nav-tabs", Tabs).can_focus = True

        # Hide panels by default
        self.query_one("#queue-panel", QueuePanel).display = False
        self.query_one("#artist-panel", ArtistPanel).display = False
        self.query_one("#youtube-panel", YoutubePanel).display = False

        # Set callbacks
        self.player.set_callbacks(
            on_track_change=self._on_track_change,
            on_pre_play=self._on_pre_play_hook
        )

        # Scan library
        self._scan_library()

        # Restore previous state
        self._restore_state()

        # Start progress-bar refresh timer
        self.set_interval(PROGRESS_INTERVAL, self._tick)

    def _on_track_change(self, song: Song) -> None:
        """Called by the player whenever a new track starts."""
        album_art = self.query_one("#album-art", AlbumArtPanel)
        album_art.update_song(
            song.path, 
            song.display_title, 
            song.display_artist,
            thumbnail=song.thumbnail
        )
        
        # Refresh queue panel if visible
        if self._current_view == "queue":
            self.query_one("#queue-panel", QueuePanel).update_queue(self.player.queue, self.player.queue_index)
        
        # Sync highlights everywhere
        self._highlight_current()

    def on_unmount(self) -> None:
        try:
            self._save_state()
        except Exception:
            pass
        self.player.cleanup()

    # ────────────────────────────────────────────────────────────
    #  Library scanning
    # ────────────────────────────────────────────────────────────

    def _scan_library(self) -> None:
        sidebar = self.query_one("#sidebar", Sidebar)
        
        if not self.root_path:
            self.playlists = []
            self.all_songs = []
            sidebar.set_libraries(
                saved_roots=self.app_state.saved_roots,
                current_root="",
                youtube_playlists=list(self.app_state.youtube_playlists.keys()),
            )
            self._show_view("all")
            return

        # Add to saved roots immediately so it shows up in sidebar
        self.app_state.add_saved_root(self.root_path)

        try:
            self.playlists = scan_root_folder(self.root_path)
            self.all_songs = get_all_songs(self.playlists)
        except Exception as e:
            self.notify(f"Scan error: {e}", severity="error")
            self.playlists = []
            self.all_songs = []

        if not self.all_songs:
            self.notify("No audio files found in the selected folder.", title="Library", severity="warning", timeout=NOTIFICATION_TIMEOUT)

        sidebar.set_libraries(
            saved_roots=self.app_state.saved_roots,
            current_root=self.root_path,
            youtube_playlists=list(self.app_state.youtube_playlists.keys()),
        )
        self._show_view("all")

        if self.all_songs:
            self.notify(
                f"Loaded {len(self.all_songs)} tracks in {len(self.playlists)} playlists",
                title="Library Loaded",
                severity="information",
                timeout=NOTIFICATION_TIMEOUT,
            )

    # ────────────────────────────────────────────────────────────
    #  View switching
    # ────────────────────────────────────────────────────────────

    def _show_view(self, view_id: str) -> None:
        self._current_view = view_id
        track_list = self.query_one("#track-list", TrackList)
        queue_panel = self.query_one("#queue-panel", QueuePanel)
        artist_panel = self.query_one("#artist-panel", ArtistPanel)
        youtube_panel = self.query_one("#youtube-panel", YoutubePanel)

        # Helper to get all YT songs from all playlists
        def get_all_yt_songs():
            yt_songs = []
            for p_name, p_songs_data in self.app_state.youtube_playlists.items():
                for s_data in p_songs_data:
                    yt_songs.append(Song(
                        path=s_data.get("path"),
                        filename=s_data.get("filename"),
                        title=s_data.get("title"),
                        artist=s_data.get("artist"),
                        album=s_data.get("album"),
                        duration=s_data.get("duration"),
                        format=s_data.get("format"),
                        playlist_name=s_data.get("playlist_name"),
                        is_stream=s_data.get("is_stream", True),
                        thumbnail=s_data.get("thumbnail", "")
                    ))
            return yt_songs

        # Show/hide panels
        if view_id == "queue":
            track_list.display = False
            queue_panel.display = True
            artist_panel.display = False
            youtube_panel.display = False
            queue_panel.update_queue(self.player.queue, self.player.queue_index)
            return
        
        if view_id == "artists":
            track_list.display = False
            queue_panel.display = False
            artist_panel.display = True
            youtube_panel.display = False
            # Include YT songs in artists view
            combined_songs = self.all_songs + get_all_yt_songs()
            artist_panel.update_artists(combined_songs)
            return

        if view_id == "youtube":
            track_list.display = False
            queue_panel.display = False
            artist_panel.display = False
            youtube_panel.display = True
            # Sync starred paths (all songs in all YT playlists)
            all_yt_paths = [s.path for s in get_all_yt_songs()]
            youtube_panel.set_starred(all_yt_paths)
            return

        track_list.display = True
        queue_panel.display = False
        artist_panel.display = False
        youtube_panel.display = False

        if view_id == "all":
            track_list.update_tracks(self.all_songs, "All Songs", self.app_state.favorites)
        elif view_id == "yt-playlists":
            playlist_name = self._last_yt_playlist
            if not playlist_name:
                # Fallback to Starred or first available
                yt_keys = list(self.app_state.youtube_playlists.keys())
                if "Starred" in yt_keys:
                    playlist_name = "Starred"
                elif yt_keys:
                    playlist_name = yt_keys[0]
            
            if playlist_name:
                self._show_view(f"yt_playlist:{playlist_name}")
                return
            else:
                track_list.update_tracks([], "No YouTube Playlists", self.app_state.favorites)
        elif view_id == "favorites":
            fav_songs = [s for s in self.all_songs if self.app_state.is_favorite(s.path)]
            track_list.update_tracks(fav_songs, "Favorites", self.app_state.favorites)
        elif view_id.startswith("yt_playlist:"):
            playlist_name = view_id[12:]
            self._last_yt_playlist = playlist_name
            songs_data = self.app_state.youtube_playlists.get(playlist_name, [])
            yt_songs = []
            for s_data in songs_data:
                yt_songs.append(Song(
                    path=s_data.get("path"),
                    filename=s_data.get("filename"),
                    title=s_data.get("title"),
                    artist=s_data.get("artist"),
                    album=s_data.get("album"),
                    duration=s_data.get("duration"),
                    format=s_data.get("format"),
                    playlist_name=s_data.get("playlist_name"),
                    is_stream=s_data.get("is_stream", True),
                    thumbnail=s_data.get("thumbnail", "")
                ))
            track_list.update_tracks(yt_songs, f"YT: {playlist_name}", self.app_state.favorites)
        elif view_id == "recent":
            recent_paths = self.app_state.recently_played
            recent_songs = []
            all_possible_songs = self.all_songs + get_all_yt_songs()
            for p in recent_paths:
                match = next((s for s in all_possible_songs if s.path == p), None)
                if match:
                    recent_songs.append(match)
            track_list.update_tracks(recent_songs, "Recently Played", self.app_state.favorites)
        self._highlight_current()

    # ────────────────────────────────────────────────────────────
    #  Timer tick – progress updates & track-end detection
    # ────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        # Auto-advance when track finishes
        if self.player.is_track_finished():
            self.player.next_track()

        # Refresh now-playing bar
        np_bar = self.query_one("#now-playing", NowPlayingBar)
        song = self.player.current_song
        np_bar.update_display(
            title=song.display_title if song else "",
            artist=song.display_artist if song else "",
            playlist=song.playlist_name if song else "",
            position=self.player.position,
            duration=song.duration if song else 0.0,
            is_playing=self.player.is_playing,
            is_paused=self.player.is_paused,
            shuffle=self.player.shuffle,
            repeat=self.player.repeat_mode.value,
            vol=self.player.volume,
            bass=self.player.bass_boost,
        )

    # ────────────────────────────────────────────────────────────
    #  State persistence
    # ────────────────────────────────────────────────────────────

    def _save_state(self) -> None:
        song = self.player.current_song
        self.app_state.save_playback(
            song_path=song.path if song else "",
            position=self.player.position,
            volume=self.player.volume,
            shuffle=self.player.shuffle,
            repeat=self.player.repeat_mode.value,
            bass=self.player.bass_boost,
            mid=self.player.mid_gain,
            treble=self.player.treble_gain,
            root=self.root_path,
        )

    def _restore_state(self) -> None:
        # Volume & EQ
        self.player.set_volume(self.app_state.last_volume)
        self.player.set_bass_boost(self.app_state.last_bass)
        self.player.set_mid_gain(self.app_state.last_mid)
        self.player.set_treble_gain(self.app_state.last_treble)

        if not self.root_path:
            return

        # Shuffle
        if self.app_state.last_shuffle:
            self.player.toggle_shuffle()

        # Repeat
        repeat_map = {"off": RepeatMode.OFF, "all": RepeatMode.ALL, "one": RepeatMode.ONE}
        target = repeat_map.get(self.app_state.last_repeat, RepeatMode.OFF)
        while self.player.repeat_mode != target:
            self.player.cycle_repeat()

        # Resume last song
        last_path = self.app_state.last_song_path
        if last_path:
            song = next((s for s in self.all_songs if s.path == last_path), None)
            if song:
                # Find which playlist this song belongs to and load its queue
                playlist_songs = [
                    s for s in self.all_songs if s.playlist_name == song.playlist_name
                ]
                idx = next(
                    (i for i, s in enumerate(playlist_songs) if s.path == last_path), 0
                )
                self.player.load_queue(playlist_songs, idx)
                # Update album art panel even if not playing yet
                album_art = self.query_one("#album-art", AlbumArtPanel)
                album_art.update_song(
                    song.path, 
                    song.display_title, 
                    song.display_artist,
                    thumbnail=song.thumbnail
                )
                # Don't auto-play, just load - user can press space to resume
                self.notify(f"Ready to resume: {song.display_title}", title="Playback", severity="information", timeout=NOTIFICATION_TIMEOUT)

    # ────────────────────────────────────────────────────────────
    #  Helpers
    # ────────────────────────────────────────────────────────────

    def _play_song_by_path(self, path: str) -> None:
        """Find a song by path and start playing it."""
        # Search all songs (local)
        song = next((s for s in self.all_songs if s.path == path), None)
        
        # If not found, search current track list (could be YouTube playlist)
        track_list = self.query_one("#track-list", TrackList)
        if not song:
            song = next((s for s in track_list._songs if s.path == path), None)
        
        if not song:
            return

        # Load the current view's songs as the queue
        view_songs = track_list._songs if track_list.display else self.all_songs
        if song not in view_songs:
            # If song is not in current view, maybe it's in all_songs
            if song in self.all_songs:
                view_songs = self.all_songs
            else:
                view_songs = [song]

        idx = next((i for i, s in enumerate(view_songs) if s.path == path), 0)
        self.player.load_queue(view_songs, idx)
        
        try:
            self.player.play()
            # Update state
            self.app_state.add_recent(path)
            self._highlight_current()
        except Exception as e:
            self.notify(str(e), title="Playback Error", severity="error", timeout=NOTIFICATION_TIMEOUT)

    def _highlight_current(self) -> None:
        """Sync all song list highlights with the currently-playing song."""
        song = self.player.current_song
        path = song.path if song else None
        
        self.query_one("#track-list", TrackList).highlight_playing(path)
        self.query_one("#artist-panel", ArtistPanel).highlight_playing(path)
        self.query_one("#youtube-panel", YoutubePanel).highlight_playing(path)

    def _get_selected_track_path(self) -> Optional[str]:
        """Return the path of the highlighted row in the active panel."""
        if self._current_view == "youtube":
            song = self.query_one("#youtube-panel", YoutubePanel).get_selected_song()
            return song.path if song else None
        
        if self._current_view == "artists":
            return self.query_one("#artist-panel", ArtistPanel).get_selected_path()
        
        track_list = self.query_one("#track-list", TrackList)
        return track_list._get_selected_path()

    # ────────────────────────────────────────────────────────────
    #  Message handlers (from widgets)
    # ────────────────────────────────────────────────────────────

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle tab switching."""
        if event.tab:
            self._show_view(event.tab.id)

    def on_sidebar_view_selected(self, message: Sidebar.ViewSelected) -> None:
        """Sync tabs with sidebar selection."""
        tabs = self.query_one("#nav-tabs", Tabs)
        try:
            tabs.active = message.view_id
        except Exception:
            pass
        self._show_view(message.view_id)

    def on_sidebar_library_switch(self, message: Sidebar.LibrarySwitch) -> None:
        """Switch to a different saved library (root folder)."""
        self._switch_library(message.root_path)

    def on_sidebar_library_remove_request(
        self, message: Sidebar.LibraryRemoveRequest
    ) -> None:
        """Handle request to remove a library from the saved list."""
        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                self.app_state.remove_saved_root(message.root_path)
                sidebar = self.query_one("#sidebar", Sidebar)
                sidebar.set_libraries(
                    saved_roots=self.app_state.saved_roots,
                    current_root=self.root_path,
                )
                self.notify(f"Removed from library list: {message.name}", title="Library")

        self.push_screen(
            ConfirmModal(
                message=f"Remove '{message.name}' from your library list?",
                yes_label="Remove",
                no_label="Cancel"
            ),
            callback=on_confirm
        )

    def on_track_list_track_selected(self, message: TrackList.TrackSelected) -> None:
        self._play_song_by_path(message.song_path)

    def on_track_list_track_remove_requested(self, message: TrackList.TrackRemoveRequested) -> None:
        """Handle removing a track from a YouTube playlist."""
        if self._current_view.startswith("yt_playlist:"):
            playlist_name = self._current_view[12:]
            
            def on_confirm(confirmed: bool) -> None:
                if confirmed:
                    self.app_state.remove_from_youtube_playlist(playlist_name, message.song_path)
                    self.notify(f"Removed from {playlist_name}", title="YouTube")
                    # Refresh the current view
                    self._show_view(self._current_view)
                    self._refresh_yt_panel_stars()

            self.push_screen(
                ConfirmModal(
                    message=f"Remove this song from '{playlist_name}'?",
                    yes_label="Remove",
                    no_label="Cancel"
                ),
                callback=on_confirm
            )
        else:
            self.notify("Can only remove tracks from YouTube playlists.", severity="warning")

    def on_queue_panel_queue_track_selected(
        self, message: QueuePanel.QueueTrackSelected
    ) -> None:
        song = next((s for s in self.player.queue if s.path == message.song_path), None)
        if song:
            self.player.play(song)
            self.app_state.add_recent(song.path)

    def on_queue_panel_queue_track_move_requested(
        self, message: QueuePanel.QueueTrackMoveRequested
    ) -> None:
        from_idx = message.index
        to_idx = from_idx + message.direction
        if 0 <= to_idx < len(self.player.queue):
            self.player.move_in_queue(from_idx, to_idx)
            # Refresh queue panel
            queue_panel = self.query_one("#queue-panel", QueuePanel)
            queue_panel.update_queue(self.player.queue, self.player.queue_index)
            # Maintain cursor position
            table = queue_panel.query_one("#queue-table", DataTable)
            table.move_cursor(row=to_idx)

    def on_queue_panel_queue_track_remove_requested(
        self, message: QueuePanel.QueueTrackRemoveRequested
    ) -> None:
        idx = message.index
        if 0 <= idx < len(self.player.queue):
            self.player.remove_from_queue(idx)
            # Refresh queue panel
            queue_panel = self.query_one("#queue-panel", QueuePanel)
            queue_panel.update_queue(self.player.queue, self.player.queue_index)
            # Maintain cursor position
            table = queue_panel.query_one("#queue-table", DataTable)
            new_cursor = min(idx, len(self.player.queue) - 1)
            if new_cursor >= 0:
                table.move_cursor(row=new_cursor)

    def on_artist_panel_artist_selected(
        self, message: ArtistPanel.ArtistSelected
    ) -> None:
        # Just ensure the panel is focused correctly
        self.query_one("#artist-panel", ArtistPanel).focus()

    def on_artist_panel_track_selected(
        self, message: ArtistPanel.TrackSelected
    ) -> None:
        """Handle song selection from the side-by-side artist panel."""
        self._play_song_by_path(message.song_path)

    def on_youtube_panel_youtube_track_add_to_playlist(
        self, message: YoutubePanel.YoutubeTrackAddToPlaylist
    ) -> None:
        """Handle adding a YouTube track to a playlist."""
        def on_pick(choice: str | None) -> None:
            if not choice: return
            
            playlist_name = choice
            if choice.startswith("new:"):
                playlist_name = choice[4:]
                self.app_state.create_youtube_playlist(playlist_name)
                self._refresh_sidebar()
            
            if self.app_state.add_to_youtube_playlist(playlist_name, asdict(message.song)):
                self.notify(f"Added to {playlist_name}", title="YouTube")
                self._refresh_yt_panel_stars()
            else:
                self.notify(f"Already in {playlist_name}", severity="warning")

        self.push_screen(
            YoutubePlaylistModal(
                playlists=list(self.app_state.youtube_playlists.keys()),
                song_title=message.song.display_title
            ),
            callback=on_pick
        )

    def _refresh_yt_panel_stars(self) -> None:
        try:
            yt_panel = self.query_one("#youtube-panel", YoutubePanel)
            all_yt_paths = []
            for p_songs in self.app_state.youtube_playlists.values():
                all_yt_paths.extend([s.get("path") for s in p_songs])
            yt_panel.set_starred(all_yt_paths)
        except Exception:
            pass

    def _refresh_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar", Sidebar)
        sidebar.set_libraries(
            saved_roots=self.app_state.saved_roots,
            current_root=self.root_path,
            youtube_playlists=list(self.app_state.youtube_playlists.keys()),
        )

    def on_youtube_panel_youtube_track_selected(
        self, message: YoutubePanel.YoutubeTrackSelected
    ) -> None:
        """Handle YouTube track selection from search results."""
        yt_panel = self.query_one("#youtube-panel", YoutubePanel)
        results = yt_panel._results
        if message.song in results:
            idx = results.index(message.song)
            self.player.load_queue(results, idx)
            self.player.play()
        else:
            self._play_youtube_song(message.song)

    def _on_pre_play_hook(self, song: Song) -> bool:
        """Called by player before playing. Return True to intercept."""
        if song.is_stream and ("youtube.com" in song.path or "youtu.be" in song.path):
            self._play_youtube_song(song)
            return True
        return False

    def _play_youtube_song(self, song: Song) -> None:
        """Extract stream URL and play a YouTube song."""
        # Add to recent history using the original YouTube path/URL
        self.app_state.add_recent(song.path)
        
        self.notify(f"Extracting stream for: {song.display_title}...", title="YouTube", timeout=2)
        
        def _extract_and_play():
            try:
                import yt_dlp
                ydl_opts = {
                    'format': 'ba/b',
                    'quiet': True,
                    'no_warnings': True,
                    'extractor_args': {'youtube': {'player_client': ['android_vr', 'ios', 'android', 'mweb', 'web']}}
                }
                
                if YOUTUBE_COOKIES_FROM_BROWSER:
                    ydl_opts['cookiesfrombrowser'] = (YOUTUBE_COOKIES_FROM_BROWSER,)
                elif YOUTUBE_COOKIES_FILE:
                    ydl_opts['cookiefile'] = YOUTUBE_COOKIES_FILE
                    
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(song.path, download=False)
                    
                    # Clone the song to avoid corrupting the original path in the playlist
                    new_song = Song(
                        path=info['url'],
                        filename=song.filename,
                        title=song.title,
                        artist=song.artist,
                        album=song.album,
                        duration=song.duration,
                        format=song.format,
                        playlist_name=song.playlist_name,
                        is_stream=True,
                        thumbnail=info.get('thumbnail', song.thumbnail)
                    )
                
                # Play in the main thread's player context
                def _play():
                    self.player.play(new_song, force=True)
                    self._highlight_current()
                    self.notify(f"Streaming: {new_song.display_title}", title="YouTube", severity="information", timeout=NOTIFICATION_TIMEOUT)
                
                self.app.call_from_thread(_play)
                
            except Exception as e:
                err_msg = str(e)
                if "confirm you're not a bot" in err_msg.lower():
                    err_msg = "YouTube bot detection triggered. Try setting YOUTUBE_COOKIES_FROM_BROWSER in .env"
                self.app.call_from_thread(self.notify, f"Streaming failed: {err_msg}", title="YouTube", severity="error")

        thread = threading.Thread(target=_extract_and_play)
        thread.daemon = True
        thread.start()

    def _download_for_playlist(self, playlist_name: str, song: Song) -> None:
        """Download a song locally and then add it to the playlist."""
        from .config import YT_DOWNLOADS_DIR
        YT_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

        # Extract video ID
        video_id = "unknown"
        if "v=" in song.path:
            video_id = song.path.split("v=")[1].split("&")[0]
        elif "youtu.be/" in song.path:
            video_id = song.path.split("youtu.be/")[1].split("?")[0]
        else:
            video_id = hashlib.md5(song.path.encode()).hexdigest()[:10]

        # Check if already downloaded
        local_file = None
        for ext in [".mp3", ".opus", ".m4a", ".webm", ".ogg"]:
            test_path = YT_DOWNLOADS_DIR / f"{video_id}{ext}"
            if test_path.exists():
                local_file = test_path
                break
        
        if local_file:
            song_data = asdict(song)
            song_data["path"] = str(local_file)
            song_data["is_stream"] = False
            if self.app_state.add_to_youtube_playlist(playlist_name, song_data):
                self.notify(f"Added local to {playlist_name}", title="YouTube")
                self._refresh_yt_panel_stars()
            else:
                self.notify(f"Already in {playlist_name}", severity="warning")
            return

        self.notify(f"Downloading to {playlist_name}...", title="YouTube", timeout=5)

        def _run_download():
            try:
                import yt_dlp
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': str(YT_DOWNLOADS_DIR / f'{video_id}.%(ext)s'),
                    'quiet': True,
                    'no_warnings': True,
                    'extractor_args': {'youtube': {'player_client': ['android_vr', 'ios', 'android', 'mweb', 'web']}}
                }
                
                if YOUTUBE_COOKIES_FROM_BROWSER:
                    ydl_opts['cookiesfrombrowser'] = (YOUTUBE_COOKIES_FROM_BROWSER,)
                elif YOUTUBE_COOKIES_FILE:
                    ydl_opts['cookiefile'] = YOUTUBE_COOKIES_FILE

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(song.path, download=True)
                    ext = info.get('ext', 'mp3')
                    final_path = YT_DOWNLOADS_DIR / f"{video_id}.{ext}"
                    
                    song_data = asdict(song)
                    song_data["path"] = str(final_path)
                    song_data["is_stream"] = False
                    if info.get('thumbnail'):
                        song_data["thumbnail"] = info['thumbnail']
                
                def _done():
                    if self.app_state.add_to_youtube_playlist(playlist_name, song_data):
                        self.notify(f"Downloaded & Added to {playlist_name}", title="YouTube")
                        self._refresh_yt_panel_stars()
                    else:
                        # If somehow added while downloading
                        pass

                self.app.call_from_thread(_done)
            except Exception as e:
                self.app.call_from_thread(self.notify, f"Download failed: {str(e)}", severity="error")

        threading.Thread(target=_run_download, daemon=True).start()

    def on_youtube_panel_youtube_track_add_to_playlist(
        self, message: YoutubePanel.YoutubeTrackAddToPlaylist
    ) -> None:
        """Handle adding a YouTube track to a playlist."""
        def on_pick(choice: str | None) -> None:
            if not choice: return
            
            playlist_name = choice
            if choice.startswith("new:"):
                playlist_name = choice[4:]
                self.app_state.create_youtube_playlist(playlist_name)
                self._refresh_sidebar()
            
            # Start download process before adding
            self._download_for_playlist(playlist_name, message.song)

        self.push_screen(
            YoutubePlaylistModal(
                playlists=list(self.app_state.youtube_playlists.keys()),
                song_title=message.song.display_title
            ),
            callback=on_pick
        )

    def on_sidebar_youtube_playlist_selected(self, message: Sidebar.YoutubePlaylistSelected) -> None:
        self._show_view(f"yt_playlist:{message.name}")

    def on_sidebar_new_youtube_playlist_request(self, message: Sidebar.NewYoutubePlaylistRequest) -> None:
        def on_name(name: str | None) -> None:
            if name:
                if self.app_state.create_youtube_playlist(name):
                    self.notify(f"Created playlist: {name}", title="YouTube")
                    self._refresh_sidebar()
                else:
                    self.notify(f"Playlist already exists: {name}", severity="error")

        self.push_screen(NewYoutubePlaylistModal(), callback=on_name)

    def on_sidebar_youtube_playlist_remove_request(self, message: Sidebar.YoutubePlaylistRemoveRequest) -> None:
        if message.name == "Starred":
            self.notify("Cannot delete 'Starred' playlist", severity="warning")
            return

        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                self.app_state.delete_youtube_playlist(message.name)
                self.notify(f"Deleted playlist: {message.name}", title="YouTube")
                self._refresh_sidebar()
                if self._current_view == f"yt_playlist:{message.name}":
                    self._show_view("youtube")

        self.push_screen(
            ConfirmModal(
                message=f"Delete YouTube playlist '{message.name}'?",
                yes_label="Delete",
                no_label="Cancel"
            ),
            callback=on_confirm
        )

    def on_sidebar_add_library_request(self, message: Sidebar.AddLibraryRequest) -> None:
        """Open the Add Library modal when the sidebar button is clicked."""
        self._open_add_library_modal()

    def _switch_library(self, new_root: str) -> None:
        """Stop playback, rescan a different root folder, refresh UI."""
        if new_root == self.root_path:
            return  # already here

        from pathlib import Path as P
        if not P(new_root).exists():
            self.notify(f"Folder not found: {new_root}", title="Library Error", severity="warning", timeout=NOTIFICATION_TIMEOUT)
            self.app_state.remove_saved_root(new_root)
            sidebar = self.query_one("#sidebar", Sidebar)
            sidebar.set_libraries(
                saved_roots=self.app_state.saved_roots,
                current_root=self.root_path,
            )
            return

        # Save current state before switching
        self._save_state()
        self.player.stop()

        # Switch
        self.root_path = new_root
        self._scan_library()
        name = P(new_root).name
        self.notify(f"Switched to library: {name}", title="Library Switch", severity="information", timeout=NOTIFICATION_TIMEOUT)

    # ────────────────────────────────────────────────────────────
    #  Actions (keyboard bindings)
    # ────────────────────────────────────────────────────────────

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar")
        sidebar.toggle_class("-hidden")

    def action_toggle_album_art(self) -> None:
        """Toggle the visibility of the album art/info panel."""
        art = self.query_one("#album-art")
        art.toggle_class("-hidden")

    def action_toggle_play(self) -> None:
        if self.player.state == PlayerState.STOPPED:
            if self._current_view == "youtube":
                yt_panel = self.query_one("#youtube-panel", YoutubePanel)
                song = yt_panel.get_selected_song()
                if song:
                    self.player.play(song)
                return

            if self.all_songs:
                # Nothing loaded yet – start from selected or first track
                path = self._get_selected_track_path()
                if path:
                    self._play_song_by_path(path)
                else:
                    self.player.load_queue(self.all_songs, 0)
                    self.player.play()
        else:
            self.player.toggle_pause()

    def action_next_track(self) -> None:
        self.player.next_track()
        if self.player.current_song:
            self.app_state.add_recent(self.player.current_song.path)
        self._highlight_current()

    def action_prev_track(self) -> None:
        self.player.prev_track()
        if self.player.current_song:
            self.app_state.add_recent(self.player.current_song.path)
        self._highlight_current()

    def action_toggle_shuffle(self) -> None:
        self.player.toggle_shuffle()
        state = "ON" if self.player.shuffle else "OFF"
        self.notify(f"Shuffle: {state}", title="Playback", severity="information", timeout=NOTIFICATION_TIMEOUT)

    def action_cycle_repeat(self) -> None:
        self.player.cycle_repeat()
        mode = self.player.repeat_mode.value.upper()
        self.notify(f"Repeat: {mode}", title="Playback", severity="information", timeout=NOTIFICATION_TIMEOUT)

    def action_seek_fwd(self) -> None:
        self.player.seek_relative(SEEK_STEP)

    def action_seek_bwd(self) -> None:
        self.player.seek_relative(-SEEK_STEP)

    def action_vol_up(self) -> None:
        self.player.volume_up()

    def action_vol_down(self) -> None:
        self.player.volume_down()

    def action_open_audio_settings(self) -> None:
        self.push_screen(AudioSettingsModal(self.player))

    def action_open_search(self) -> None:
        def on_result(path: Optional[str]) -> None:
            if path:
                self._play_song_by_path(path)

        self.push_screen(SearchModal(self.all_songs), callback=on_result)

    def action_toggle_fav(self) -> None:
        if self._current_view == "youtube":
            yt_panel = self.query_one("#youtube-panel", YoutubePanel)
            song = yt_panel.get_selected_song()
            if song:
                self.on_youtube_panel_youtube_track_add_to_playlist(
                    YoutubePanel.YoutubeTrackAddToPlaylist(song)
                )
            return

        path = self._get_selected_track_path()
        if not path:
            # Try currently playing
            if self.player.current_song:
                path = self.player.current_song.path
        
        if path:
            if self._current_view.startswith("yt_playlist:"):
                track_list = self.query_one("#track-list", TrackList)
                song = next((s for s in track_list._songs if s.path == path), None)
                if song:
                    self.on_youtube_panel_youtube_track_add_to_playlist(
                        YoutubePanel.YoutubeTrackAddToPlaylist(song)
                    )
                return

            is_fav = self.app_state.toggle_favorite(path)
            song = next((s for s in self.all_songs if s.path == path), None)
            name = song.display_title if song else "Track"
            if is_fav:
                self.notify(f"Added to favorites: {name}", title="Favorites", severity="information", timeout=NOTIFICATION_TIMEOUT)
            else:
                self.notify(f"Removed from favorites: {name}", title="Favorites", severity="information", timeout=NOTIFICATION_TIMEOUT)
            # Refresh view
            track_list = self.query_one("#track-list", TrackList)
            track_list.set_favorites(self.app_state.favorites)
            if self._current_view == "favorites":
                self._show_view("favorites")

    def action_add_library(self) -> None:
        """Open the Add Library modal (keyboard shortcut)."""
        self._open_add_library_modal()

    def _open_add_library_modal(self) -> None:
        """Show the Add Library modal and handle the result."""
        def on_result(path: Optional[str]) -> None:
            if path:
                self._switch_library(path)

        self.push_screen(AddLibraryModal(), callback=on_result)

    def action_add_to_queue(self) -> None:
        path = self._get_selected_track_path()
        if path:
            # Check local library first
            song = next((s for s in self.all_songs if s.path == path), None)
            
            # If not in local library, check current track list (could be YT playlist or Recent)
            if not song:
                track_list = self.query_one("#track-list", TrackList)
                song = next((s for s in track_list._songs if s.path == path), None)
            
            # Also check YouTube panel search results
            if not song and self._current_view == "youtube":
                yt_panel = self.query_one("#youtube-panel", YoutubePanel)
                song = next((s for s in yt_panel._results if s.path == path), None)

            if song:
                self.player.add_to_queue(song)
                self.notify(f"Added to queue: {song.display_title}", title="Queue", severity="information", timeout=NOTIFICATION_TIMEOUT)
                if self._current_view == "queue":
                    self.query_one("#queue-panel", QueuePanel).update_queue(self.player.queue, self.player.queue_index)

    def action_sort_title(self) -> None:
        self.query_one("#track-list", TrackList).sort_by("title")

    def action_sort_artist(self) -> None:
        self.query_one("#track-list", TrackList).sort_by("artist")

    def action_sort_album(self) -> None:
        self.query_one("#track-list", TrackList).sort_by("album")

    def action_sort_duration(self) -> None:
        self.query_one("#track-list", TrackList).sort_by("duration")

    def action_sort_type(self) -> None:
        self.query_one("#track-list", TrackList).sort_by("type")

    def action_quit_app(self) -> None:
        self._save_state()
        self.player.cleanup()
        self.exit()

    def action_go_back(self) -> None:
        """Return to artist list if currently viewing an artist's songs."""
        if self._current_view.startswith("artist:"):
            self._show_view("artists")

    def action_next_tab(self) -> None:
        """Switch to the next available tab."""
        tabs = self.query_one("#nav-tabs", Tabs)
        if tabs.active_tab:
            # Simple list of main tab IDs
            ids = ["all", "artists", "youtube", "yt-playlists", "favorites", "recent", "queue"]
            try:
                idx = ids.index(tabs.active_tab.id)
                next_id = ids[(idx + 1) % len(ids)]
                tabs.active = next_id
                self._show_view(next_id)
            except ValueError:
                tabs.active = "all"
                self._show_view("all")

    def action_prev_tab(self) -> None:
        """Switch to the previous available tab."""
        tabs = self.query_one("#nav-tabs", Tabs)
        if tabs.active_tab:
            ids = ["all", "artists", "youtube", "yt-playlists", "favorites", "recent", "queue"]
            try:
                idx = ids.index(tabs.active_tab.id)
                prev_id = ids[(idx - 1) % len(ids)]
                tabs.active = prev_id
                self._show_view(prev_id)
            except ValueError:
                tabs.active = "all"
                self._show_view("all")
