from dataclasses import dataclass

from cpr2ardour.binary import BinaryReader
from cpr2ardour.riff import Chunk


@dataclass(slots=True)
class RootInfo:
    """Information stored in the Cubase ROOT chunk."""

    arrangement_name: str
    arrangement_type: str


def read_root(reader: BinaryReader, chunk: Chunk) -> RootInfo:
    """Read the Cubase ROOT chunk."""

    reader.seek(chunk.data_offset)

    arrangement_name = reader.read_length_prefixed_string()
    arrangement_type = reader.read_length_prefixed_string()

    return RootInfo(
        arrangement_name=arrangement_name,
        arrangement_type=arrangement_type,
    )


@dataclass(slots=True)
class ArchiveInfo:
    """Information discovered in the ARCH chunk."""

    classes: list[str]


def read_archive_info(
    reader: BinaryReader,
    chunk: Chunk,
) -> ArchiveInfo:
    """Read the initial class names from the ARCH chunk."""

    reader.seek(chunk.data_offset)

    classes: list[str] = []

    while True:
        position = reader.tell()
        marker = reader.read_u32_be()

        if marker not in (0xFFFFFFFE, 0xFFFFFFFF):
            # We've reached a different structure.
            reader.seek(position)
            break

        classes.append(reader.read_length_prefixed_string())

        # Skip any padding bytes.
        while reader.read(1) == b"\x00":
            pass
        reader.skip(-1)

    return ArchiveInfo(classes=classes)


@dataclass(slots=True)
class ClassTable:
    """Class names discovered at the start of the ARCH chunk."""

    classes: list[str]


def read_class_table(reader: BinaryReader, chunk: Chunk) -> ClassTable:
    """Read the initial class table from the ARCH chunk."""

    reader.seek(chunk.data_offset)

    classes: list[str] = []

    while True:
        position = reader.tell()
        marker = reader.read_u32_be()

        if marker not in (0xFFFFFFFE, 0xFFFFFFFF):
            reader.seek(position)
            break

        class_name = reader.read_length_prefixed_string().rstrip("\x00")
        classes.append(class_name)

        while reader.read(1) == b"\x00":
            pass

        reader.skip(-1)

    return ClassTable(classes=classes)
