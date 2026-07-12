from argparse import ArgumentParser
from pathlib import Path

from cpr2ardour.corpus import scan_corpus
import re


def group_missing_files(missing: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    """Group numbered filename families such as kick_00.wav."""

    pattern = re.compile(
        r"^(?P<prefix>.+?)_(?P<number>\d+)\.wav$",
        re.IGNORECASE,
    )

    grouped: dict[str, list[str]] = {}
    singles: list[str] = []

    for name in missing:
        match = pattern.match(name)

        if match:
            prefix = match.group("prefix").lower()
            grouped.setdefault(prefix, []).append(name)
        else:
            singles.append(name)

    return grouped, singles


def main() -> None:
    parser = ArgumentParser(
        prog="cprcorpus",
        description="Inspect a collection of Cubase CPR projects.",
    )
    parser.add_argument(
        "root",
        type=Path,
        help="Root directory of the Cubase session corpus.",
    )
    parser.add_argument(
        "--show-missing",
        action="store_true",
        help="List WAV files referenced by CPRs but not found anywhere in the corpus.",
    )

    args = parser.parse_args()
    report = scan_corpus(args.root)

    all_references = {
        name.casefold()
        for project in report.projects
        for name in project.audio_references
    }

    missing = sorted(
        name for name in all_references if name not in report.wav_locations
    )

    print("Cubase corpus")
    print()
    print(f"Root                 : {report.root}")
    print(f"CPR projects         : {len(report.projects)}")
    print(f"Unique WAV references: {len(all_references)}")
    print(f"Unique WAV names found: {len(report.wav_locations)}")
    print(f"Missing everywhere   : {len(missing)}")
    if args.show_missing:
        grouped, singles = group_missing_files(missing)

        print()
        print("Missing WAV files")

        if grouped:
            print()
            print("Grouped filename families")

            for prefix in sorted(grouped):
                print(f"  {prefix}_*.wav : {len(grouped[prefix])}")

        if singles:
            print()
            print("Individual files")

            for name in singles:
                print(f"  {name}")


if __name__ == "__main__":
    main()
