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


@dataclass(slots=True)
class DrumMapEntry:
    """One MIDI-note entry from a Cubase drum map."""

    note: int
    name: str
    size: int
    file_offset: int
    trailer: bytes


def read_drum_map_entries(path: Path) -> list[DrumMapEntry]:
    """Read observed PDrumMapEntry records from a Cubase project."""

    data = path.read_bytes()
    anchor = data.find(b"PDrumMapEntry\x00")

    if anchor == -1:
        return []

    position = data.find(
        b"\x00\x00\x00\x25",
        anchor + len(b"PDrumMapEntry\x00"),
    )

    if position == -1:
        return []

    entries: list[DrumMapEntry] = []

    for _ in range(128):
        if position + 4 > len(data):
            break

        size = int.from_bytes(
            data[position : position + 4],
            byteorder="big",
        )

        if not 1 <= size <= 256:
            break

        record_start = position + 4
        record_end = record_start + size

        if record_end > len(data):
            break

        record = data[record_start:record_end]

        note = record[3]
        name = "<unknown>"

        for offset in range(0, len(record) - 4):
            length = int.from_bytes(
                record[offset : offset + 4],
                byteorder="big",
            )

            if not 1 <= length <= 64:
                continue

            text_start = offset + 4
            text_end = text_start + length

            if text_end > len(record):
                continue

            raw = record[text_start:text_end].rstrip(b"\x00")

            if raw and all(32 <= byte <= 126 for byte in raw):
                name = raw.decode("ascii")
                break

        trailer = data[record_end : record_end + 4]

        entries.append(
            DrumMapEntry(
                note=note,
                name=name,
                size=size,
                file_offset=record_start,
                trailer=trailer,
            )
        )

        position = record_end + 4

    return entries


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

        window_start = object_offset + len(needle)
        window_end = min(len(data), window_start + 320)
        window = data[window_start:window_end]

        audio_event_offset = window.find(b"MAudioEvent")

        if audio_event_offset == -1:
            search_from = object_offset + len(needle)
            continue

        search_end = audio_event_offset
        name: str | None = None

        # First try the MListNode layout seen in Everyone Knows.cpr.
        list_node_offset = window.find(b"MListNode")

        if list_node_offset != -1:
            list_search_start = list_node_offset + len(b"MListNode")
            list_search_end = min(
                search_end,
                list_search_start + 64,
            )

            for offset in range(
                list_search_start,
                max(list_search_start, list_search_end - 4),
            ):
                length = int.from_bytes(
                    window[offset : offset + 4],
                    byteorder="big",
                )

                if not 1 <= length <= 128:
                    continue

                text_start = offset + 4
                text_end = text_start + length

                if text_end > list_search_end:
                    continue

                raw = window[text_start:text_end].rstrip(b"\x00")

                if raw and all(32 <= byte <= 126 for byte in raw):
                    name = raw.decode("ascii")
                    break

        # If that did not work, use the older layout seen in Sapphic3.cpr.
        if name is None:
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

                    if candidate not in {
                        "MAudioEvent",
                        "MAudioTrackEvent",
                        "MListNode",
                    }:
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


def list_classes(path: Path) -> list[str]:
    """Return likely Cubase class names from marker/name records."""

    data = path.read_bytes()
    names: set[str] = set()

    for marker in (b"\xff\xff\xff\xfe", b"\xff\xff\xff\xff"):
        search_from = 0

        while True:
            marker_offset = data.find(marker, search_from)

            if marker_offset == -1:
                break

            length_offset = marker_offset + 4

            if length_offset + 4 > len(data):
                break

            length = int.from_bytes(
                data[length_offset : length_offset + 4],
                byteorder="big",
            )

            text_start = length_offset + 4
            text_end = text_start + length

            if 1 <= length <= 128 and text_end <= len(data):
                raw = data[text_start:text_end].rstrip(b"\x00")

                if raw and all(32 <= byte <= 126 for byte in raw):
                    try:
                        name = raw.decode("ascii")
                    except UnicodeDecodeError:
                        pass
                    else:
                        names.add(name)

            search_from = marker_offset + 4

    return sorted(names)


def inspect_drum_map_entries(
    path: Path,
    limit: int = 128,
) -> None:
    """Print the first few observed PDrumMapEntry records."""

    data = path.read_bytes()
    anchor = data.find(b"PDrumMapEntry\x00")

    if anchor == -1:
        print("PDrumMapEntry was not found.")
        return

    position = data.find(
        b"\x00\x00\x00\x25",
        anchor + len(b"PDrumMapEntry\x00"),
    )

    if position == -1:
        print("No drum-map records were found.")
        return

    for entry_number in range(limit):
        size = int.from_bytes(
            data[position : position + 4],
            byteorder="big",
        )

        if not 1 <= size <= 256:
            print(f"Stopped at offset {position}: implausible record size {size}.")
            break

        record_start = position + 4
        record_end = record_start + size
        record = data[record_start:record_end]

        if len(record) != size:
            print("Stopped at the end of the file.")
            break

        note_values = tuple(record[3:6])

        name = "<unknown>"

        for offset in range(0, len(record) - 4):
            length = int.from_bytes(
                record[offset : offset + 4],
                byteorder="big",
            )

            text_start = offset + 4
            text_end = text_start + length

            if not 1 <= length <= 32:
                continue

            if text_end > len(record):
                continue

            raw = record[text_start:text_end].rstrip(b"\x00")

            if raw and all(32 <= byte <= 126 for byte in raw):
                name = raw.decode("ascii")
                break

        trailer = data[record_end : record_end + 4]

        print(
            f"Entry {entry_number:3}: "
            f"size={size}, "
            f"values={note_values!r}, "
            f"name={name!r}, "
            f"offset={record_start}, "
            f"trailer={trailer.hex(' ')}"
        )

        position = record_end + 4
