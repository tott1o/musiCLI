"""
Modal for creating a new YouTube playlist.
"""

from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Input, Static, Button

from ..theme import (
    YT_ACCENT, BG_ELEVATED, BG_SURFACE, BORDER,
    TEXT_PRIMARY, TEXT_SECONDARY,
)


class NewYoutubePlaylistModal(ModalScreen[Optional[str]]):
    """A pop-up modal for creating a new YouTube playlist."""

    BINDINGS = [
        ("escape", "dismiss(None)", "Cancel"),
    ]

    DEFAULT_CSS = f"""
    NewYoutubePlaylistModal {{
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }}
    #new-yt-playlist-container {{
        width: 60;
        height: auto;
        background: {BG_SURFACE};
        border: solid {YT_ACCENT};
        padding: 1 2;
    }}
    #new-yt-playlist-header {{
        width: 100%;
        color: {YT_ACCENT};
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }}
    #new-yt-playlist-help {{
        width: 100%;
        color: {TEXT_SECONDARY};
        margin-bottom: 1;
        text-align: center;
    }}
    NewYoutubePlaylistModal Input {{
        width: 100%;
        background: {BG_ELEVATED};
        border: solid {BORDER};
        color: {TEXT_PRIMARY};
        margin-bottom: 1;
    }}
    NewYoutubePlaylistModal Input:focus {{
        border: solid {YT_ACCENT};
    }}
    #new-yt-playlist-buttons {{
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
    }}
    #new-yt-playlist-buttons Button {{
        margin: 0 1;
        width: 15;
    }}
    #btn-create {{
        background: {YT_ACCENT};
        color: {TEXT_PRIMARY};
        text-style: bold;
        border: none;
    }}
    #btn-cancel {{
        background: {BG_ELEVATED};
        color: {TEXT_SECONDARY};
        border: none;
    }}
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="new-yt-playlist-container"):
            yield Static("new youtube playlist", id="new-yt-playlist-header")
            yield Static("Enter a name for your new collection.", id="new-yt-playlist-help")
            yield Input(placeholder="e.g. Chill Beats, Gym Mix...", id="playlist-name-input")
            with Horizontal(id="new-yt-playlist-buttons"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Create", variant="success", id="btn-create")

    def on_mount(self) -> None:
        self.query_one("#playlist-name-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-create":
            self._submit()
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit()

    def _submit(self) -> None:
        name = self.query_one("#playlist-name-input", Input).value.strip()
        if not name:
            return
        self.dismiss(name)
