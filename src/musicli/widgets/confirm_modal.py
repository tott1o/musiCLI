"""
Confirmation modal for MusiCLI.

A simple Yes/No dialog for destructive actions.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from ..theme import ACCENT, BG_ELEVATED, BG_HOVER, DANGER_BG, ERROR


class ConfirmModal(ModalScreen[bool]):
    """A simple confirmation dialog."""

    DEFAULT_CSS = f"""
    ConfirmModal {{
        align: center middle;
    }}

    #confirm-panel {{
        width: 50;
        height: auto;
        background: {BG_ELEVATED};
        border: thick {ACCENT};
        padding: 1 2;
    }}

    #confirm-message {{
        width: 100%;
        content-align: center middle;
        margin-bottom: 1;
    }}

    #confirm-buttons {{
        width: 100%;
        height: 3;
        align: center middle;
    }}

    #confirm-buttons Button {{
        margin: 0 1;
    }}

    #btn-yes {{
        background: {DANGER_BG};
        color: {ERROR};
        border: tall {ERROR};
    }}

    #btn-no {{
        background: {BG_HOVER};
        color: {ACCENT};
        border: tall {ACCENT};
    }}
    """

    def __init__(
        self,
        message: str = "Are you sure?",
        yes_label: str = "Yes",
        no_label: str = "No",
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.message = message
        self.yes_label = yes_label
        self.no_label = no_label

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-panel"):
            yield Static(self.message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button(self.yes_label, variant="error", id="btn-yes")
                yield Button(self.no_label, variant="primary", id="btn-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)
