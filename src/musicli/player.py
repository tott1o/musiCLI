"""
Audio playback engine for MusiCLI.

Wraps vlc with queue management, shuffle, repeat
modes, seeking, and volume control.  Designed to be driven by a
Textual timer that calls ``tick()`` every ~500 ms.
"""

import random
import subprocess
import os
import signal
from enum import Enum
from typing import List, Optional, Callable

import vlc

from .models import Song


class RepeatMode(Enum):
    OFF = "off"
    ALL = "all"
    ONE = "one"


class PlayerState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


class MusicPlayer:
    """Core audio engine backed by vlc."""

    def __init__(self) -> None:
        # Initialise vlc
        self._vlc_instance = vlc.Instance("--no-video", "--quiet")
        self._vlc_player = self._vlc_instance.media_player_new()

        # ── playback state ──────────────────────────────────────
        self._state: PlayerState = PlayerState.STOPPED
        self._current_song: Optional[Song] = None
        self._volume: float = 0.7
        self._seek_offset: float = 0.0      # position (s) we seeked to
        self._bass_boost: float = 0.0      # bass level (0.0 to 1.0)
        self._mid_gain: float = 0.0       # mid level (0.0 to 1.0)
        self._treble_gain: float = 0.0    # treble level (0.0 to 1.0)

        # ── EQ ──────────────────────────────────────────────────
        self._equalizer = vlc.AudioEqualizer()
        self._update_equalizer()

        # ── queue ───────────────────────────────────────────────
        self._queue: List[Song] = []
        self._queue_index: int = -1
        self._original_queue: List[Song] = []   # pre-shuffle order

        # ── modes ───────────────────────────────────────────────
        self._shuffle: bool = False
        self._repeat_mode: RepeatMode = RepeatMode.OFF

        # ── history ─────────────────────────────────────────────
        self._history: List[Song] = []

        # ── error guard ─────────────────────────────────────────
        self._failed_attempts: int = 0

        # ── callbacks (set by the App) ──────────────────────────
        self._on_track_change: Optional[Callable] = None
        self._on_state_change: Optional[Callable] = None
        self._on_pre_play: Optional[Callable] = None

        self.set_volume(self._volume)

    # ────────────────────────────────────────────────────────────
    #  Properties
    # ────────────────────────────────────────────────────────────

    @property
    def state(self) -> PlayerState:
        return self._state

    @property
    def is_playing(self) -> bool:
        return self._state == PlayerState.PLAYING

    @property
    def is_paused(self) -> bool:
        return self._state == PlayerState.PAUSED

    @property
    def current_song(self) -> Optional[Song]:
        return self._current_song

    @property
    def volume(self) -> float:
        return self._volume

    @property
    def bass_boost(self) -> float:
        return self._bass_boost

    @property
    def mid_gain(self) -> float:
        return self._mid_gain

    @property
    def treble_gain(self) -> float:
        return self._treble_gain

    @property
    def shuffle(self) -> bool:
        return self._shuffle

    @property
    def repeat_mode(self) -> RepeatMode:
        return self._repeat_mode

    @property
    def queue(self) -> List[Song]:
        return list(self._queue)

    @property
    def queue_index(self) -> int:
        return self._queue_index

    @property
    def position(self) -> float:
        """Current playback position in seconds."""
        if self._state == PlayerState.STOPPED:
            return 0.0
        
        # VLC returns time in ms
        return self._vlc_player.get_time() / 1000.0

    @property
    def history(self) -> List[Song]:
        return list(self._history)

    # ────────────────────────────────────────────────────────────
    #  Presets
    # ────────────────────────────────────────────────────────────

    def get_presets(self) -> List[str]:
        """Return a list of available VLC equalizer preset names."""
        count = vlc.libvlc_audio_equalizer_get_preset_count()
        presets = []
        for i in range(count):
            name = vlc.libvlc_audio_equalizer_get_preset_name(i)
            if isinstance(name, bytes):
                name = name.decode("utf-8")
            presets.append(name)
        return presets

    def apply_preset(self, index: int) -> None:
        """Apply a VLC equalizer preset by index and sync internal gain values."""
        # Use vlc's built-in presets
        new_eq = vlc.libvlc_audio_equalizer_new_from_preset(index)
        if new_eq:
            self._equalizer = new_eq
            
            # Extract approximate values for UI indicators (mapping -20..20dB to roughly 0..1.0)
            # We use representative bands for each zone: 60Hz (0), 1kHz (4), 16kHz (9)
            # We treat 0dB as 0.0 and 20dB as 1.0 (clamping cuts to 0 for the 'boost' bars)
            try:
                self._bass_boost = max(0.0, self._equalizer.get_amp_at_index(0)) / 20.0
                self._mid_gain = max(0.0, self._equalizer.get_amp_at_index(4)) / 20.0
                self._treble_gain = max(0.0, self._equalizer.get_amp_at_index(9)) / 20.0
            except Exception:
                self._bass_boost = 0.0
                self._mid_gain = 0.0
                self._treble_gain = 0.0
            
            if self._vlc_player:
                self._vlc_player.set_equalizer(self._equalizer)

    # ────────────────────────────────────────────────────────────
    #  Callbacks
    # ────────────────────────────────────────────────────────────

    def set_callbacks(
        self,
        on_track_change: Optional[Callable] = None,
        on_state_change: Optional[Callable] = None,
        on_pre_play: Optional[Callable] = None,
    ) -> None:
        self._on_track_change = on_track_change
        self._on_state_change = on_state_change
        self._on_pre_play = on_pre_play

    # ────────────────────────────────────────────────────────────
    #  Queue management
    # ────────────────────────────────────────────────────────────

    def load_queue(self, songs: List[Song], start_index: int = 0) -> None:
        """Replace the play queue with *songs*, optionally starting at *start_index*."""
        self._original_queue = list(songs)
        if self._shuffle:
            self._queue = list(songs)
            if 0 <= start_index < len(self._queue):
                first = self._queue.pop(start_index)
                random.shuffle(self._queue)
                self._queue.insert(0, first)
                self._queue_index = 0
            else:
                random.shuffle(self._queue)
                self._queue_index = 0
        else:
            self._queue = list(songs)
            self._queue_index = max(0, min(start_index, len(songs) - 1))

    def add_to_queue(self, song: Song) -> None:
        """Insert a single song after the current track so it plays next."""
        insert_idx = self._queue_index + 1
        if insert_idx < 0:
            insert_idx = 0
        
        self._queue.insert(insert_idx, song)
        self._original_queue.append(song)

    def remove_from_queue(self, index: int) -> None:
        if 0 <= index < len(self._queue):
            song = self._queue.pop(index)
            if index < self._queue_index:
                self._queue_index -= 1
            elif index == self._queue_index:
                # If we removed the current song, we stay at the same index
                # but the next song slides in. If we were at the end, adjust.
                if self._queue_index >= len(self._queue):
                    self._queue_index = len(self._queue) - 1

            if song in self._original_queue:
                self._original_queue.remove(song)

    def clear_queue_upcoming(self) -> None:
        """Remove everything *after* the currently-playing index."""
        if self._queue_index + 1 < len(self._queue):
            self._queue = self._queue[: self._queue_index + 1]

    def move_in_queue(self, from_idx: int, to_idx: int) -> None:
        if 0 <= from_idx < len(self._queue) and 0 <= to_idx < len(self._queue):
            song = self._queue.pop(from_idx)
            self._queue.insert(to_idx, song)
            
            # Sync original_queue if not shuffling
            if not self._shuffle:
                if song in self._original_queue:
                    old_orig_idx = self._original_queue.index(song)
                    self._original_queue.pop(old_orig_idx)
                    # This is a bit tricky, where to insert in original_queue?
                    # If we're not shuffling, _queue and _original_queue should be identical.
                    self._original_queue = list(self._queue)

            if from_idx == self._queue_index:
                self._queue_index = to_idx
            elif from_idx < self._queue_index <= to_idx:
                self._queue_index -= 1
            elif to_idx <= self._queue_index < from_idx:
                self._queue_index += 1

    # ────────────────────────────────────────────────────────────
    #  Playback controls
    # ────────────────────────────────────────────────────────────

    def _stop_all(self) -> None:
        """Internal helper to stop vlc."""
        if self._vlc_player:
            self._vlc_player.stop()

    def play(self, song: Optional[Song] = None, start_pos: float = 0.0, force: bool = False) -> None:
        """
        Start playback.

        *song* – if given, play that specific track (must already be in queue,
                  or it becomes the sole queue entry).
        *start_pos* – seek offset in seconds.
        *force* - if True, skip the pre-play hook (used for re-entering after extraction).
        """
        if song is not None:
            if song in self._queue:
                self._queue_index = self._queue.index(song)
            else:
                self._queue = [song]
                self._original_queue = [song]
                self._queue_index = 0
            self._current_song = song
        elif self._queue and 0 <= self._queue_index < len(self._queue):
            self._current_song = self._queue[self._queue_index]
        else:
            return

        # Pre-play hook (e.g. for YouTube extraction)
        if not force and self._on_pre_play:
            if self._on_pre_play(self._current_song):
                return

        self._stop_all()

        try:
            # Play with vlc
            media = self._vlc_instance.media_new(self._current_song.path)
            self._vlc_player.set_media(media)
            self._vlc_player.audio_set_volume(int(self._volume * 100))
            self._vlc_player.set_equalizer(self._equalizer)
            self._vlc_player.play()
            
            # If there's a start position, seek after a short delay (vlc needs to buffer)
            if start_pos > 0:
                self._vlc_player.set_time(int(start_pos * 1000))
            
            self._seek_offset = start_pos
            self._state = PlayerState.PLAYING
            self._failed_attempts = 0

            # history
            if (
                not self._history
                or self._history[-1].path != self._current_song.path
            ):
                self._history.append(self._current_song)
                if len(self._history) > 50:
                    self._history.pop(0)

            if self._on_track_change:
                self._on_track_change(self._current_song)
            if self._on_state_change:
                self._on_state_change(self._state)

        except Exception as e:
            # File unreadable – try the next track (with a guard).
            self._failed_attempts += 1
            if self._failed_attempts < len(self._queue):
                self._queue_index = (self._queue_index + 1) % len(self._queue)
                self.play()
            else:
                self._state = PlayerState.STOPPED
                self._failed_attempts = 0
                raise e

    def pause(self) -> None:
        if self._state == PlayerState.PLAYING:
            self._vlc_player.pause()
            self._state = PlayerState.PAUSED
            if self._on_state_change:
                self._on_state_change(self._state)

    def resume(self) -> None:
        if self._state == PlayerState.PAUSED:
            self._vlc_player.play()
            self._state = PlayerState.PLAYING
            if self._on_state_change:
                self._on_state_change(self._state)

    def toggle_pause(self) -> None:
        if self._state == PlayerState.PLAYING:
            self.pause()
        elif self._state == PlayerState.PAUSED:
            self.resume()
        elif self._state == PlayerState.STOPPED and self._current_song:
            self.play()

    def stop(self) -> None:
        self._stop_all()
        self._state = PlayerState.STOPPED
        self._seek_offset = 0.0
        if self._on_state_change:
            self._on_state_change(self._state)

    def next_track(self) -> None:
        if not self._queue:
            return
        if self._repeat_mode == RepeatMode.ONE:
            self.play(start_pos=0.0)
            return

        self._queue_index += 1
        if self._queue_index >= len(self._queue):
            if self._repeat_mode == RepeatMode.ALL:
                self._queue_index = 0
                if self._shuffle:
                    random.shuffle(self._queue)
            else:
                self._queue_index = len(self._queue) - 1
                self.stop()
                return
        self.play()

    def prev_track(self) -> None:
        if not self._queue:
            return
        # If more than 3 s into the track → restart it.
        if self.position > 3.0:
            self.play(start_pos=0.0)
            return
        if self._repeat_mode == RepeatMode.ONE:
            self.play(start_pos=0.0)
            return

        self._queue_index -= 1
        if self._queue_index < 0:
            if self._repeat_mode == RepeatMode.ALL:
                self._queue_index = len(self._queue) - 1
            else:
                self._queue_index = 0
                self.play(start_pos=0.0)
                return
        self.play()

    # ────────────────────────────────────────────────────────────
    #  Seeking
    # ────────────────────────────────────────────────────────────

    def seek(self, position: float) -> None:
        """Seek to an absolute *position* in seconds."""
        if self._current_song is None or self._state == PlayerState.STOPPED:
            return
        
        # Guard against seeking beyond duration if known
        if self._current_song.duration > 0:
            position = max(0.0, min(position, self._current_song.duration))
        else:
            position = max(0.0, position)

        try:
            # VLC uses milliseconds
            self._vlc_player.set_time(int(position * 1000))
        except Exception:
            pass

    def seek_relative(self, delta: float) -> None:
        """Seek forward/backward by *delta* seconds."""
        self.seek(self.position + delta)

    # ────────────────────────────────────────────────────────────
    #  Volume & Bass
    # ────────────────────────────────────────────────────────────

    def set_volume(self, volume: float) -> None:
        self._volume = max(0.0, min(1.0, volume))
        if self._vlc_player:
            self._vlc_player.audio_set_volume(int(self._volume * 100))

    def volume_up(self, step: float = 0.05) -> None:
        self.set_volume(self._volume + step)

    def volume_down(self, step: float = 0.05) -> None:
        self.set_volume(self._volume - step)

    def set_bass_boost(self, level: float) -> None:
        """Set bass boost level from 0.0 to 1.0."""
        self._bass_boost = max(0.0, min(1.0, level))
        self._update_equalizer()

    def bass_up(self, step: float = 0.1) -> None:
        self.set_bass_boost(self._bass_boost + step)

    def bass_down(self, step: float = 0.1) -> None:
        self.set_bass_boost(self._bass_boost - step)

    def set_mid_gain(self, level: float) -> None:
        """Set mid gain level from 0.0 to 1.0."""
        self._mid_gain = max(0.0, min(1.0, level))
        self._update_equalizer()

    def set_treble_gain(self, level: float) -> None:
        """Set treble gain level from 0.0 to 1.0."""
        self._treble_gain = max(0.0, min(1.0, level))
        self._update_equalizer()

    def _update_equalizer(self) -> None:
        """Apply audio settings to EQ bands."""
        # VLC EQ bands: 60Hz, 170Hz, 310Hz, 600Hz, 1kHz, 3kHz, 6kHz, 12kHz, 14kHz, 16kHz
        # Range: -20.0 to 20.0 dB
        
        # Bass (Bands 0, 1, 2)
        bass_db = self._bass_boost * 20.0
        self._equalizer.set_amp_at_index(bass_db, 0)
        self._equalizer.set_amp_at_index(bass_db * 0.8, 1)
        self._equalizer.set_amp_at_index(bass_db * 0.4, 2)
        
        # Mids (Bands 3, 4, 5)
        mid_db = self._mid_gain * 20.0
        self._equalizer.set_amp_at_index(mid_db * 0.5, 3)
        self._equalizer.set_amp_at_index(mid_db, 4)
        self._equalizer.set_amp_at_index(mid_db * 0.5, 5)
        
        # Treble (Bands 6, 7, 8, 9)
        treble_db = self._treble_gain * 20.0
        self._equalizer.set_amp_at_index(treble_db * 0.3, 6)
        self._equalizer.set_amp_at_index(treble_db * 0.6, 7)
        self._equalizer.set_amp_at_index(treble_db, 8)
        self._equalizer.set_amp_at_index(treble_db, 9)
        
        if self._vlc_player:
            self._vlc_player.set_equalizer(self._equalizer)

    # ────────────────────────────────────────────────────────────
    #  Shuffle / repeat
    # ────────────────────────────────────────────────────────────

    def toggle_shuffle(self) -> None:
        self._shuffle = not self._shuffle
        if self._shuffle:
            current = self._current_song
            remaining = [s for i, s in enumerate(self._queue) if i > self._queue_index]
            random.shuffle(remaining)
            self._queue = self._queue[: self._queue_index + 1] + remaining
        else:
            # Restore original order, keeping current track selected.
            if self._current_song and self._current_song in self._original_queue:
                idx = self._original_queue.index(self._current_song)
                self._queue = list(self._original_queue)
                self._queue_index = idx

    def cycle_repeat(self) -> None:
        """OFF → ALL → ONE → OFF."""
        modes = [RepeatMode.OFF, RepeatMode.ALL, RepeatMode.ONE]
        cur = modes.index(self._repeat_mode)
        self._repeat_mode = modes[(cur + 1) % 3]

    # ────────────────────────────────────────────────────────────
    #  Tick (called by App timer)
    # ────────────────────────────────────────────────────────────

    def is_track_finished(self) -> bool:
        """True when the current track has ended naturally."""
        if self._state != PlayerState.PLAYING:
            return False
        
        # VLC states: 6 is Ended, 7 is Error. 
        # We use .value for safer comparison across some binding versions.
        state = self._vlc_player.get_state().value
        return state in [6, 7] # vlc.State.Ended, vlc.State.Error

    # ────────────────────────────────────────────────────────────
    #  Cleanup
    # ────────────────────────────────────────────────────────────

    def cleanup(self) -> None:
        """Release vlc resources."""
        try:
            if self._vlc_player:
                self._vlc_player.stop()
                self._vlc_player.release()
            if self._vlc_instance:
                self._vlc_instance.release()
        except Exception:
            pass
