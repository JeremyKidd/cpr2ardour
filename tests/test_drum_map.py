from pathlib import Path

from cpr2ardour.cpr import read_drum_map_entries


def test_read_drum_map_entries() -> None:
    path = Path("/home/jeremy/Music/2007CubaseSessions/Black Sheep/Black Sheep kit.cpr")

    entries = read_drum_map_entries(path)

    assert len(entries) == 128
    assert entries[35].name == "Acoustic Bass Drum"
    assert entries[36].name == "Bass Drum"
    assert entries[38].name == "Acoustic Snare"
    assert entries[42].name == "Closed Hi-Hat"
