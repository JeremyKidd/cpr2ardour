from pathlib import Path

from cpr2ardour.binary import BinaryReader
from cpr2ardour.riff import read_riff


with BinaryReader.open(Path("tests/data/Sapphic3.riff")) as reader:
    riff = read_riff(reader)

    reader.seek(riff.root.data_offset)

    first = reader.read_length_prefixed_string()
    second = reader.read_length_prefixed_string()

    print(first)
    print(second)