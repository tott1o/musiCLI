"""
Sidebar widget – navigation and saved libraries.

Shows navigation items (All Songs, Favorites, Recent, Queue)
and saved libraries (previously accessed root folders).
"""

from __future__ import annotations

from typing import List

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Static, OptionList
from textual.widgets.option_list import Option

from ..utils import truncate
from ..theme import (
    ACCENT, BG_DEEPEST, BG_ELEVATED, BG_HIGHLIGHT, BORDER,
    TEXT_SECONDARY,
)


class Sidebar(Vertical):
    """Left-hand navigation panel."""

    class ViewSelected(Message):
        """Posted when the user picks a navigation item."""

        def __init__(self, view_id: str) -> None:
            super().__init__()
            self.view_id = view_id

    class LibrarySwitch(Message):
        """Posted when the user wants to switch to a saved library."""

        def __init__(self, root_path: str) -> None:
            super().__init__()
            self.root_path = root_path

    class LibraryRemoveRequest(Message):
        """Posted when the user wants to remove a saved library."""

        def __init__(self, root_path: str, name: str) -> None:
            super().__init__()
            self.root_path = root_path
            self.name = name

    class AddLibraryRequest(Message):
        """Posted when the user clicks '+ Add Library'."""

    class YoutubePlaylistSelected(Message):
        """Posted when a YouTube playlist is picked from the sidebar."""
        def __init__(self, name: str) -> None:
            super().__init__()
            self.name = name

    class NewYoutubePlaylistRequest(Message):
        """Posted when user clicks '+ New YT Playlist'."""

    class YoutubePlaylistRemoveRequest(Message):
        """Posted when user wants to delete a YT playlist."""
        def __init__(self, name: str) -> None:
            super().__init__()
            self.name = name

    DEFAULT_CSS = f"""
    Sidebar {{
        width: 30;
        background: {BG_DEEPEST};
        border-right: solid {BORDER};
        padding: 0;
        overflow-x: hidden;
    }}
    Sidebar:focus-within {{
        border-right: solid {ACCENT};
    }}
    Sidebar #sidebar-title {{
        width: 100%;
        padding: 1 2;
        color: {ACCENT};
        text-style: bold;
        text-align: center;
        border-bottom: solid {BORDER};
    }}
    Sidebar OptionList {{
        background: transparent;
        scrollbar-size: 1 1;
        padding: 0 1;
        border: none;
        height: 1fr;
    }}
    Sidebar OptionList:focus {{
        border: none;
    }}
    Sidebar OptionList > .option-list--option-highlighted {{
        background: {BG_HIGHLIGHT};
        color: {ACCENT};
        text-style: bold;
    }}
    Sidebar OptionList > .option-list--option-hover {{
        background: {BG_ELEVATED};
    }}
    """

    BINDINGS = [
        Binding("delete", "remove_library", "Remove", show=False),
        Binding("x", "remove_library", "Remove", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Static("[bold]musiCLI >_<[/bold]", id="sidebar-title")
        yield OptionList(

            Option(" ALL SONGS", id="all"),
            Option(" ARTISTS", id="artists"),
            Option(" YOUTUBE", id="youtube"),
            Option(" YT-PLAYLISTS", id="yt-playlists"),
            Option(" FAVORITES", id="favorites"),
            Option(" RECENT", id="recent"),
            Option(" QUEUE", id="queue"),
            Option("", disabled=True),
            Option("  YouTube Playlists", id="_label_yt_playlists", disabled=True),
            Option(f"  [bold {ACCENT}]＋ new playlist[/]", id="new_yt_playlist"),
            Option("", disabled=True),
            Option("  LIBRARIES", id="_label_libraries", disabled=True),
            id="nav-list",
        )

    # ── Public API ──────────────────────────────────────────────

    def set_libraries(
        self,
        saved_roots: List[dict] | None = None,
        current_root: str = "",
        youtube_playlists: List[str] | None = None,
    ) -> None:
        """Rebuild the sidebar list with saved libraries and YT playlists."""
        self._saved_roots_data = saved_roots or []  # Store for lookup
        self._youtube_playlists = youtube_playlists or []
        nav = self.query_one("#nav-list", OptionList)
        
        # Remember what was highlighted
        highlighted_id = None
        if nav.highlighted is not None:
            try:
                opt = nav.get_option_at_index(nav.highlighted)
                highlighted_id = opt.id
            except Exception:
                pass

        nav.clear_options()

        # Navigation
        nav.add_option(Option("  ALL-SONGS", id="all"))
        nav.add_option(Option("  ARTISTS", id="artists"))
        nav.add_option(Option("  YOUTUBE", id="youtube"))
        nav.add_option(Option("  YT-PLAYLISTS", id="yt-playlists"))
        nav.add_option(Option("  FAVORITES", id="favorites"))
        nav.add_option(Option("  RECENT", id="recent"))
        nav.add_option(Option("  QUEUE", id="queue"))
        nav.add_option(Option("", disabled=True))

        # YouTube Playlists
        nav.add_option(Option("  YOUTUBE-PLAYLISTS", id="_label_yt_playlists", disabled=True))
        for yt_p in sorted(self._youtube_playlists):
            nav.add_option(Option(f"    {truncate(yt_p, 22)}", id=f"yt_playlist:{yt_p}"))
        nav.add_option(Option(f"  [bold {ACCENT}]＋ new playlist[/]", id="new_yt_playlist"))
        nav.add_option(Option("", disabled=True))

        # Libraries
        nav.add_option(Option("  LIBRARIES", id="_label_libraries", disabled=True))
        
        # Sort libraries alphabetically for a "still" UI
        sorted_roots = sorted(self._saved_roots_data, key=lambda x: x.get("name", "").lower())
        
        if sorted_roots:
            for root in sorted_roots:
                name = root.get("name", "Unknown")
                path = root.get("path", "")
                
                # Truncate library name if it's too long for the sidebar
                display_name = truncate(name, 22)
                
                # Use a different icon/style for the current active library
                if path == current_root:
                    label = f"  [bold {ACCENT}]● {display_name}[/]"
                else:
                    label = f"    {display_name}"
                
                nav.add_option(Option(label, id=f"library:{path}"))

        # Add Library button
        nav.add_option(Option(f"  [bold {ACCENT}]＋ add Library[/]", id="add_library"))

        # Restore highlight if possible
        if highlighted_id:
            try:
                nav.highlighted = nav.get_option_index(highlighted_id)
            except Exception:
                pass

    # ── Actions ─────────────────────────────────────────────────

    def action_remove_library(self) -> None:
        """Triggered by keybinding to remove a highlighted library or YT playlist."""
        nav = self.query_one("#nav-list", OptionList)
        if nav.highlighted is None:
            return

        option = nav.get_option_at_index(nav.highlighted)
        option_id = str(option.id)

        if option_id.startswith("library:"):
            root_path = option_id[8:]
            # Find name from our stored data
            name = "Unknown Library"
            for r in self._saved_roots_data:
                if r.get("path") == root_path:
                    name = r.get("name", "Unknown")
                    break
            self.post_message(self.LibraryRemoveRequest(root_path, name))
        elif option_id.startswith("yt_playlist:"):
            name = option_id[12:]
            self.post_message(self.YoutubePlaylistRemoveRequest(name))

    # ── Events ──────────────────────────────────────────────────

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        option_id = str(event.option_id)
        if not option_id or option_id.startswith("_label_"):
            return  # ignore section headers

        if option_id == "add_library":
            self.post_message(self.AddLibraryRequest())
        elif option_id == "new_yt_playlist":
            self.post_message(self.NewYoutubePlaylistRequest())
        elif option_id.startswith("yt_playlist:"):
            name = option_id[12:]
            self.post_message(self.YoutubePlaylistSelected(name))
        elif option_id.startswith("library:"):
            root_path = option_id[8:]
            self.post_message(self.LibrarySwitch(root_path))
        else:
            self.post_message(self.ViewSelected(option_id))
