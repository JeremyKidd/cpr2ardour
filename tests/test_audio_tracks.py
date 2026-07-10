from pathlib import Path

from cpr2ardour.cpr import find_audio_tracks


def test_find_audio_tracks() -> None:
    path = Path("tests/data/Sapphic3.cpr")

    tracks = find_audio_tracks(path)

    assert [(track.name, track.object_offset) for track in tracks] == [
        ("G Vox", 112231),
    ]
