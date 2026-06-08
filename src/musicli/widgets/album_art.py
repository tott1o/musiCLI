"""
Album art and lyrics panel — idiomatic Textual implementation with high-quality images.

Design decisions
----------------
* ``textual-image`` is used for album art rendering. This provides high-resolution
  output (Kitty, Sixel, iTerm2) on supported terminals, falling back to
  half-blocks elsewhere.
* ``reactive`` attributes own all mutable state. ``watch_`` methods are the
  single place that push state changes into the DOM.
* ``@work(exclusive=True, thread=True)`` for lyrics: Textual automatically
  cancels the previous worker when a new song starts.
* Image is square-cropped before display to ensure it fills the container perfectly.
"""

from __future__ import annotations

import io
import os
import re
import logging
from typing import Optional

from textual import work
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.widgets import Static
from tinytag import TinyTag
from PIL import Image, ImageOps
import syncedlyrics
import logging

# Suppress loud traceback and connection logs from underlying libraries
logging.getLogger("textual_image").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("syncedlyrics").setLevel(logging.CRITICAL)

from textual_image.widget import Image as TermImageWidget

from ..utils import resolve_resource, truncate
from ..theme import (
    ACCENT, BG_DEEPEST, BG_PRIMARY, BG_ELEVATED, BORDER, BORDER_SUBTLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_HOVER, TEXT_DIMMER, TEXT_LYRICS,
)


