"""
Queue panel – allows viewing and managing the upcoming play queue.

Displayed in the main content area when "Queue" is selected in the
sidebar.  This widget is intentionally simple: the TrackList widget
doubles as the queue view; this module only provides helper logic.
"""

from __future__ import annotations

from typing import List, Optional

from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import DataTable, Static

from ..utils import truncate

from ..models import Song
from ..theme import ACCENT, BG_PRIMARY, BG_HOVER, TEXT_SECONDARY


class QueuePanel(Vertical):
    """Dedicated queue view with move / remove controls."""

    BINDINGS = [
        Binding("k", "move_up", "Move Up", show=False),
        Binding("j", "move_down", "Move Down", show=False),
        Binding("delete", "remove_from_queue", "Remove", show=False),
        Binding("x", "remove_from_queue", "Remove", show=False),
    ]

    DEFAULT_CSS = f"""
    QueuePanel {{
        background: {BG_PRIMARY};
        padding: 0;
    }}
    QueuePanel #queue-header {{
        width: 100%;
        padding: 1 2;
        color: {ACCENT};
        text-style: bold;
        background: {BG_PRIMARY};
    }}
    QueuePanel #queue-info {{
        width: 100%;
        padding: 0 2 1 2;
        color: {TEXT_SECONDARY};
        background: {BG_PRIMARY};
    }}
    QueuePanel DataTable {{
        background: {BG_PRIMARY};
        scrollbar-size: 1 1;
        max-width: 100%;
    }}
    QueuePanel DataTable > .datatable--cursor {{
        background: {BG_HOVER};
        color: {ACCENT};
    }}
    """

    class QueueTrackSelected(Message):
        def __init__(self, song_path: str) -> None:
            super().__init__()
            self.song_path = song_path

    class QueueTrackMoveRequested(Message):
        def __init__(self, index: int, direction: int) -> None:
            super().__init__()
            self.index = index
            self.direction = direction

    class QueueTrackRemoveRequested(Message):
        def __init__(self, index: int) -> None:
            super().__init__()
            self.index = index

    def compose(self) -> ComposeResult:
        yield Static("   Play Queue", id="queue-header")
        yield Static("0 upcoming tracks", id="queue-info")
        yield DataTable(id="queue-table")

    def on_mount(self) -> None:
        table = self.query_one("#queue-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("   ", "#", "Title", "Artist", "Duration")

    def action_move_up(self) -> None:
        table = self.query_one("#queue-table", DataTable)
        if table.cursor_row is not None:
            self.post_message(self.QueueTrackMoveRequested(table.cursor_row, -1))

    def action_move_down(self) -> None:
        table = self.query_one("#queue-table", DataTable)
        if table.cursor_row is not None:
            self.post_message(self.QueueTrackMoveRequested(table.cursor_row, 1))

    def action_remove_from_queue(self) -> None:
        table = self.query_one("#queue-table", DataTable)
        if table.cursor_row is not None:
            self.post_message(self.QueueTrackRemoveRequested(table.cursor_row))

    def update_queue(
        self,
        queue: List[Song],
        current_index: int = -1,
    ) -> None:
        """Refresh the queue display."""
        table = self.query_one("#queue-table", DataTable)
        
        # Save state
        cursor_coord = table.cursor_coordinate
        scroll_x, scroll_y = table.scroll_offset

        table.clear()

        upcoming = 0
        for idx, song in enumerate(queue):
            playing = "▶" if idx == current_index else " "
            if idx > current_index:
                upcoming += 1
            
            title = truncate(song.display_title, 50)
            artist = truncate(song.display_artist, 40)
            
            table.add_row(
                playing,
                str(idx + 1),
                title,
                artist,
                song.duration_str,
                key=f"q_{idx}_{song.path}",
            )

        # Restore state
        if cursor_coord:
            row = min(cursor_coord.row, len(queue) - 1)
            if row >= 0:
                table.cursor_coordinate = (row, cursor_coord.column)
            table.scroll_to(scroll_x, scroll_y, animate=False)

        info = self.query_one("#queue-info", Static)
        info.update(f"  {upcoming} upcoming track{'s' if upcoming != 1 else ''}")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        raw_key = str(event.row_key.value)
        path = raw_key.split("_", 2)[2] if raw_key.startswith("q_") else raw_key
        self.post_message(self.QueueTrackSelected(path))
