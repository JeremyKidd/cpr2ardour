from dataclasses import dataclass

from cpr2ardour.binary import BinaryReader

RIFF_HEADER_SIZE = 12


@dataclass(slots=True)
class RiffFile:
    """A RIFF-style file."""

    form_type: str

class Chunk:
    """A chunk in a RIFF-style file."""

    chunk_id: str
    size: int
    file_offset: int

    @property
    def data_offset(self) -> int:
        return self.file_offset + 8

    @property
    def end_offset(self) -> int:
        return self.data_offset + self.size


def read_chunk_header(reader: BinaryReader) -> Chunk:
    """Read a chunk header."""
    offset = reader.tell()
    chunk_id = reader.read_fourcc()
    size = reader.read_u32_be()

    return Chunk(
        chunk_id=chunk_id,
        size=size,
        file_offset=offset,
    )

def read_riff(reader: BinaryReader) -> RiffFile:
    """Read the RIFF file header."""

    magic = reader.read_fourcc()

    if magic != "RIFF":
        raise ValueError(
            f"Expected 'RIFF' but found '{magic}'."
        )

    reader.read_u32_be()

    form_type = reader.read_fourcc()

    return RiffFile(form_type=form_type)

