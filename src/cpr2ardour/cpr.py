from dataclasses import dataclass

from cpr2ardour.binary import BinaryReader
from cpr2ardour.riff import Chunk
from pathlib import Path
import ntpath


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


def read_archive_info(reader: BinaryReader, chunk: Chunk) -> ArchiveInfo:
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
class InitialNames:
    """Initial marker/name records found in the ARCH chunk."""

    names: list[str]


def read_initial_names(
    reader: BinaryReader,
    chunk: Chunk,
) -> InitialNames:
    """Read the initial marker/name records from the ARCH chunk."""

    reader.seek(chunk.data_offset)

    names: list[str] = []

    while True:
        position = reader.tell()
        marker = reader.read_u32_be()

        if marker not in (0xFFFFFFFE, 0xFFFFFFFF):
            reader.seek(position)
            break

        class_name = reader.read_length_prefixed_string().rstrip("\x00")
        names.append(class_name)

        while reader.read(1) == b"\x00":
            pass

        reader.skip(-1)

    return InitialNames(names=names)


@dataclass(slots=True)
class AudioReference:
    """A referenced audio file found in a CPR project."""

    filename: str
    offset: int


def find_audio_references(path: Path) -> list[AudioReference]:
    """Find ASCII .wav file references in a CPR file."""

    data = path.read_bytes()
    lower_data = data.lower()
    references: list[AudioReference] = []

    search_from = 0

    while True:
        extension_offset = lower_data.find(b".wav", search_from)

        if extension_offset == -1:
            break

        reference_end = extension_offset + 4
        reference_start = extension_offset

        # Move backwards over printable ASCII characters.
        while reference_start > 0 and 32 <= data[reference_start - 1] <= 126:
            reference_start -= 1

        raw_reference = data[reference_start:reference_end].decode(
            "ascii",
            errors="replace",
        )

        # A reference may contain a complete Windows path.
        filename = ntpath.basename(raw_reference).strip()

        if filename:
            filename_offset = reference_end - len(
                filename.encode("ascii", errors="replace")
            )

            references.append(
                AudioReference(
                    filename=filename,
                    offset=filename_offset,
                )
            )

        search_from = reference_end

    return references


@dataclass(slots=True)
class ObjectOccurrence:
    """Location of a named object marker in a CPR file."""

    name: str
    offset: int


def find_object_occurrences(
    path: Path,
    object_name: str,
) -> list[ObjectOccurrence]:
    """Find occurrences of an ASCII object name in a CPR file."""

    data = path.read_bytes()
    needle = object_name.encode("ascii")
    occurrences: list[ObjectOccurrence] = []

    start = 0

    while True:
        offset = data.find(needle, start)

        if offset == -1:
            break

        occurrences.append(
            ObjectOccurrence(
                name=object_name,
                offset=offset,
            )
        )

        start = offset + len(needle)

    return occurrences


@dataclass(slots=True)
class AudioTrackInfo:
    """Basic information recovered from an audio track object."""

    object_offset: int
    name: str


def find_audio_tracks(path: Path) -> list[AudioTrackInfo]:
    """Find candidate MAudioTrackEvent objects and recover nearby track names."""

    data = path.read_bytes()
    needle = b"MAudioTrackEvent"
    tracks: list[AudioTrackInfo] = []

    search_from = 0

    while True:
        object_offset = data.find(needle, search_from)

        if object_offset == -1:
            break

        # Ignore schema-style occurrences by looking for a nearby
        # length-prefixed printable string before the next MAudioEvent.
        window_start = object_offset + len(needle)
        window_end = min(len(data), window_start + 160)
        window = data[window_start:window_end]

        audio_event_offset = window.find(b"MAudioEvent")

        if audio_event_offset == -1:
            search_from = object_offset + len(needle)
            continue

        search_end = audio_event_offset

        name: str | None = None

        for offset in range(0, max(0, search_end - 4)):
            length = int.from_bytes(
                window[offset : offset + 4],
                byteorder="big",
            )

            if not 1 <= length <= 128:
                continue

            text_start = offset + 4
            text_end = text_start + length

            if text_end > search_end:
                continue

            raw = window[text_start:text_end].rstrip(b"\x00")

            if not raw:
                continue

            if all(32 <= byte <= 126 for byte in raw):
                candidate = raw.decode("ascii")

                # Avoid accepting the object names themselves.
                if candidate not in {"MAudioEvent", "MAudioTrackEvent"}:
                    name = candidate
                    break

        if name is not None:
            tracks.append(
                AudioTrackInfo(
                    object_offset=object_offset,
                    name=name,
                )
            )

        search_from = object_offset + len(needle)

    return tracks