class AlbumArtPanel(Vertical):
    """Right-hand panel: album art, song metadata, and scrollable lyrics."""

    # ── Focus: this panel is display-only ─────────────────────────────
    can_focus          = False
    can_focus_children = False

    # ── Reactive state ────────────────────────────────────────────────
    _song_path: reactive[str] = reactive("", init=False)
    _song_thumbnail: reactive[str] = reactive("", init=False)
    _title:     reactive[str] = reactive("", init=False)
    _artist:    reactive[str] = reactive("", init=False)
    _album:     reactive[str] = reactive("", init=False)
    _lyrics:    reactive[str] = reactive("", init=False)

    DEFAULT_CSS = f"""
    AlbumArtPanel {{
        width: 42;
        height: 1fr;
        background: rgba(13, 17, 23, 0.4);
        border-left: solid {BORDER};
        border-right: solid {BORDER};
        padding: 0;
        layout: vertical;
        overflow: hidden;
        transition: offset 200ms in_out_cubic;
    }}

    AlbumArtPanel.-hidden {{
        offset-x: 42;
        width: 0;
    }}

    /* ── Fixed top section (art + song info) ─────────────────────────── */
    #art-display-section {{
        width: 100%;
        height: auto;
        padding: 1 2;
        align: center top;
        overflow: hidden;
    }}

    #art-container-outer {{
        width: 100%;
        height: 18;
        border: round {BORDER_SUBTLE};
        background: {BG_DEEPEST};
        overflow: hidden;
        margin: 0 0 1 0;
    }}

    /* ── Image widget – kill ALL borders/focus outlines ────── */
    #album-art-img {{
        width: 100%;
        height: 100%;
        border: none;
        outline: none;
    }}

    #album-art-img:focus {{
        border: none;
        outline: none;
    }}

    TermImageWidget {{
        border: none;
        outline: none;
    }}

    /* ── Song metadata ───────────────────────────────────────────────── */
    #art-info-box {{
        width: 100%;
        height: auto;
        padding: 0 1;
        background: {BG_ELEVATED};
        border: solid {BORDER_SUBTLE};
        margin-top: 1;
    }}

    #art-title {{
        width: 100%;
        color: {TEXT_PRIMARY};
        text-style: bold;
        text-align: center;
        height: 1;
    }}

    #art-artist {{
        width: 100%;
        color: {ACCENT};
        text-align: center;
        height: 1;
    }}

    #art-album {{
        width: 100%;
        color: {TEXT_SECONDARY};
        text-align: center;
        text-style: italic;
        height: 1;
    }}

    /* ── Lyrics — ScrollableContainer handles overflow natively ──────── */
    #lyrics-scroll {{
        width: 100%;
        height: 1fr;
        scrollbar-size: 1 1;
        scrollbar-color: {BORDER_SUBTLE};
        scrollbar-color-hover: {TEXT_DIMMER};
        scrollbar-color-active: {ACCENT};
        scrollbar-background: {BG_PRIMARY};
    }}

    #lyrics-header {{
        width: 100%;
        color: {TEXT_SECONDARY};
        text-style: bold;
        text-align: center;
        padding: 1 0;
        border-bottom: solid {BORDER};
        border-top: solid {BORDER};
    }}

    #lyrics-content {{
        width: 100%;
        height: auto;
        color: {TEXT_HOVER};
        text-align: center;
        padding: 1 3 4 3;
    }}
    """

    # ------------------------------------------------------------------ #
    #  Compose                                                             #
    # ------------------------------------------------------------------ #

    def compose(self) -> ComposeResult:
        with Vertical(id="art-display-section"):
            with Vertical(id="art-container-outer"):
                yield TermImageWidget(id="album-art-img")

            with Vertical(id="art-info-box"):
                yield Static("", id="art-title")
                yield Static("", id="art-artist")
                yield Static("", id="art-album")

        with ScrollableContainer(id="lyrics-scroll"):
            yield Static("── LYRICS ──", id="lyrics-header")
            yield Static("", id="lyrics-content")

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def update_song(
        self,
        song_path: Optional[str],
        title:     str = "",
        artist:    str = "",
        thumbnail: str = "",
    ) -> None:
        """Display a new song. Pass None or empty string to clear."""
        if not song_path:
            self._song_path = ""
            self._song_thumbnail = ""
            return

        if song_path == self._song_path:
            return

        self._title   = truncate(title  or "Unknown Title",  38)
        self._artist  = truncate(artist or "Unknown Artist", 38)
        self._album   = truncate(self._read_album(song_path), 38)
        self._song_thumbnail = thumbnail
        self._song_path = song_path

    # ------------------------------------------------------------------ #
    #  Reactive watchers                                                   #
    # ------------------------------------------------------------------ #

    def watch__title(self, value: str) -> None:
        self.query_one("#art-title", Static).update(value)

    def watch__artist(self, value: str) -> None:
        self.query_one("#art-artist", Static).update(value)

    def watch__album(self, value: str) -> None:
        self.query_one("#art-album", Static).update(value)

    def watch__lyrics(self, value: str) -> None:
        self.query_one("#lyrics-content", Static).update(value)

    def watch__song_path(self, path: str) -> None:
        """Central handler for every song change."""
        if not path:
            self.query_one("#album-art-img",  TermImageWidget).image = None
            self.query_one("#art-title",       Static).update("")
            self.query_one("#art-artist",      Static).update("")
            self.query_one("#art-album",       Static).update("")
            self._lyrics = ""
            return

        self._render_art(path, self._song_thumbnail)
        self._lyrics = "[dim]Searching lyrics…[/dim]"
        self._fetch_lyrics(self._title, self._artist)

    # ------------------------------------------------------------------ #
    #  Image rendering                                                     #
    # ------------------------------------------------------------------ #

    @work(exclusive=True, thread=True)
    def _render_art(self, song_path: str, thumbnail_url: str = "") -> None:
        """Load and render album art in a background thread."""
        widget = self.query_one("#album-art-img", TermImageWidget)
        
        try:
            pil_img = None

            # Case 1: Provided Thumbnail URL (YouTube / Remote)
            if thumbnail_url and thumbnail_url.startswith("http"):
                try:
                    import requests
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
                    resp = requests.get(thumbnail_url, timeout=5, headers=headers)
                    if resp.status_code == 200:
                        pil_img = Image.open(io.BytesIO(resp.content))
                except Exception:
                    pass

            # Case 2: YouTube / Remote URL (fallback check)
            if not pil_img and song_path.startswith("http"):
                from ..app import MusiCLIApp
                if isinstance(self.app, MusiCLIApp):
                    song = next((s for s in self.app.all_songs if s.path == song_path or s.thumbnail == song_path), None)
                    if not song and self.app.player.current_song:
                        if self.app.player.current_song.path == song_path:
                            song = self.app.player.current_song
                    
                    if song and song.thumbnail:
                        import requests
                        resp = requests.get(song.thumbnail, timeout=5)
                        if resp.status_code == 200:
                            pil_img = Image.open(io.BytesIO(resp.content))
            
            # Case 3: Local File
            if not pil_img and not song_path.startswith("http") and os.path.exists(song_path):
                tag = TinyTag.get(song_path, image=True)
                raw = tag.get_image()
                if raw:
                    pil_img = Image.open(io.BytesIO(raw))

            # Case 3: Fallback to default
            if not pil_img:
                path = resolve_resource("musiCLI.png")
                if os.path.exists(path):
                    pil_img = Image.open(path)

            if pil_img:
                pil_img = _prepare_image(pil_img)
                
                # --- Strict 1:1 Center Crop Logic ---
                width, height = pil_img.size
                size = min(width, height)
                left = (width - size) // 2
                top = (height - size) // 2
                right = (width + size) // 2
                bottom = (height + size) // 2
                
                final_img = pil_img.crop((left, top, right, bottom))
                
                def _update():
                    widget.image = final_img
                
                self.app.call_from_thread(_update)
            else:
                self.app.call_from_thread(setattr, widget, "image", None)

        except Exception:
            # Final fallback
            def _set_none():
                widget.image = None
            self.app.call_from_thread(_set_none)

    # ------------------------------------------------------------------ #
    #  Lyrics worker                                                       #
    # ------------------------------------------------------------------ #

    @work(exclusive=True, thread=True)
    def _fetch_lyrics(self, title: str, artist: str) -> None:
        """Fetch and display lyrics in a background thread."""
        def set_lyrics(text: str) -> None:
            self._lyrics = text

        try:
            query = f"{title} {artist}".strip()
            if not query or query.lower() == "unknown title unknown artist":
                self.app.call_from_thread(set_lyrics, "[dim]No metadata to search lyrics.[/dim]")
                return

            # syncedlyrics can sometimes hang on certain providers
            # We use a short-circuit if it takes too long (simulated via thread safety)
            # and rely on the library's internal behavior while catching all networking errors
            lrc = syncedlyrics.search(query)
            
            if not lrc:
                self.app.call_from_thread(set_lyrics, "[dim]No lyrics found.[/dim]")
                return

            clean = re.sub(r"\[\d{2}:\d{2}\.\d{2,3}\]", "", lrc)
            lines = [ln.strip() for ln in clean.splitlines() if ln.strip()]

            if not lines:
                self.app.call_from_thread(set_lyrics, "[dim]No lyrics found.[/dim]")
                return

            styled: list[str] = []
            for i, line in enumerate(lines):
                if   i % 4 == 0: styled.append(f"[{ACCENT}]{line}[/]")
                elif i % 4 == 2: styled.append(f"[{TEXT_LYRICS}]{line}[/]")
                else:             styled.append(line)

            self.app.call_from_thread(set_lyrics, "\n\n".join(styled))

        except Exception:
            # Catch timeouts, connection errors, etc.
            self.app.call_from_thread(set_lyrics, "[dim]Lyrics currently unavailable (timeout).[/dim]")

    # ------------------------------------------------------------------ #
    #  Metadata helpers                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _read_album(song_path: str) -> str:
        """Read the album tag from the file."""
        try:
            return "" if song_path.startswith("http") else (
                TinyTag.get(song_path).album or ""
            )
        except Exception:
            return ""


def _prepare_image(pil: Image.Image) -> Image.Image:
    """Normalise an image for high-quality terminal display."""
    pil = ImageOps.exif_transpose(pil)
    if pil.mode != "RGB":
        pil = pil.convert("RGB")
    return pil
