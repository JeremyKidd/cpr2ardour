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
        "--verbose-audio",
        action="store_true",
        help="List individual missing and unreferenced audio files.",
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
            data = reader.read_bytes(192)

            print()
            print(f"Bytes around offset {args.dump_around}")
            print(f"  Start: {start}")
            print(data.hex(" "))

    print_summary(
        args.path,
        riff,
        root,
        arch,
        initial_names,
    )

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

    if args.audio_dir is not None:
        audio_references = find_audio_references(args.path)

        referenced_by_key = {
            reference.filename.casefold(): reference.filename
            for reference in audio_references
        }

        actual_by_key = {
            path.name.casefold(): path.name
            for path in args.audio_dir.iterdir()
            if path.is_file() and path.suffix.casefold() == ".wav"
        }

        missing_keys = referenced_by_key.keys() - actual_by_key.keys()
        unreferenced_keys = actual_by_key.keys() - referenced_by_key.keys()

        missing = sorted(
            (referenced_by_key[key] for key in missing_keys),
            key=str.casefold,
        )

        unreferenced = sorted(
            (actual_by_key[key] for key in unreferenced_keys),
            key=str.casefold,
        )

        recordings, generated_fades, external_resources = classify_missing_audio(
            missing
        )

        print()
        print("Audio directory check")
        print(f"  Referenced in CPR  : {len(referenced_by_key)}")
        print(f"  Present in Audio   : {len(actual_by_key)}")
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
                print("In Audio but not referenced")
                for name in unreferenced:
                    print(f"  {name}")


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
