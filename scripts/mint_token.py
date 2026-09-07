"""Mint a capability token. Run by whoever holds the signing secret.

This is the whole of the access control: there is no sign-up, no password and no
account to compromise, so the only way to obtain a role above Viewer is to hold
`UPLIFT_SIGNING_SECRET` and run this.

    export UPLIFT_SIGNING_SECRET="$(uv run python scripts/mint_token.py --new-secret)"
    uv run python scripts/mint_token.py --role admin --hours 8 --subject krishna@laptop

The token is printed to stdout and nowhere else. It is not written to a file,
because a credential on disk outlives the reason it was created.
"""

from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "services"))

from services.api.core import identity  # noqa: E402
from services.api.core.rbac import Role  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--role", choices=[r.value for r in Role], default="admin")
    ap.add_argument("--hours", type=float, default=8.0, help="lifetime; keep it short")
    ap.add_argument("--subject", default="operator", help="who this is for, recorded in the token")
    ap.add_argument(
        "--new-secret",
        action="store_true",
        help="print a fresh secret and exit; does not store it anywhere",
    )
    args = ap.parse_args()

    if args.new_secret:
        # 64 hex characters from the OS CSPRNG. Printed once, stored by the
        # operator, never seen by this project again.
        print(secrets.token_hex(32))
        return 0

    try:
        token = identity.mint(args.role, subject=args.subject, ttl_seconds=int(args.hours * 3600))
    except identity.IdentityError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        print(
            "\nGenerate one with:\n"
            '  export UPLIFT_SIGNING_SECRET="$(uv run python scripts/mint_token.py --new-secret)"',
            file=sys.stderr,
        )
        return 1

    print(token)
    print(
        f"\n# role={args.role} subject={args.subject} expires in {args.hours:g}h\n"
        f'# curl -H "Authorization: Bearer $TOKEN" '
        f'"$API/admin/killswitch/engage?reason=demo"',
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
