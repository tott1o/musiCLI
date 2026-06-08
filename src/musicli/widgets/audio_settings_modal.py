"""
Audio Settings modal – Equalizer and Volume controls with Presets.
"""

from __future__ import annotations

from typing import Optional, List

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, Grid, Container
from textual.screen import ModalScreen
from textual.widgets import Static, Button

from ..utils import modern_bar
from ..theme import (
    ACCENT, BG_PRIMARY, BG_ELEVATED, BG_SURFACE, BG_BUTTON,
    TEXT_PRIMARY, TEXT_SECONDARY, BORDER,
)


class AudioSettingsModal(ModalScreen[None]):
    """A compact Audio Settings modal with Done and Cancel buttons."""

    BINDINGS = [
        ("escape", "dismiss(None)", "Cancel"),
    ]

    DEFAULT_CSS = f"""
    AudioSettingsModal {{
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }}
    #audio-container {{
        width: 82;
        height: auto;
        background: {BG_SURFACE};
        border: solid {ACCENT};
        padding: 0 2;
    }}
    #audio-header {{
        width: 100%;
        color: {ACCENT};
        text-style: bold;
        text-align: center;
        margin: 1 0;
    }}

    /* ── Layout ────────────────────────────────────────────── */
    #audio-body {{
        layout: horizontal;
        height: auto;
    }}
    #presets-column {{
        width: 32;
        border-right: solid {BORDER};
        padding-right: 1;
        height: 20;
    }}
    #tuning-column {{
        width: 1fr;
        padding-left: 2;
        height: 20;
    }}

    /* ── Presets ───────────────────────────────────────────── */
    .section-title {{
        color: {ACCENT};
        text-style: bold;
        margin-bottom: 1;
        width: 100%;
        text-align: center;
        background: {BG_ELEVATED};
    }}
    #presets-grid {{
        grid-size: 2;
        grid-gutter: 1 1;
        height: auto;
    }}
    .preset-btn {{
        width: 100%;
        height: 3;
        margin-bottom: 0;
        background: {BG_ELEVATED};
        color: {TEXT_SECONDARY};
        border: none;
    }}
    .preset-btn:hover {{
        background: {BG_BUTTON};
        color: {TEXT_PRIMARY};
    }}
    .preset-btn.-active {{
        background: {ACCENT};
        color: {BG_PRIMARY};
        text-style: bold;
    }}

    /* ── Tuning ────────────────────────────────────────────── */
    .tuning-row {{
        width: 100%;
        height: 3;
        align: center middle;
        margin-bottom: 1;
    }}
    .tuning-label {{
        width: 10;
        color: {TEXT_SECONDARY};
        text-style: bold;
    }}
    .tuning-val {{
        width: 5;
        color: {ACCENT};
        text-align: right;
        text-style: bold;
    }}
    .adj-btn {{
        width: 3;
        min-width: 3;
        height: 1;
        background: {BG_BUTTON};
        color: {TEXT_PRIMARY};
        border: none;
    }}
    .adj-btn:hover {{
        background: {ACCENT};
        color: {BG_PRIMARY};
    }}
    .tuning-bar {{
        width: 1fr;
        content-align: center middle;
        margin: 0 1;
    }}

    /* ── Footer ────────────────────────────────────────────── */
    #audio-buttons {{
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
    }}
    #audio-buttons Button {{
        margin: 0 1;
        width: 15;
    }}
    #btn-done {{
        background: {ACCENT};
        color: {BG_PRIMARY};
        text-style: bold;
        border: none;
    }}
    #btn-cancel {{
        background: {BG_ELEVATED};
        color: {TEXT_SECONDARY};
        border: none;
    }}
    """

    def __init__(self, player, **kwargs) -> None:
        super().__init__(**kwargs)
        self.player = player
        self.preset_names = self.player.get_presets()
        # Filter popular presets
        self.popular_indices = [0, 1, 11, 13, 3, 4, 17, 12] 
        self.active_preset_idx: Optional[int] = None

    def compose(self) -> ComposeResult:
        with Vertical(id="audio-container"):
            yield Static("AUDIO SETTINGS", id="audio-header")
            
            with Horizontal(id="audio-body"):
                # Left: Presets
                with Vertical(id="presets-column"):
                    yield Static(" PRESET MODES ", classes="section-title")
                    with Grid(id="presets-grid"):
                        for idx in self.popular_indices:
                            name = self.preset_names[idx].upper() if idx < len(self.preset_names) else f"PRESET {idx}"
                            yield Button(name, id=f"preset-{idx}", classes="preset-btn")

                # Right: Fine Tuning
                with Vertical(id="tuning-column"):
                    yield Static(" FINE TUNING ", classes="section-title")
                    
                    # Volume
                    with Horizontal(classes="tuning-row"):
                        yield Static("VOL", classes="tuning-label")
                        yield Button("-", id="vol-down", classes="adj-btn")
                        yield Static("", id="tune-vol-bar", classes="tuning-bar")
                        yield Button("+", id="vol-up", classes="adj-btn")
                        yield Static("0%", id="tune-vol-val", classes="tuning-val")

                    # Bass
                    with Horizontal(classes="tuning-row"):
                        yield Static("BASS", classes="tuning-label")
                        yield Button("-", id="bass-down", classes="adj-btn")
                        yield Static("", id="tune-bass-bar", classes="tuning-bar")
                        yield Button("+", id="bass-up", classes="adj-btn")
                        yield Static("0%", id="tune-bass-val", classes="tuning-val")

                    # Mids
                    with Horizontal(classes="tuning-row"):
                        yield Static("MIDS", classes="tuning-label")
                        yield Button("-", id="mid-down", classes="adj-btn")
                        yield Static("", id="tune-mid-bar", classes="tuning-bar")
                        yield Button("+", id="mid-up", classes="adj-btn")
                        yield Static("0%", id="tune-mid-val", classes="tuning-val")

                    # Treble
                    with Horizontal(classes="tuning-row"):
                        yield Static("TREBLE", classes="tuning-label")
                        yield Button("-", id="treble-down", classes="adj-btn")
                        yield Static("", id="tune-treble-bar", classes="tuning-bar")
                        yield Button("+", id="treble-up", classes="adj-btn")
                        yield Static("0%", id="tune-treble-val", classes="tuning-val")

            with Horizontal(id="audio-buttons"):
                yield Button("Cancel", id="btn-cancel")
                yield Button("Done", id="btn-done")

    def on_mount(self) -> None:
        self._update_all()

    def _update_all(self) -> None:
        # Volume
        self.query_one("#tune-vol-bar", Static).update(modern_bar(self.player.volume, 18))
        self.query_one("#tune-vol-val", Static).update(f"{int(self.player.volume * 100)}%")
        
        # Bass
        self.query_one("#tune-bass-bar", Static).update(modern_bar(self.player.bass_boost, 18))
        self.query_one("#tune-bass-val", Static).update(f"{int(self.player.bass_boost * 100)}%")
        
        # Mids
        self.query_one("#tune-mid-bar", Static).update(modern_bar(self.player.mid_gain, 18))
        self.query_one("#tune-mid-val", Static).update(f"{int(self.player.mid_gain * 100)}%")
        
        # Treble
        self.query_one("#tune-treble-bar", Static).update(modern_bar(self.player.treble_gain, 18))
        self.query_one("#tune-treble-val", Static).update(f"{int(self.player.treble_gain * 100)}%")
        
        for idx in self.popular_indices:
            try:
                btn = self.query_one(f"#preset-{idx}", Button)
                is_active = (idx == self.active_preset_idx)
                btn.set_class(is_active, "-active")
                # Add indicator to label
                name = self.preset_names[idx].upper() if idx < len(self.preset_names) else f"PRESET {idx}"
                btn.label = f"• {name}" if is_active else name
            except Exception:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "btn-done":
            self.dismiss()
            return
        elif bid == "btn-cancel":
            self.dismiss()
            return
            
        if not bid: return
        
        step = 0.05
        
        if bid.startswith("preset-"):
            idx = int(bid.split("-")[1])
            self.player.apply_preset(idx)
            self.active_preset_idx = idx
            self.app.notify(f"Equalizer: {self.preset_names[idx]}", title="Audio")
        elif bid == "vol-up":
            self.player.volume_up(step)
        elif bid == "vol-down":
            self.player.volume_down(step)
        elif bid == "bass-up":
            self.active_preset_idx = None
            self.player.set_bass_boost(self.player.bass_boost + step * 2)
        elif bid == "bass-down":
            self.active_preset_idx = None
            self.player.set_bass_boost(self.player.bass_boost - step * 2)
        elif bid == "mid-up":
            self.active_preset_idx = None
            self.player.set_mid_gain(self.player.mid_gain + step * 2)
        elif bid == "mid-down":
            self.active_preset_idx = None
            self.player.set_mid_gain(self.player.mid_gain - step * 2)
        elif bid == "treble-up":
            self.active_preset_idx = None
            self.player.set_treble_gain(self.player.treble_gain + step * 2)
        elif bid == "treble-down":
            self.active_preset_idx = None
            self.player.set_treble_gain(self.player.treble_gain - step * 2)
            
        self._update_all()
