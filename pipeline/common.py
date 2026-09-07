"""Shared pipeline machinery: cached HTTP, and the results record.

CACHING IS NOT AN OPTIMISATION HERE
-----------------------------------
Every raw response is written to data/raw/ before anything parses it. That is
what makes a run reproducible and what makes a licence claim checkable: the
bytes the provider actually returned, on the date recorded in
docs/datasets.md, are on disk. It also means re-running a pipeline after a
parsing change does not hit the provider again, which is the courteous way to
use a free API with no key.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RESULTS = ROOT / "docs" / "results"

USER_AGENT = (
    "UPLIFT-MAWSIM/0.1 (SP Jain MAIB AI 208 coursework; "
    "https://github.com/krish2105/UPLIFT-AI-in-Marketing)"
)


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def fetch_json(
    url: str,
    params: dict[str, Any],
    *,
    cache_key: str,
    refresh: bool = False,
    timeout: float = 90.0,
) -> Any:
    """GET JSON, caching the raw bytes under data/raw/.

    The cache key includes a hash of the parameters, so changing the date range
    or the variable list is a different cache entry rather than a stale hit.
    """
    RAW.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(
        json.dumps({"url": url, "params": params}, sort_keys=True).encode()
    ).hexdigest()[:12]
    path = RAW / f"{cache_key}.{digest}.json"

    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))

    r = httpx.get(url, params=params, timeout=timeout, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    path.write_text(r.text, encoding="utf-8")
    return r.json()


@dataclass
class Result:
    """One pipeline's verification record, written to docs/results/.

    Nothing in any document is typed by hand, so this is the only route a
    number takes from a pipeline into a report.
    """

    task: str
    dataset: str
    generated_by: str
    checks: list[dict] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def check(self, name: str, passed: bool, detail: str = "") -> bool:
        self.checks.append({"name": name, "pass": bool(passed), "detail": detail})
        return bool(passed)

    @property
    def passed(self) -> bool:
        return all(c["pass"] for c in self.checks)

    def write(self) -> Path:
        RESULTS.mkdir(parents=True, exist_ok=True)
        path = RESULTS / f"{self.task}.json"
        path.write_text(
            json.dumps(
                {
                    "task": self.task,
                    "dataset": self.dataset,
                    "generated_by": self.generated_by,
                    "generated_at": now_iso(),
                    "pass": self.passed,
                    "stats": self.stats,
                    "checks": self.checks,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def report(self) -> int:
        """Print the checks and return a process exit code."""
        for c in self.checks:
            mark = "pass" if c["pass"] else "FAIL"
            print(f"  [{mark}] {c['name']}{(' — ' + c['detail']) if c['detail'] else ''}")
        path = self.write()
        print(f"\n{'PASS' if self.passed else 'FAIL'} — wrote {path.relative_to(ROOT)}")
        return 0 if self.passed else 1
