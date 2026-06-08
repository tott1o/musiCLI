"""Tests for MusiCLI data models."""

from musicli.models import Song, Playlist


def test_song_display_title_with_title():
    song = Song(
        path="/music/test.mp3",
        filename="test",
        title="My Song",
        artist="Artist",
        album="Album",
        duration=180.0,
        format="mp3",
        playlist_name="Music",
    )
    assert song.display_title == "My Song"


def test_song_display_title_fallback():
    song = Song(
        path="/music/test.mp3",
        filename="test",
        title="",
        artist="",
        album="",
        duration=0.0,
        format="mp3",
        playlist_name="Music",
    )
    assert song.display_title == "test"


def test_song_duration_str():
    song = Song(
        path="/music/test.mp3",
        filename="test",
        title="Test",
        artist="",
        album="",
        duration=125.0,
        format="mp3",
        playlist_name="Music",
    )
    assert song.duration_str == "2:05"


def test_song_duration_str_hours():
    song = Song(
        path="/music/test.mp3",
        filename="test",
        title="Test",
        artist="",
        album="",
        duration=3661.0,
        format="mp3",
        playlist_name="Music",
    )
    assert song.duration_str == "1:01:01"


def test_song_matches_query():
    song = Song(
        path="/music/test.mp3",
        filename="test",
        title="Bohemian Rhapsody",
        artist="Queen",
        album="A Night at the Opera",
        duration=354.0,
        format="mp3",
        playlist_name="Rock",
    )
    assert song.matches_query("bohemian")
    assert song.matches_query("queen")
    assert song.matches_query("opera")
    assert not song.matches_query("beatles")


def test_playlist_song_count():
    songs = [
        Song(
            path=f"/music/song{i}.mp3",
            filename=f"song{i}",
            title=f"Song {i}",
            artist="Artist",
            album="Album",
            duration=180.0,
            format="mp3",
            playlist_name="Playlist",
        )
        for i in range(5)
    ]
    playlist = Playlist(name="Test", path="/music", songs=songs)
    assert playlist.song_count == 5


def test_playlist_total_duration():
    songs = [
        Song(
            path=f"/music/song{i}.mp3",
            filename=f"song{i}",
            title=f"Song {i}",
            artist="Artist",
            album="Album",
            duration=60.0,
            format="mp3",
            playlist_name="Playlist",
        )
        for i in range(3)
    ]
    playlist = Playlist(name="Test", path="/music", songs=songs)
    assert playlist.total_duration == 180.0
    assert playlist.total_duration_str == "3m 0s"
