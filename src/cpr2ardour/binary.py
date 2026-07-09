from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


@dataclass(slots=True)
class BinaryReader:
    """Read binary data from a file."""

    path: Path
    file: BinaryIO

    @classmethod
    def open(cls, path: Path) -> "BinaryReader":
        """Open a binary file."""
        return cls(
            path=path,
            file=path.open("rb"),
        )

    def close(self) -> None:
        """Close the file."""
        self.file.close()

    def read(self, size: int) -> bytes:
        """Read exactly *size* bytes."""

        data = self.file.read(size)

        if len(data) != size:
            raise EOFError(f"Expected {size} bytes but only read {len(data)}.")

        return data

    def tell(self) -> int:
        """Return the current position in the file."""
        return self.file.tell()

    def seek(self, position: int) -> None:
        """Move to an absolute position in the file."""
        self.file.seek(position)

    def skip(self, size: int) -> None:
        """Skip forward by *size* bytes."""
        self.file.seek(size, 1)

    def read_fourcc(self) -> str:
        """Read a Four Character Code (FourCC)."""
        return self.read(4).decode("ascii")

    def read_u32_be(self) -> int:
        """Read a 32-bit unsigned integer (big-endian)."""
        return int.from_bytes(self.read(4), byteorder="big")

    def read_bytes(self, size: int) -> bytes:
        """Read raw bytes."""
        return self.read(size)

    def read_string(self, size: int) -> str:
        """Read an ASCII string of *size* bytes."""
        return self.read(size).decode("ascii")

    def read_length_prefixed_string(self) -> str:
        """Read a big-endian length-prefixed ASCII string."""
        length = self.read_u32_be()
        return self.read_string(length)

    def remaining(self, end_offset: int) -> int:
        """Return the number of bytes remaining until end_offset."""
        return end_offset - self.tell()

    def __enter__(self) -> "BinaryReader":
        """Enter a context manager."""
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Exit a context manager."""
        self.close()
