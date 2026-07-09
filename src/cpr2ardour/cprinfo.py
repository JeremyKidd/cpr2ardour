from argparse import ArgumentParser
from pathlib import Path

from cpr2ardour.binary import BinaryReader
from cpr2ardour.cpr import (
    InitialNames,
    RootInfo,
    read_initial_names,
    read_root,
)
from cpr2ardour.riff import Chunk, RiffFile, read_chunk_header, read_riff


def main() -> None:
    parser = ArgumentParser(
        prog="cprinfo",
        description="Inspect a Cubase CPR project file.",
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to a Cubase .cpr file.",
    )

    parser.add_argument(
        "--dump-arch",
        type=int,
        metavar="BYTES",
        help="Dump the first BYTES of the ARCH chunk.",
    )

    args = parser.parse_args()

    with BinaryReader.open(args.path) as reader:
        riff = read_riff(reader)
        root = read_root(reader, riff.root)
        arch = read_chunk_header(reader)
        initial_names = read_initial_names(reader, arch)

        if args.dump_arch is not None:
            reader.seek(arch.data_offset)
            data = reader.read_bytes(args.dump_arch)

            print()
            print("ARCH dump")
            print(data.hex(" "))

        position = reader.tell()
        data = reader.read_bytes(256)

        print("After class table")
        print("  Offset:", position)
        print("  Bytes :", data.hex(" "))
        print()

    print_summary(
        args.path,
        riff,
        root,
        arch,
        initial_names,
    )


def print_summary(
    path: Path,
    riff: RiffFile,
    root: RootInfo,
    arch: Chunk,
    initial_names: InitialNames,
) -> None:
    """Print a summary of a Cubase project."""

    print("CPR Information")
    print()

    print(f"File        : {path}")
    print(f"RIFF form   : {riff.form_type}")
    print()

    print("ROOT")
    print(f"  Arrangement : {root.arrangement_name}")
    print(f"  Type        : {root.arrangement_type}")
    print()

    print("ARCH")
    print(f"  Offset      : {arch.file_offset}")
    print(f"  Size        : {arch.size} bytes")

    print()
    print("Initial names")

    for name in initial_names.names:
        print(f"  {name}")


if __name__ == "__main__":
    main()
