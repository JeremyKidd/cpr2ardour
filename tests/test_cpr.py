from pathlib import Path

from cpr2ardour.binary import BinaryReader
from cpr2ardour.cpr import read_root
from cpr2ardour.riff import read_riff


def test_read_root() -> None:
    path = Path("tests/data/Sapphic3.cpr")

    with BinaryReader.open(path) as reader:
        riff = read_riff(reader)
        root = read_root(reader, riff.root)

    assert root.arrangement_name == "Arrangement1"
    assert root.arrangement_type == "PArrangement"