from dataclasses import dataclass
from pathlib import Path
from cpr2ardour.cpr import find_audio_references


@dataclass(slots=True)
class CorpusProject:
    """One CPR project found in a corpus."""

    path: Path
    audio_references: set[str]


@dataclass(slots=True)
class CorpusReport:
    """Summary of a directory containing Cubase projects and media."""

    root: Path
    projects: list[CorpusProject]
    wav_locations: dict[str, list[Path]]


def scan_corpus(root: Path) -> CorpusReport:
    """Scan a directory tree for CPR projects and WAV files."""

    root = root.expanduser()

    projects: list[CorpusProject] = []

    for cpr_path in sorted(root.rglob("*.cpr")):
        references = {
            reference.filename for reference in find_audio_references(cpr_path)
        }

        projects.append(
            CorpusProject(
                path=cpr_path,
                audio_references=references,
            )
        )

    wav_locations: dict[str, list[Path]] = {}

    for wav_path in sorted(root.rglob("*")):
        if not wav_path.is_file():
            continue

        if wav_path.suffix.casefold() != ".wav":
            continue

        key = wav_path.name.casefold()
        wav_locations.setdefault(key, []).append(wav_path)

    return CorpusReport(
        root=root,
        projects=projects,
        wav_locations=wav_locations,
    )
