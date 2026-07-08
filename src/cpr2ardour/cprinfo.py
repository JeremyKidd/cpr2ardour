from pathlib import Path

from cpr2ardour.binary import BinaryReader
from cpr2ardour.cpr import read_root
from cpr2ardour.riff import read_riff


def main() -> None:
    path = Path("tests/data/Sapphic3.cpr")

    with BinaryReader.open(path) as reader:
        riff = read_riff(reader)
        root = read_root(reader, riff.root)

    print(root)


if __name__ == "__main__":
    main()