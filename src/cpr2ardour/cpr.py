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