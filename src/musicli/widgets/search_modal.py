"""
Search modal – find songs by title, artist, or album.
"""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from ..theme import (
    ACCENT, BG_PRIMARY, BG_ELEVATED, BG_SURFACE, BG_HOVER, BORDER,
    TEXT_PRIMARY, TEXT_SECONDARY,
)

if TYPE_CHECKING:
    from ..models import Song


class SearchModal(ModalScreen[Optional[str]]):
    """A pop-up modal for searching the music library."""

    BINDINGS = [
        ("escape", "dismiss(None)", "Cancel"),
    ]

    DEFAULT_CSS = f"""
    SearchModal {{
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }}
    #search-container {{
        width: 80;
        height: 30;
        background: {BG_SURFACE};
        border: solid {ACCENT};
        padding: 1 2;
    }}
    #search-header {{
        width: 100%;
        color: {ACCENT};
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }}
    SearchModal Input {{
        width: 100%;
        background: {BG_ELEVATED};
        border: solid {BORDER};
        color: {TEXT_PRIMARY};
        margin-bottom: 1;
    }}
    SearchModal Input:focus {{
        border: solid {ACCENT};
    }}
    SearchModal OptionList {{
        background: {BG_PRIMARY};
        height: 1fr;
        border: solid {BORDER};
    }}
    SearchModal OptionList > .option-list--option-highlighted {{
        background: {BG_HOVER};
        color: {ACCENT};
    }}
    #search-footer {{
        width: 100%;
        color: {TEXT_SECONDARY};
        text-align: center;
        margin-top: 1;
    }}
    """

    def __init__(self, all_songs: List[Song], **kwargs) -> None:
        super().__init__(**kwargs)
        self.all_songs = all_songs
        self._results: List[Song] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="search-container"):
            yield Static("SEARCH LIBRARY", id="search-header")
            yield Input(placeholder="Type to search title, artist, or album...", id="search-input")
            yield OptionList(id="search-results")
            yield Static("[ENTER] Play  [ESC] Cancel", id="search-footer")

    def on_mount(self) -> None:
        self.query_one("#search-input", Input).focus()
        self._update_results("")

    def on_input_changed(self, event: Input.Changed) -> None:
        self._update_results(event.value)

    def _update_results(self, query: str) -> None:
        ol = self.query_one("#search-results", OptionList)
        ol.clear_options()

        if not query:
            self._results = self.all_songs[:50]  # Show some recent or first 50
        else:
            self._results = [s for s in self.all_songs if s.matches_query(query)]

        for i, s in enumerate(self._results):
            label = f"{s.display_title} - {s.display_artist}"
            ol.add_option(Option(label, id=str(i)))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        idx = int(str(event.option_id))
        if 0 <= idx < len(self._results):
            self.dismiss(self._results[idx].path)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        ol = self.query_one("#search-results", OptionList)
        if ol.highlighted is not None:
            idx = int(str(ol.get_option_at_index(ol.highlighted).id))
            self.dismiss(self._results[idx].path)
        elif self._results:
            self.dismiss(self._results[0].path)

    def action_cancel(self) -> None:
        self.dismiss(None)
