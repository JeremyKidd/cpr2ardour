from pathlib import Path

from cpr2ardour.binary import BinaryReader
from cpr2ardour.cpr import read_root
from cpr2ardour.riff import read_riff

with BinaryReader.open(Path("tests/data/Sapphic3.cpr")) as reader:
    riff = read_riff(reader)
    root = read_root(reader, riff.root)

print(root)