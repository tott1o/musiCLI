"""
Data models for MusiCLI.

Plain dataclasses that represent a song and a playlist.  They carry
no framework-specific logic so they can be reused anywhere.
"""

from dataclasses import dataclass, field


@dataclass
class Song:
    """A single audio track."""

    path: str                  # absolute file path
    filename: str              # stem without extension
    title: str                 # from metadata or filename
    artist: str
    album: str
    duration: float            # seconds
    format: str                # e.g. "mp3", "flac"
    playlist_name: str         # parent folder name
    is_stream: bool = False    # True if URL, False if local file
    thumbnail: str = ""        # URL or path to thumbnail image

    # ── Display helpers ─────────────────────────────────────────
    @property
    def display_title(self) -> str:
        return self.title if self.title else self.filename

    @property
    def display_artist(self) -> str:
        return self.artist if self.artist else "Unknown Artist"

    @property
    def display_album(self) -> str:
        return self.album if self.album else "Unknown Album"

    @property
    def duration_str(self) -> str:
        """Format duration as M:SS or H:MM:SS."""
        total = int(self.duration)
        if total < 0:
            return "0:00"
        hrs, remainder = divmod(total, 3600)
        mins, secs = divmod(remainder, 60)
        if hrs > 0:
            return f"{hrs}:{mins:02d}:{secs:02d}"
        return f"{mins}:{secs:02d}"

    def matches_query(self, query: str) -> bool:
        """Case-insensitive search across title, artist, album, filename."""
        q = query.lower()
        return (
            q in self.title.lower()
            or q in self.artist.lower()
            or q in self.album.lower()
            or q in self.filename.lower()
        )


@dataclass
class Playlist:
    """A folder of songs (== a playlist)."""

    name: str
    path: str
    songs: list[Song] = field(default_factory=list)

    @property
    def song_count(self) -> int:
        return len(self.songs)

    @property
    def total_duration(self) -> float:
        return sum(s.duration for s in self.songs)

    @property
    def total_duration_str(self) -> str:
        total = int(self.total_duration)
        hrs, remainder = divmod(total, 3600)
        mins, secs = divmod(remainder, 60)
        if hrs > 0:
            return f"{hrs}h {mins}m"
        return f"{mins}m {secs}s"
