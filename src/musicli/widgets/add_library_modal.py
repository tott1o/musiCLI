"""
Add Library modal – pick a new root folder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pyperclip
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from ..theme import (
    ACCENT,
    BG_BUTTON,
    BG_ELEVATED,
    BG_PRIMARY,
    BG_SURFACE,
    BORDER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class AddLibraryModal(ModalScreen[Optional[str]]):
    """A pop-up modal for adding a new music library folder."""

    BINDINGS = [
        ("escape", "dismiss(None)", "Cancel"),
        ("ctrl+v", "paste_from_clipboard", "Paste"),
    ]

    DEFAULT_CSS = f"""
    AddLibraryModal {{
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }}
    #add-lib-container {{
        width: 70;
        height: auto;
        background: {BG_SURFACE};
        border: solid {ACCENT};
        padding: 1 2;
    }}
    #add-lib-header {{
        width: 100%;
        color: {ACCENT};
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }}
    #add-lib-help {{
        width: 100%;
        color: {TEXT_SECONDARY};
        margin-bottom: 1;
        text-align: center;
    }}
    AddLibraryModal Input {{
        width: 100%;
        background: {BG_ELEVATED};
        border: solid {BORDER};
        color: {TEXT_PRIMARY};
        margin-bottom: 1;
    }}
    AddLibraryModal Input:focus {{
        border: solid {ACCENT};
    }}
    #add-lib-buttons {{
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
    }}
    #add-lib-buttons Button {{
        margin: 0 1;
        width: 15;
    }}
    #btn-add {{
        background: {ACCENT};
        color: {BG_PRIMARY};
        text-style: bold;
        border: none;
    }}
    #btn-paste {{
        background: {BG_BUTTON};
        color: {TEXT_PRIMARY};
        border: none;
    }}
    #btn-cancel {{
        background: {BG_ELEVATED};
        color: {TEXT_SECONDARY};
        border: none;
    }}
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="add-lib-container"):
            yield Static("ADD MUSIC LIBRARY", id="add-lib-header")
            yield Static("Enter the absolute path to your music folder.", id="add-lib-help")
            yield Input(placeholder="C:\\Users\\...\\Music", id="lib-path-input")
            with Horizontal(id="add-lib-buttons"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Paste", variant="primary", id="btn-paste")
                yield Button("Add Folder", variant="success", id="btn-add")

    def on_mount(self) -> None:
        self.query_one("#lib-path-input", Input).focus()

    def action_paste_from_clipboard(self) -> None:
        """Paste text from system clipboard into the input field."""
        try:
            text = pyperclip.paste()
            if text:
                input_widget = self.query_one("#lib-path-input", Input)
                input_widget.value = text
                input_widget.focus()
                self.app.notify("Pasted from clipboard", title="Library", timeout=1.0)
        except Exception as e:
            self.app.notify(f"Could not paste: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-add":
            self._submit()
        elif event.button.id == "btn-paste":
            self.action_paste_from_clipboard()
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit()

    def _submit(self) -> None:
        path_str = self.query_one("#lib-path-input", Input).value.strip()
        if not path_str:
            return

        path = Path(path_str)
        if not path.exists() or not path.is_dir():
            self.app.notify("Invalid folder path. Please check and try again.", title="Library Error", severity="error")
            return

        self.dismiss(str(path.resolve()))
