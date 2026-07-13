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


def project_similarity(
    first_references: set[str],
    second_references: set[str],
) -> tuple[float, int, int]:
    """Compare two sets of referenced WAV filenames."""

    first = {name.casefold() for name in first_references}
    second = {name.casefold() for name in second_references}

    shared = first & second
    combined = first | second

    if not combined:
        return 1.0, 0, 0

    score = len(shared) / len(combined)

    return score, len(shared), len(combined)


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

    parser.add_argument(
        "--find-wav",
        metavar="NAME",
        help="Show which CPR projects reference a WAV and where it exists.",
    )

    parser.add_argument(
        "--find-project",
        metavar="NAME",
        help="Show CPR files and media summary for matching project directories.",
    )

    parser.add_argument(
        "--compare-projects",
        metavar="NAME",
        help="Compare the media-reference similarity of matching CPR projects.",
    )

    parser.add_argument(
        "--show-project-missing",
        action="store_true",
        help="List missing WAV names for projects matched by --find-project.",
    )

    parser.add_argument(
        "--closest-projects",
        metavar="NAME",
        help="Show the closest media-reference match for each matching CPR project.",
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

    if args.find_wav is not None:
        query = args.find_wav.casefold()

        referenced_by = [
            project.path
            for project in report.projects
            if query in {name.casefold() for name in project.audio_references}
        ]

        found_at = report.wav_locations.get(query, [])

        print()
        print(f"WAV: {args.find_wav}")

        print()
        print("Referenced by")

        if referenced_by:
            for project_path in referenced_by:
                print(f"  {project_path.relative_to(report.root)}")
        else:
            print("  (none)")

        print()
        print("Found in")

        if found_at:
            for wav_path in found_at:
                print(f"  {wav_path.relative_to(report.root)}")
        else:
            print("  (missing)")

    if args.find_project is not None:
        query = args.find_project.casefold()

        matching_projects = [
            project
            for project in report.projects
            if query in project.path.stem.casefold()
            or query in project.path.parent.name.casefold()
        ]

        print()
        print(f"Project search: {args.find_project}")

        if not matching_projects:
            print("  No matching CPR projects found.")
        else:
            for project in matching_projects:
                referenced_keys = {name.casefold() for name in project.audio_references}

                found_keys = {
                    key for key in referenced_keys if key in report.wav_locations
                }

                missing_keys = referenced_keys - found_keys

                print()
                print(project.path.relative_to(report.root))
                print(f"  Referenced WAVs : {len(referenced_keys)}")
                print(f"  Found in corpus : {len(found_keys)}")
                print(f"  Missing         : {len(missing_keys)}")
                if args.show_project_missing and missing_keys:
                    print("  Missing WAVs")

                    for key in sorted(missing_keys):
                        print(f"    {key}")

    if args.compare_projects is not None:
        query = args.compare_projects.casefold()

        matching_projects = [
            project
            for project in report.projects
            if query in project.path.stem.casefold()
            or query in project.path.parent.name.casefold()
        ]

        print()
        print(f"Project similarity: {args.compare_projects}")

        if len(matching_projects) < 2:
            print("  Fewer than two matching CPR projects were found.")
        else:
            comparisons: list[tuple[float, int, int, Path, Path]] = []

            for first_index, first in enumerate(matching_projects):
                for second in matching_projects[first_index + 1 :]:
                    score, shared_count, combined_count = project_similarity(
                        first.audio_references,
                        second.audio_references,
                    )

                    comparisons.append(
                        (
                            score,
                            shared_count,
                            combined_count,
                            first.path,
                            second.path,
                        )
                    )

            comparisons.sort(
                key=lambda item: item[0],
                reverse=True,
            )

            for (
                score,
                shared_count,
                combined_count,
                first_path,
                second_path,
            ) in comparisons:
                print()
                print(f"  {first_path.relative_to(report.root)}")
                print(f"  {second_path.relative_to(report.root)}")
                print(f"    Similarity : {score:.1%}")
                print(f"    Shared WAVs: {shared_count}")
                print(f"    Combined   : {combined_count}")

    if args.closest_projects is not None:
        query = args.closest_projects.casefold()

        matching_projects = [
            project
            for project in report.projects
            if query in project.path.stem.casefold()
            or query in project.path.parent.name.casefold()
        ]

        print()
        print(f"Closest project matches: {args.closest_projects}")

        if len(matching_projects) < 2:
            print("  Fewer than two matching CPR projects were found.")
        else:
            for project in matching_projects:
                candidates: list[tuple[float, int, int, Path]] = []

                for other in matching_projects:
                    if other is project:
                        continue

                    score, shared_count, combined_count = project_similarity(
                        project.audio_references,
                        other.audio_references,
                    )

                    candidates.append(
                        (
                            score,
                            shared_count,
                            combined_count,
                            other.path,
                        )
                    )

                candidates.sort(
                    key=lambda item: item[0],
                    reverse=True,
                )

                score, shared_count, combined_count, closest_path = candidates[0]

                print()
                print(f"  {project.path.relative_to(report.root)}")
                print(f"    Closest     : {closest_path.relative_to(report.root)}")
                print(f"    Similarity  : {score:.1%}")
                print(f"    Shared WAVs : {shared_count}")
                print(f"    Combined    : {combined_count}")


if __name__ == "__main__":
    main()
