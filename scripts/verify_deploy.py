"""Record what is true of the deployed pair, as a result rather than a claim.

Task A12 named this file. It went unwritten for the same reason deployment
checks usually do: the deploy worked, so nobody wrote down what "worked" meant.
The value is not in today's run — it is that the next person can see which
properties were ever asserted, and re-assert them with one command.

Nothing here is a substitute for `make smoke-live`, which drives a real browser.
This records the API half, which is the half a build can silently break.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common import now_iso  # noqa: E402

RESULTS = ROOT / "docs" / "results"
API = os.environ.get("LIVE_API_URL", "https://mawsim-api.onrender.com")
WEB = os.environ.get("LIVE_WEB_URL", "https://uplift-mawsim.vercel.app")

# The free instance sleeps after fifteen minutes and takes about fifty seconds
# to wake. A short timeout here would report the sleep as an outage.
TIMEOUT = 120


def get(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:  # noqa: S310
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # noqa: BLE001
        return 0, str(e)


def main() -> int:
    checks: list[dict] = []

    def record(name: str, held: bool, detail: str) -> None:
        checks.append({"check": name, "held": held, "detail": detail})
        print(f"  [{'ok  ' if held else 'FAIL'}] {name} — {detail}")

    status, body = get(f"{API}/healthz")
    health = json.loads(body) if status == 200 and body else {}
    record("the API answers", status == 200, f"HTTP {status}")

    # The failure this exists to catch: Render's build and runtime are different
    # containers, so a database written during the build is not there at runtime.
    empty = health.get("empty_datasets", ["<no response>"])
    record("no dataset is empty on the deployed instance", empty == [], f"empty: {empty or 'none'}")
    record(
        "the brand is declared fictional by the API",
        health.get("brand", {}).get("fictional") is True,
        str(health.get("brand", {}).get("fictional")),
    )

    status, body = get(f"{API}/data/freshness")
    sets = json.loads(body)["datasets"] if status == 200 and body else []
    unlabelled = [d["key"] for d in sets if not d.get("licence") or not d.get("label")]
    record(
        "every dataset carries a licence and a label",
        bool(sets) and not unlabelled,
        f"{len(sets)} datasets, {len(unlabelled)} missing provenance",
    )

    status, body = get(f"{API}/security")
    red = json.loads(body).get("red_team") if status == 200 and body else None
    record(
        "the red-team result reached the deployed instance",
        bool(red),
        f"{red['held']}/{red['cases']} held"
        if red
        else "absent — the section would vanish silently",
    )

    status, body = get(f"{API}/admin/roles")
    roles = json.loads(body) if status == 200 and body else {}
    record(
        "the deployed instance grants no Admin",
        roles.get("admin_available_on_this_instance") is False and roles.get("you_are") == "viewer",
        f"admin available: {roles.get('admin_available_on_this_instance')}",
    )

    # The string that used to engage the kill switch on this very URL.
    status, _ = get(f"{API}/admin/killswitch/engage?reason=deploy+probe")
    record(
        "the retired role header grants nothing",
        status == 403,
        f"HTTP {status}",
    )

    status, _ = get(WEB)
    record("the web app answers", status == 200, f"HTTP {status}")

    payload = {
        "task": "A12-deploy",
        "generated_by": "scripts/verify_deploy.py",
        "generated_at": now_iso(),
        "api": API,
        "web": WEB,
        "host_api": "Render free web service, region singapore",
        "host_web": "Vercel",
        "checks": checks,
        "held": sum(1 for c in checks if c["held"]),
        "total": len(checks),
        "datasets_loaded": health.get("datasets_loaded", {}),
        "note_on_sleep": (
            "The free instance sleeps after fifteen minutes idle, so the first request "
            "after a quiet period takes about fifty seconds. That is not an outage and "
            "the timeout here is set above it; a shorter one would record a nap as a "
            "failure."
        ),
        "note_on_scope": (
            "This records the API half. The browser half — CORS, the disclaimer, the "
            "fifteen tabs, the Security tab's attack table — is asserted by "
            "apps/web/e2e-live/live.spec.ts, which drives a real browser."
        ),
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "A12-deploy.json"
    if out.exists():
        previous = json.loads(out.read_text(encoding="utf-8"))
        if {k: v for k, v in previous.items() if k != "generated_at"} == {
            k: v for k, v in payload.items() if k != "generated_at"
        }:
            payload["generated_at"] = previous["generated_at"]
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"\n{payload['held']}/{payload['total']} deployment checks held")
    print("  wrote docs/results/A12-deploy.json")
    return 0 if payload["held"] == payload["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
