"""Provider health, budgets, and the kill switch.

THE ONLY NON-READ SURFACE IN THE APPLICATION, AND IT IS STILL A GET.
Engaging the kill switch changes process state rather than data: it stops
inference, it does not write anything, and it is lost on restart — which is the
correct behaviour for a latch whose whole purpose is to be reachable when
something is wrong.

It requires the Admin role, and that role is now proved rather than claimed: a
token signed with a secret only the operator holds. On a deployment with no
secret configured there is no Admin at all, which is the correct default for a
public URL — the capability is absent rather than open.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from services.api.core import identity, killswitch
from services.api.core.llm import LLMChain
from services.api.core.quota import Quota
from services.api.core.rbac import (
    AUTH_HEADER,
    SCHEME,
    Role,
    Scope,
    current_identity,
    current_role,
    scopes_for,
)

router = APIRouter(prefix="/admin", tags=["admin"])

#: One chain and one budget for the process, so the counts a reader sees on the
#: Security tab are the counts the application would actually spend.
_QUOTA = Quota.from_env()
_CHAIN = LLMChain.default(_QUOTA)


def require_admin(
    who: tuple[Role, identity.Claims | None] = Depends(current_identity),
) -> tuple[Role, identity.Claims]:
    role, claims = who
    if Scope.ADMIN_WRITE not in scopes_for(role) or claims is None:
        # One message for every failure — no secret, no token, a forged one, an
        # expired one. Distinguishing them would tell an attacker which of the
        # four they are up against, and would tell a legitimate operator nothing
        # they cannot get from `scripts/mint_token.py`.
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"This needs a signed Admin token. Send {AUTH_HEADER}: {SCHEME} <token>, "
            "minted with `uv run python scripts/mint_token.py --role admin`."
            + ("" if identity.configured() else " This instance has no signing secret configured."),
        )
    return role, claims


@router.get("/providers", summary="The inference chain, in order, with its budgets")
def providers(role: Role = Depends(current_role)) -> dict:
    return {
        "role": role.value,
        "chain": _CHAIN.health(),
        "budgets_are": "requests, never tokens",
        "why": (
            "The free tiers do not return trustworthy token accounting, and a number "
            "this project cannot verify has no business appearing in a report — the "
            "same rule that governs every other figure here."
        ),
        "killswitch": {"engaged": killswitch.engaged(), "reason": killswitch.reason()},
        "note": (
            "Nothing in the decision path calls this chain. The forecast, the "
            "segmentation, the allocation, the lift estimate and every compliance "
            "verdict are computed in code. The chain writes prose about those results."
        ),
    }


@router.get("/killswitch", summary="Read the latch")
def read_switch() -> dict:
    return {"engaged": killswitch.engaged(), "reason": killswitch.reason()}


@router.get("/killswitch/engage", summary="Stop all inference (Admin)")
def engage(
    reason: str = Query(..., min_length=3, max_length=200),
    who: tuple[Role, identity.Claims] = Depends(require_admin),
) -> dict:
    role, claims = who
    killswitch.engage(reason)
    # The token's subject and id, so the latch records WHICH admin stopped
    # inference. "by: admin" was never an answer to that question.
    return {"engaged": True, "reason": reason, "by": claims.subject, "token": claims.jti}


@router.get("/killswitch/release", summary="Resume inference (Admin)")
def release(who: tuple[Role, identity.Claims] = Depends(require_admin)) -> dict:
    role, claims = who
    killswitch.release()
    return {"engaged": False, "by": claims.subject, "token": claims.jti}


@router.get("/tokens/revoke", summary="Refuse a token before it expires (Admin)")
def revoke_token(
    jti: str = Query(..., min_length=4, max_length=64),
    who: tuple[Role, identity.Claims] = Depends(require_admin),
) -> dict:
    """The answer to "what if a token leaks".

    A stateless credential is usable by whoever holds it until it expires, and
    the operator still has the secret — so they mint a fresh token and refuse
    the old id. The set is process memory, like the kill switch, and clears on
    restart: on a free instance a leaked token's real bound is its expiry.
    """
    _, claims = who
    identity.revoke(jti)
    return {
        "revoked": jti,
        "by": claims.subject,
        "revocations_this_process": len(identity.revoked()),
        "note": (
            "Revocations live in this process and clear on restart. A short "
            "lifetime is the durable control; this is the fast one."
        ),
    }


@router.get("/roles", summary="What each role may do, and how one is proved")
def roles(who: tuple[Role, identity.Claims | None] = Depends(current_identity)) -> dict:
    role, claims = who
    return {
        "you_are": role.value,
        "authenticated": claims is not None,
        "as": None
        if claims is None
        else {"subject": claims.subject, "token": claims.jti, "expires_in_s": claims.expires_in},
        "how": f"{AUTH_HEADER}: {SCHEME} <token>",
        "admin_available_on_this_instance": identity.configured(),
        "roles": {r.value: sorted(s.value for s in scopes_for(r)) for r in Role},
        "mechanism": (
            "A role is proved by a token signed with HMAC-SHA256 under a secret held only "
            "by the operator. The signature covers the role AND the expiry, the algorithm "
            "is fixed by the verifier rather than named in the token, and the comparison "
            "is constant-time. There is no password store, because there are no users: "
            "identity here means holding the secret."
        ),
        "if_unavailable": (
            "This instance has no signing secret, so there is no Admin. The capability is "
            "absent rather than open, which is the intended state for a public URL."
        )
        if not identity.configured()
        else None,
        "residual": (
            "A bearer token is usable by whoever holds it until it expires. Lifetimes are "
            "short by default and /admin/tokens/revoke refuses an id early, but the "
            "revocation set is process memory and clears on restart."
        ),
    }
