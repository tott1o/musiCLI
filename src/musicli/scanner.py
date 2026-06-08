"""
Folder scanning and metadata reading for MusiCLI.

Walks the user-supplied root directory, treats each immediate
subdirectory as a playlist, reads audio-file metadata via tinytag,
and returns a clean list of Playlist objects.
"""

from pathlib import Path

from tinytag import TinyTag

from .config import SUPPORTED_FORMATS
from .models import Playlist, Song


def scan_root_folder(root_path: str) -> list[Playlist]:
    """
    Scan *root_path* for playlist folders and their audio files.

    Structure expected:
        root/
            playlist_a/
                song1.mp3
                song2.flac
            playlist_b/
                song3.ogg

    Audio files sitting directly in *root_path* are grouped under a
    special "Root" playlist.

    Returns a sorted list of Playlist objects.
    """
    root = Path(root_path).resolve()
    if not root.exists() or not root.is_dir():
        return []

    playlists: list[Playlist] = []

    # ── Songs directly in root → "Root" playlist ───────────────
    root_songs = _scan_directory(root, "Root")
    if root_songs:
        playlists.append(Playlist(name="Root", path=str(root), songs=root_songs))

    # ── Each subdirectory → one playlist ───────────────────────
    for entry in sorted(root.iterdir()):
        if entry.is_dir() and not entry.name.startswith("."):
            songs = _scan_directory(entry, entry.name)
            if songs:
                playlists.append(
                    Playlist(name=entry.name, path=str(entry), songs=songs)
                )

    return playlists


def get_all_songs(playlists: list[Playlist]) -> list[Song]:
    """Flatten all playlists into a single song list."""
    return [song for pl in playlists for song in pl.songs]


# ── Internal helpers ────────────────────────────────────────────


def _scan_directory(directory: Path, playlist_name: str) -> list[Song]:
    """Return every readable audio file in *directory* (non-recursive)."""
    songs: list[Song] = []
    for fp in sorted(directory.iterdir()):
        if fp.is_file() and fp.suffix.lower() in SUPPORTED_FORMATS:
            song = _read_metadata(fp, playlist_name)
            if song is not None:
                songs.append(song)
    return songs


def _read_metadata(file_path: Path, playlist_name: str) -> Song:
    """
    Read ID3 / Vorbis / FLAC tags with tinytag.

    If metadata extraction fails the song is still returned with
    sensible defaults derived from the filename.
    """
    title = file_path.stem
    artist = "Unknown Artist"
    album = "Unknown Album"
    duration = 0.0

    try:
        tag = TinyTag.get(str(file_path))
        if tag.title:
            title = tag.title
        if tag.artist:
            artist = tag.artist
        if tag.album:
            album = tag.album
        if tag.duration:
            duration = tag.duration
    except Exception:
        # Mutagen/tinytag could not parse the file — that's OK,
        # we still add the song with filename-based info.
        pass

    return Song(
        path=str(file_path),
        filename=file_path.stem,
        title=title,
        artist=artist,
        album=album,
        duration=duration,
        format=file_path.suffix.lower().lstrip("."),
        playlist_name=playlist_name,
    )
