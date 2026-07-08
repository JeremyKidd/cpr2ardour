from dataclasses import dataclass

from cpr2ardour.binary import BinaryReader


@dataclass(slots=True)
class Chunk:
    """A chunk in a RIFF-style file."""

    id: str
    size: int
    file_offset: int

    @property
    def data_offset(self) -> int:
        return self.file_offset + 8

    @property
    def end_offset(self) -> int:
        return self.data_offset + self.size


@dataclass(slots=True)
class RiffFile:
    """A RIFF-style file."""

    form_type: str
    root: Chunk

def read_chunk_header(reader: BinaryReader) -> Chunk:
    """Read a chunk header."""
    offset = reader.tell()
    id = reader.read_fourcc()
    size = reader.read_u32_be()

    return Chunk(
        id=id,
        size=size,
        file_offset=offset,
    )


def read_riff(reader: BinaryReader) -> RiffFile:
    magic = reader.read_fourcc()

    if magic != "RIFF":
        raise ValueError(f"Expected 'RIFF' but found '{magic}'.")

    riff_size = reader.read_u32_be()
    form_type = reader.read_fourcc()
    root = read_chunk_header(reader)

    return RiffFile(
        form_type=form_type,
        root=root,
    )

