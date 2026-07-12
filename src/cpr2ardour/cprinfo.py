from argparse import ArgumentParser
from pathlib import Path

from cpr2ardour.binary import BinaryReader
from cpr2ardour.cpr import (
    InitialNames,
    RootInfo,
    find_audio_tracks,
    find_audio_references,
    find_object_occurrences,
    read_initial_names,
    read_root,
    list_classes,
    read_drum_map_entries,
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

    parser.add_argument(
        "--find-audio",
        action="store_true",
        help="Find referenced .wav audio files.",
    )

    parser.add_argument(
        "--audio-dir",
        type=Path,
        help="Path to the Cubase Audio directory.",
    )

    parser.add_argument(
        "--session-dir",
        type=Path,
        metavar="DIR",
        help="Path to the Cubase session directory.",
    )

    parser.add_argument(
        "--verbose-audio",
        action="store_true",
        help="List individual missing and unreferenced audio files.",
    )

    parser.add_argument(
        "--list-classes",
        action="store_true",
        help="List class names found in the ARCH chunk.",
    )

    parser.add_argument(
        "--find-object",
        metavar="NAME",
        help="Find occurrences of an object name in the CPR file.",
    )

    parser.add_argument(
        "--dump-around",
        type=int,
        metavar="OFFSET",
        help="Dump bytes around a file offset.",
    )

    parser.add_argument(
        "--find-track-names",
        action="store_true",
        help="Investigate names near MAudioTrackEvent objects.",
    )

    parser.add_argument(
        "--find-tracks",
        action="store_true",
        help="Find candidate audio track names.",
    )

    parser.add_argument(
        "--inspect-track",
        type=int,
        metavar="OFFSET",
        help="Inspect bytes after an MAudioTrackEvent at OFFSET.",
    )

    parser.add_argument(
        "--inspect-drum-map",
        action="store_true",
        help="Inspect the first drum-map entries.",
    )

    parser.add_argument(
        "--scan-corpus",
        type=Path,
        metavar="DIR",
        help="Scan a directory tree containing Cubase projects and WAV files.",
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

        if args.dump_around is not None:
            start = max(0, args.dump_around - 64)
            reader.seek(start)
            data = reader.read_bytes(320)

            print()
            print(f"Bytes around offset {args.dump_around}")
            print(f"  Start: {start}")
            print(data.hex(" "))

        if args.inspect_track is not None:
            object_offset = args.inspect_track
            start = object_offset + len("MAudioTrackEvent")

            reader.seek(start)
            data = reader.read_bytes(96)

            name_bytes = b"G Vox\x00"
            relative_name_offset = data.find(name_bytes)

            if relative_name_offset != -1:
                name_offset = start + relative_name_offset
                length_offset = name_offset - 4

                length = int.from_bytes(
                    data[relative_name_offset - 4 : relative_name_offset],
                    byteorder="big",
                )

                print()
                print("Track name field")
                print(f"  Length offset : {length_offset}")
                print(f"  Name offset   : {name_offset}")
                print(f"  Stored length : {length}")
                print(f"  Raw value     : {name_bytes!r}")

            print()
            print(f"Track object at offset {object_offset}")
            print(f"Data starts at      : {start}")
            print()

            for row_offset in range(0, len(data), 16):
                row = data[row_offset : row_offset + 16]

                hex_part = " ".join(f"{byte:02x}" for byte in row)
                ascii_part = "".join(
                    chr(byte) if 32 <= byte <= 126 else "." for byte in row
                )

                print(f"{start + row_offset:08x}  {hex_part:<47}  {ascii_part}")

            print()
            print("32-bit big-endian values")

            for offset in range(0, 64, 4):
                value = int.from_bytes(
                    data[offset : offset + 4],
                    byteorder="big",
                )

                print(f"  {start + offset}: {value:#010x} ({value})")

    print_summary(
        args.path,
        riff,
        root,
        arch,
        initial_names,
    )

    if args.inspect_drum_map:
        entries = read_drum_map_entries(args.path)

        print()
        print("Drum-map entries")

        for entry in entries:
            if entry.name == "---":
                continue

            print(f"  {entry.note:3}  {entry.name}")

    if args.find_tracks:
        tracks = find_audio_tracks(args.path)

        print()
        print("Audio tracks")

        for track in tracks:
            print(f"  {track.name} @ offset {track.object_offset}")

    if args.find_track_names:
        data = args.path.read_bytes()
        needle = b"MAudioTrackEvent"
        start = 0

        print()
        print("Candidate audio track objects")

        while True:
            object_offset = data.find(needle, start)

            if object_offset == -1:
                break

            # Ignore the later schema entry for now.
            window_end = min(len(data), object_offset + 128)
            window = data[object_offset:window_end]

            print()
            print(f"  MAudioTrackEvent at offset {object_offset}")

            # Show printable strings found nearby.
            current = bytearray()

            for byte in window:
                if 32 <= byte <= 126:
                    current.append(byte)
                else:
                    if len(current) >= 3:
                        print(f"    {current.decode('ascii')}")
                    current.clear()

            if len(current) >= 3:
                print(f"    {current.decode('ascii')}")

            start = object_offset + len(needle)

    if args.list_classes:
        print()
        print("Classes discovered")
        for name in list_classes(args.path):
            print(f"  {name}")

    if args.find_object is not None:
        occurrences = find_object_occurrences(
            args.path,
            args.find_object,
        )

        print()
        print(f"Object occurrences: {args.find_object}")
        print(f"  Count: {len(occurrences)}")

        for occurrence in occurrences:
            print(f"  Offset: {occurrence.offset}")

    if args.find_audio:
        audio_references = find_audio_references(args.path)

        print(f"Total references : {len(audio_references)}")

        referenced = {ref.filename for ref in audio_references}
        print(f"Unique filenames : {len(referenced)}")

        print()
        print("Audio references")

        for reference in audio_references:
            print(f"  {reference.filename} @ offset {reference.offset}")

    if args.session_dir is not None:
        audio_root = args.session_dir.expanduser()
    elif args.audio_dir is not None:
        audio_root = args.audio_dir.expanduser()
    else:
        audio_root = None

    if audio_root is not None:
        audio_references = find_audio_references(args.path)

        referenced_by_key = {
            reference.filename.casefold(): reference.filename
            for reference in audio_references
        }

        actual_by_key = {
            path.name.casefold(): path for path in audio_root.rglob("*.wav")
        }

        missing_keys = referenced_by_key.keys() - actual_by_key.keys()
        unreferenced_keys = actual_by_key.keys() - referenced_by_key.keys()

        missing = sorted(
            (referenced_by_key[key] for key in missing_keys),
            key=str.casefold,
        )

        unreferenced = sorted(
            (actual_by_key[key] for key in unreferenced_keys),
            key=lambda path: path.name.casefold(),
        )

        recordings, generated_fades, external_resources = classify_missing_audio(
            missing
        )

        print()
        print("Session media check")
        print(f"  Session directory : {audio_root}")
        print(f"  Unique names referenced : {len(referenced_by_key)}")
        print(f"  WAV files found   : {len(actual_by_key)}")
        print(f"  Missing source recordings : {len(recordings)}")
        print(f"  Missing fades      : {len(generated_fades)}")
        print(f"  Missing external   : {len(external_resources)}")
        print(f"  Unreferenced       : {len(unreferenced)}")

        if args.verbose_audio:
            if recordings:
                print()
                print("Missing original recordings")

                for name in recordings:
                    print(f"  {name}")

            if generated_fades:
                print()
                print("Missing generated fades")
                for name in generated_fades:
                    print(f"  {name}")

            if external_resources:
                print()
                print("Missing external resources")
                for name in external_resources:
                    print(f"  {name}")

            if unreferenced:
                print()
                print("In session but not referenced")

                for path in unreferenced:
                    print(f"  {path.relative_to(audio_root)}")


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


def classify_missing_audio(
    filenames: list[str],
) -> tuple[list[str], list[str], list[str]]:
    """Classify missing audio references."""

    generated_fades: list[str] = []
    external_resources: list[str] = []
    recordings: list[str] = []

    for filename in filenames:
        if filename.startswith(("FadeIn", "FadeOut")):
            generated_fades.append(filename)
        elif filename.casefold() in {"hiclave.wav", "lowclave.wav"}:
            external_resources.append(filename)
        else:
            recordings.append(filename)

    return recordings, generated_fades, external_resources


if __name__ == "__main__":
    main()
