from pathlib import Path

from cpr2ardour.binary import BinaryReader
from cpr2ardour.cpr import read_class_table, read_root
from cpr2ardour.riff import read_chunk_header, read_riff


def test_read_class_table() -> None:
    path = Path("tests/data/Sapphic3.cpr")

    with BinaryReader.open(path) as reader:
        riff = read_riff(reader)
        read_root(reader, riff.root)

        arch = read_chunk_header(reader)
        table = read_class_table(reader, arch)

    assert table.classes == [
        "GDocument",
        "GModel",
        "FShared",
        "CmObject",
        "PArrangement",
    ]
