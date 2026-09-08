"""`.env.example` names every variable the code reads, and no others.

A template drifts silently in both directions and both hurt a future operator:
a variable the code reads but the template omits is a setting they never knew to
set, and one the template lists but nothing reads sends them hunting for an
effect that does not exist. This repository had four of the first and three of
the second before the archival pass.

The scan is deliberately literal about indirection: `identity.py` reads its
variable through a module constant, so a naive grep for `getenv("...")` misses
it entirely — which is exactly how UPLIFT_SIGNING_SECRET went undeclared.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("services", "pipeline", "scripts")
#: The web app reads its own configuration through process.env, so a scanner
#: that walks Python only reports NEXT_PUBLIC_API_BASE as dead. It is not.
WEB_SOURCES = ("apps/web/lib", "apps/web/next.config.ts", "apps/web/playwright.config.ts")

#: Set by the platform or by a person on a command line, never by this project.
EXTERNAL = frozenset({"VERCEL", "PATH", "HOME", "PORT", "CI"})

DIRECT = re.compile(r'(?:getenv|environ\.get)\(\s*"([A-Z][A-Z0-9_]{2,})"')
#: `ENV_VAR = "UPLIFT_SIGNING_SECRET"` then `os.getenv(ENV_VAR, "")`.
INDIRECT = re.compile(r'^[A-Z][A-Z0-9_]*\s*=\s*"([A-Z][A-Z0-9_]{2,})"\s*$', re.MULTILINE)
WEB = re.compile(r"process\.env\.([A-Z][A-Z0-9_]{2,})")

#: Declared on purpose while nothing reads it. The list is short and each entry
#: states why, because "it is in the allowlist" is how a genuinely dead variable
#: survives a test written to find dead variables.
DECLARED_BUT_UNREAD = {
    # available() is a hardcoded `return False`; the key is never consulted, and
    # the variable is declared so the disabled paid provider is visible.
    "ANTHROPIC_API_KEY",
    # Named on a command line for `make smoke-live`, never loaded from a file.
    "LIVE_API_URL",
    "LIVE_WEB_URL",
}


def _read_by_code() -> set[str]:
    found: set[str] = set()
    for root in SOURCES:
        for path in (ROOT / root).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            found |= set(DIRECT.findall(text))
            # Only count an indirect constant if it is actually passed to getenv.
            for name in INDIRECT.findall(text):
                if "getenv(" in text or "environ" in text:
                    found.add(name)
    for entry in WEB_SOURCES:
        target = ROOT / entry
        paths = target.rglob("*.ts") if target.is_dir() else [target]
        for path in paths:
            if path.exists():
                found |= set(WEB.findall(path.read_text(encoding="utf-8")))
    return {n for n in found if n not in EXTERNAL}


def _declared() -> set[str]:
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    return set(re.findall(r"^([A-Z][A-Z0-9_]{2,})=", text, re.MULTILINE))


def test_every_variable_the_code_reads_is_declared():
    missing = _read_by_code() - _declared()
    assert not missing, (
        f"read by the code but absent from .env.example: {sorted(missing)}. "
        "A future operator cannot set what the template does not name."
    )


def test_no_declared_variable_is_dead():
    dead = _declared() - _read_by_code() - DECLARED_BUT_UNREAD
    assert not dead, (
        f"declared in .env.example but read nowhere: {sorted(dead)}. "
        "Remove it, or the next operator configures a setting with no effect."
    )


def test_the_template_carries_no_values_that_look_real():
    """A committed secret is a secret in every clone and every downloaded zip."""
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() in {"OLLAMA_HOST", "NEXT_PUBLIC_API_BASE", "CORS_ORIGINS", "UPLIFT_DB"}:
            continue  # non-secret defaults, useful as written
        assert len(value.strip()) < 40, f"{key} carries something long enough to be a real key"
        assert not re.fullmatch(r"[0-9a-f]{32,}", value.strip()), f"{key} looks like a real secret"
