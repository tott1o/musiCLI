"""
Modal for adding a YouTube song to a playlist.
"""

from __future__ import annotations

from typing import List

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Static, OptionList, Input
from textual.widgets.option_list import Option
from textual import on

from ..theme import (
    YT_ACCENT, BG_ELEVATED, BG_SURFACE, BORDER,
    TEXT_PRIMARY, TEXT_SECONDARY,
)


class YoutubePlaylistModal(ModalScreen[str]):
    """Dialog to pick a YouTube playlist or create a new one."""

    DEFAULT_CSS = f"""
    YoutubePlaylistModal {{
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }}

    #yt-playlist-panel {{
        width: 60;
        height: auto;
        max-height: 80%;
        background: {BG_SURFACE};
        border: solid {YT_ACCENT};
        padding: 1 2;
    }}

    #yt-playlist-title {{
        width: 100%;
        text-align: center;
        text-style: bold;
        margin-bottom: 0;
        color: {YT_ACCENT};
    }}

    #yt-song-title {{
        width: 100%;
        text-align: center;
        color: {TEXT_SECONDARY};
        margin-bottom: 1;
    }}

    #yt-playlist-list {{
        background: {BG_ELEVATED};
        height: auto;
        max-height: 12;
        border: solid {BORDER};
        margin-bottom: 1;
    }}

    #yt-playlist-list:focus {{
        border: solid {YT_ACCENT};
    }}

    #yt-new-playlist-input {{
        background: {BG_ELEVATED};
        border: solid {BORDER};
        color: {TEXT_PRIMARY};
        margin-bottom: 1;
    }}

    #yt-new-playlist-input:focus {{
        border: solid {YT_ACCENT};
    }}

    #yt-playlist-buttons {{
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
    }}

    #yt-playlist-buttons Button {{
        margin: 0 1;
        width: 15;
    }}

    #btn-cancel {{
        background: {BG_ELEVATED};
        color: {TEXT_SECONDARY};
        border: none;
    }}
    """

    def __init__(
        self,
        playlists: List[str],
        song_title: str = "",
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.playlists = playlists
        self.song_title = song_title

    def compose(self) -> ComposeResult:
        with Vertical(id="yt-playlist-panel"):
            yield Static(f"Add to Playlist", id="yt-playlist-title")
            yield Static(f"[italic]{self.song_title}[/]", id="yt-song-title")
            
            yield OptionList(
                *[Option(f"  {p}", id=p) for p in self.playlists],
                id="yt-playlist-list"
            )
            
            yield Input(placeholder="Or create new playlist...", id="yt-new-playlist-input")
            
            with Horizontal(id="yt-playlist-buttons"):
                yield Button("Cancel", id="btn-cancel")

    def on_mount(self) -> None:
        if self.playlists:
            self.query_one("#yt-playlist-list").focus()
        else:
            self.query_one("#yt-new-playlist-input").focus()

    @on(OptionList.OptionSelected, "#yt-playlist-list")
    def on_playlist_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_id:
            self.dismiss(str(event.option_id))

    @on(Input.Submitted, "#yt-new-playlist-input")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        name = event.value.strip()
        if name:
            self.dismiss(f"new:{name}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss("")
