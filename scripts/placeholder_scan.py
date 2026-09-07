"""Fail the build if any document still contains a placeholder.

WHY THIS IS A GATE AND NOT A LINT
---------------------------------
UPLIFT generates coursework artefacts — a report, a deck outline, a viva sheet —
from the same documents a reader is invited to check. A single "TBD" that
survives into a generated report is worse than a missing section: it looks like
finished work and is not. So this runs inside `make check`, before any artefact
can be built, and it fails rather than warns.

It deliberately scans only prose the project publishes (docs/, README.md).
Source code is allowed to say TODO; a document is not.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Each pattern is matched case-insensitively against a whole line.
PATTERNS: dict[str, re.Pattern[str]] = {
    "TBD": re.compile(r"\bTBD\b", re.I),
    "TODO": re.compile(r"\bTODO\b", re.I),
    "FIXME": re.compile(r"\bFIXME\b", re.I),
    "XXX": re.compile(r"\bXXX\b"),
    "lorem ipsum": re.compile(r"\blorem ipsum\b", re.I),
    "angle-bracket placeholder": re.compile(
        r"<(?:placeholder|your[- ]|insert |name of )[^>]*>", re.I
    ),
    "coming soon": re.compile(r"\bcoming soon\b", re.I),
    "ellipsis stub": re.compile(r"^\s*\.\.\.\s*$"),
}

SCAN: tuple[Path, ...] = (ROOT / "docs", ROOT / "README.md")

#: Plans are working documents that legitimately contain unticked checkboxes and
#: the word TODO. They are excluded, and the exclusion is narrow and named.
EXCLUDE_DIRS = {"superpowers", "results"}


def _files() -> list[Path]:
    out: list[Path] = []
    for target in SCAN:
        if target.is_file():
            out.append(target)
        elif target.is_dir():
            out.extend(
                p
                for p in target.rglob("*.md")
                if not EXCLUDE_DIRS & set(p.relative_to(target).parts)
            )
    return sorted(out)


def main() -> int:
    hits: list[str] = []
    for path in _files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for label, pattern in PATTERNS.items():
                if pattern.search(line):
                    rel = path.relative_to(ROOT)
                    hits.append(f"{rel}:{lineno}: {label} — {line.strip()[:90]}")

    if hits:
        print(f"placeholder scan FAILED — {len(hits)} placeholder(s) in published documents:\n")
        for hit in hits:
            print(f"  {hit}")
        print("\nA generated artefact must not contain any of these.")
        return 1

    print(f"placeholder scan clean — {len(_files())} document(s) checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
