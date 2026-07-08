from argparse import ArgumentParser
from pathlib import Path

from cpr2ardour.binary import BinaryReader
from cpr2ardour.cpr import (
    ClassTable,
    RootInfo,
    read_class_table,
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

    args = parser.parse_args()

    with BinaryReader.open(args.path) as reader:
        riff = read_riff(reader)
        root = read_root(reader, riff.root)
        arch = read_chunk_header(reader)
        class_table = read_class_table(reader, arch)

    print_summary(
        args.path,
        riff,
        root,
        arch,
        class_table,
    )


def print_summary(
    path: Path,
    riff: RiffFile,
    root: RootInfo,
    arch: Chunk,
    class_table: ClassTable,
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
    print("Classes")

    for name in class_table.classes:
        print(f"  {name}")


if __name__ == "__main__":
    main()
