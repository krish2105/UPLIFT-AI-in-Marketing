"""The repository must contain what it needs to rebuild itself.

WHY THIS EXISTS
---------------
A deployed build failed with FileNotFoundError on
data/raw/dubai_events_seed.yaml — a curated input the events pipeline cannot run
without. The file was on the developer's disk, `git status` was clean, and
nothing inside the repository revealed the problem: a GLOBAL gitignore at
~/.gitignore_global excluded `data/raw/` for every repository on the machine.

That is the worst shape a bug can take. It is invisible locally, it only appears
on a machine that has never seen the developer's home directory, and the symptom
is a runtime error in a pipeline rather than anything a linter would look at.

So this asserts the property directly: every file the project needs in order to
rebuild itself is tracked by git. It runs in `make check`, which means it runs
before a push rather than after a deploy.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

#: Inputs the pipelines and generators cannot run without. Each is CURATED or
#: authored — none can be re-derived by re-running something.
REQUIRED: tuple[str, ...] = (
    "data/brand/sidra.yaml",
    "data/raw/dubai_events_seed.yaml",
    "data/pos_sample.csv",
    "pyproject.toml",
    "uv.lock",
    "render.yaml",
    "Makefile",
    "apps/web/package.json",
    "apps/web/package-lock.json",
    "apps/web/styles/tokens.css",
)

#: Measured results every document quotes. A missing one makes the report
#: generator refuse, which is correct — but better caught here.
REQUIRED_RESULTS: tuple[str, ...] = (
    "A2-contrast",
    "A9-embedding-spike",
    "A10-palette",
    "B1-forecast",
    "B1-forward",
    "B2-segments",
    "B3-allocator",
    "B4-uplift",
    "C1-compliance",
)


def tracked() -> set[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
    return set(out.stdout.splitlines())


@pytest.fixture(scope="module")
def files() -> set[str]:
    return tracked()


@pytest.mark.parametrize("path", REQUIRED)
def test_a_required_input_is_tracked(files: set[str], path: str):
    assert (ROOT / path).exists(), f"{path} is missing from the working tree"
    assert path in files, (
        f"{path} exists on disk but is NOT tracked by git. Check for a global "
        "gitignore — `git check-ignore -v <path>` names the file and line that "
        "excluded it. A clean `git status` does not mean the repository is complete."
    )


@pytest.mark.parametrize("name", REQUIRED_RESULTS)
def test_a_quoted_result_is_tracked(files: set[str], name: str):
    path = f"docs/results/{name}.json"
    assert (ROOT / path).exists(), f"{path} has not been generated"
    assert path in files, f"{path} is generated but not committed"


def test_the_events_pipeline_can_find_its_seed():
    """The specific failure, pinned. The pipeline resolves this path relative to
    the repository root, so it breaks identically on any machine that clones."""
    from pipeline.events import SEED

    assert SEED.exists(), f"{SEED} is missing"
    assert str(SEED.relative_to(ROOT)) in tracked()


def test_nothing_the_build_needs_lives_only_in_a_gitignored_directory():
    """A broader sweep: any Python file under pipeline/ or scripts/ that opens a
    path under data/ must open something git has."""
    import re

    referenced: set[str] = set()
    for source in list((ROOT / "pipeline").rglob("*.py")) + list((ROOT / "scripts").rglob("*.py")):
        for match in re.finditer(r'"(data/[\w./-]+\.(?:yaml|csv|json))"', source.read_text()):
            referenced.add(match.group(1))

    files = tracked()
    missing = [
        p
        for p in sorted(referenced)
        if (ROOT / p).exists() and p not in files and not p.startswith("data/processed/")
    ]
    assert not missing, f"referenced by a pipeline, present on disk, and not committed: {missing}"
