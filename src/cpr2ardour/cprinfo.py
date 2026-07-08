from pathlib import Path

from cpr2ardour.binary import BinaryReader
from cpr2ardour.cpr import read_root
from cpr2ardour.riff import read_chunk_header, read_riff


def main() -> None:
    path = Path("tests/data/Sapphic3.cpr")

    with BinaryReader.open(path) as reader:
        riff = read_riff(reader)
        root = read_root(reader, riff.root)

        print(root)
        print("Reader position:", reader.tell())
        print("ROOT ends at    :", riff.root.end_offset)

        next_chunk = read_chunk_header(reader)
        print(next_chunk)

        reader.seek(next_chunk.data_offset)
        data = reader.read_bytes(64)

        print(data)
        print(data.hex(" "))

        reader.seek(next_chunk.data_offset)

        for _ in range(20):
            position = reader.tell()
            marker = reader.read_u32_be()

            if marker not in (0xFFFFFFFE, 0xFFFFFFFF):
                print("Stopped at", position, "marker:", hex(marker))
                break

            text = reader.read_length_prefixed_string()
            print(hex(marker), text, "position:", reader.tell())

            while reader.read(1) == b"\x00":
                pass

            reader.skip(-1)


if __name__ == "__main__":
    main()