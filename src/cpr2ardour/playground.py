from pathlib import Path

from cpr2ardour.binary import BinaryReader

reader = BinaryReader.open(Path("tests/data/Sapphic3.cpr"))

print(reader.read(4))

reader.close()