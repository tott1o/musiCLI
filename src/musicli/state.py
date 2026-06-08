"""
Persistent state manager for MusiCLI.

Stores favourites, recently-played history, and last playback
position in a JSON file under ~/.musicli/state.json so the player
can resume where you left off.
"""

import json
from pathlib import Path
from typing import Set, List

from .config import STATE_DIR, STATE_FILE, MAX_RECENT


class AppState:
    """Read / write player state to disk."""

    def __init__(self) -> None:
        self._favorites: Set[str] = set()        # song paths
        self._youtube_playlists: dict[str, List[dict]] = {"Starred": []} # playlist name -> list of song info
        self._recently_played: List[str] = []    # song paths, newest last
        self._saved_roots: List[dict] = []       # [{"name": ..., "path": ...}]
        self._last_song_path: str = ""
        self._last_position: float = 0.0
        self._last_volume: float = 0.7
        self._last_shuffle: bool = False
        self._last_repeat: str = "off"
        self._last_bass: float = 0.0
        self._last_mid: float = 0.0
        self._last_treble: float = 0.0
        self._last_root: str = ""
        self._load()

    # ── Persistence ─────────────────────────────────────────────

    def _load(self) -> None:
        """Load state from disk (silently ignores errors)."""
        try:
            if STATE_FILE.exists():
                data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                self._favorites = set(data.get("favorites", []))
                self._youtube_playlists = data.get("youtube_playlists", {"Starred": []})
                self._recently_played = data.get("recently_played", [])
                self._saved_roots = data.get("saved_roots", [])
                self._last_song_path = data.get("last_song_path", "")
                self._last_position = data.get("last_position", 0.0)
                self._last_volume = data.get("last_volume", 0.7)
                self._last_shuffle = data.get("last_shuffle", False)
                self._last_repeat = data.get("last_repeat", "off")
                self._last_bass = data.get("last_bass", 0.0)
                self._last_mid = data.get("last_mid", 0.0)
                self._last_treble = data.get("last_treble", 0.0)
                self._last_root = data.get("last_root", "")
        except Exception:
            pass

    def save(self) -> None:
        """Flush current state to disk."""
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "favorites": list(self._favorites),
                "youtube_playlists": self._youtube_playlists,
                "recently_played": self._recently_played[-MAX_RECENT:],
                "saved_roots": self._saved_roots,
                "last_song_path": self._last_song_path,
                "last_position": self._last_position,
                "last_volume": self._last_volume,
                "last_shuffle": self._last_shuffle,
                "last_repeat": self._last_repeat,
                "last_bass": self._last_bass,
                "last_mid": self._last_mid,
                "last_treble": self._last_treble,
                "last_root": self._last_root,
            }
            STATE_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    # ── Favorites ───────────────────────────────────────────────

    def toggle_favorite(self, path: str) -> bool:
        """Toggle favourite status. Returns True if now a favourite."""
        if path in self._favorites:
            self._favorites.discard(path)
            self.save()
            return False
        self._favorites.add(path)
        self.save()
        return True

    def is_favorite(self, path: str) -> bool:
        return path in self._favorites

    @property
    def favorites(self) -> Set[str]:
        return self._favorites

    # ── YouTube Playlists ───────────────────────────────────────

    def create_youtube_playlist(self, name: str) -> bool:
        """Create a new empty YouTube playlist. Returns True if created."""
        if name in self._youtube_playlists:
            return False
        self._youtube_playlists[name] = []
        self.save()
        return True

    def delete_youtube_playlist(self, name: str) -> None:
        """Delete a YouTube playlist."""
        if name in self._youtube_playlists and name != "Starred":
            del self._youtube_playlists[name]
            self.save()

    def add_to_youtube_playlist(self, playlist_name: str, song_data: dict) -> bool:
        """Add a song to a specific YouTube playlist."""
        if playlist_name not in self._youtube_playlists:
            return False
        
        path = song_data.get("path")
        # Avoid duplicates in same playlist
        if any(s.get("path") == path for s in self._youtube_playlists[playlist_name]):
            return False
            
        # Update playlist_name so it displays correctly when played from this playlist
        song_data["playlist_name"] = playlist_name
        self._youtube_playlists[playlist_name].append(song_data)
        self.save()
        return True

    def remove_from_youtube_playlist(self, playlist_name: str, path: str) -> None:
        """Remove a song from a YouTube playlist."""
        if playlist_name in self._youtube_playlists:
            self._youtube_playlists[playlist_name] = [
                s for s in self._youtube_playlists[playlist_name] if s.get("path") != path
            ]
            self.save()

    def is_youtube_starred(self, path: str) -> bool:
        """Checks if a song is in the 'Starred' playlist."""
        return any(star.get("path") == path for star in self._youtube_playlists.get("Starred", []))

    @property
    def youtube_playlists(self) -> dict[str, List[dict]]:
        return self._youtube_playlists

    # ── Recently played ─────────────────────────────────────────

    def add_recent(self, path: str) -> None:
        """Push a song to the recently-played list (deduped)."""
        if path in self._recently_played:
            self._recently_played.remove(path)
        self._recently_played.append(path)
        if len(self._recently_played) > MAX_RECENT:
            self._recently_played.pop(0)
        self.save()

    @property
    def recently_played(self) -> List[str]:
        """Most-recent first."""
        return list(reversed(self._recently_played))

    # ── Last playback state ─────────────────────────────────────

    def save_playback(
        self,
        song_path: str,
        position: float,
        volume: float,
        shuffle: bool,
        repeat: str,
        bass: float,
        mid: float,
        treble: float,
        root: str,
    ) -> None:
        self._last_song_path = song_path
        self._last_position = position
        self._last_volume = volume
        self._last_shuffle = shuffle
        self._last_repeat = repeat
        self._last_bass = bass
        self._last_mid = mid
        self._last_treble = treble
        self._last_root = root
        self.save()

    @property
    def last_song_path(self) -> str:
        return self._last_song_path

    @property
    def last_position(self) -> float:
        return self._last_position

    @property
    def last_volume(self) -> float:
        return self._last_volume

    @property
    def last_shuffle(self) -> bool:
        return self._last_shuffle

    @property
    def last_repeat(self) -> str:
        return self._last_repeat

    @property
    def last_bass(self) -> float:
        return self._last_bass

    @property
    def last_mid(self) -> float:
        return self._last_mid

    @property
    def last_treble(self) -> float:
        return self._last_treble

    @property
    def last_root(self) -> str:
        return self._last_root

    # ── Saved libraries (previously accessed roots) ─────────────

    def add_saved_root(self, path: str) -> None:
        """Remember a root folder without changing the list order."""
        from pathlib import Path as P
        path_obj = P(path).resolve()
        abs_path = str(path_obj)
        name = path_obj.name or path_obj.anchor

        # Check if already exists to avoid reordering
        for r in self._saved_roots:
            if r.get("path") == abs_path:
                return

        self._saved_roots.append({"name": name, "path": abs_path})
        self.save()

    def remove_saved_root(self, path: str) -> None:
        """Remove a saved root folder."""
        self._saved_roots = [
            r for r in self._saved_roots if r.get("path") != path
        ]
        self.save()

    def prune_saved_roots(self) -> None:
        """Check all saved roots and remove those that no longer exist."""
        from pathlib import Path as P
        original_count = len(self._saved_roots)
        self._saved_roots = [
            r for r in self._saved_roots if P(r.get("path", "")).exists()
        ]
        if len(self._saved_roots) != original_count:
            self.save()

    @property
    def saved_roots(self) -> List[dict]:
        """Return list of {name, path} dicts, most-recent last."""
        return list(self._saved_roots)
