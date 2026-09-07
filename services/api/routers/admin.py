"""Provider health, budgets, and the kill switch.

THE ONLY NON-READ SURFACE IN THE APPLICATION, AND IT IS STILL A GET.
Engaging the kill switch changes process state rather than data: it stops
inference, it does not write anything, and it is lost on restart — which is the
correct behaviour for a latch whose whole purpose is to be reachable when
something is wrong.

It requires the Admin role. That role comes from a request header and is
therefore a claim the caller makes about itself; see services/api/core/rbac.py
for why that is adequate here and exactly what it does not protect.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from services.api.core import killswitch
from services.api.core.llm import LLMChain
from services.api.core.quota import Quota
from services.api.core.rbac import ROLE_HEADER, Role, Scope, current_role, scopes_for

router = APIRouter(prefix="/admin", tags=["admin"])

#: One chain and one budget for the process, so the counts a reader sees on the
#: Security tab are the counts the application would actually spend.
_QUOTA = Quota.from_env()
_CHAIN = LLMChain.default(_QUOTA)


def require_admin(role: Role = Depends(current_role)) -> Role:
    if Scope.ADMIN_WRITE not in scopes_for(role):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"{role} cannot do this. Send {ROLE_HEADER}: admin.",
        )
    return role


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
    role: Role = Depends(require_admin),
) -> dict:
    killswitch.engage(reason)
    return {"engaged": True, "reason": reason, "by": role.value}


@router.get("/killswitch/release", summary="Resume inference (Admin)")
def release(role: Role = Depends(require_admin)) -> dict:
    killswitch.release()
    return {"engaged": False, "by": role.value}


@router.get("/roles", summary="What each role may do, and what this is not")
def roles(role: Role = Depends(current_role)) -> dict:
    return {
        "you_are": role.value,
        "header": ROLE_HEADER,
        "roles": {r.value: sorted(s.value for s in scopes_for(r)) for r in Role},
        "limitation": (
            "This is authorisation, not authentication. The role is read from a request "
            "header, which is a claim the caller makes about itself and trivially "
            "forgeable. That is adequate for a single-operator coursework tool whose "
            "entire API is read-only and which cannot take an action in the world — the "
            "worst a forged Admin header achieves is stopping a demo. Binding roles to "
            "real identity is what would be needed before this held anything private."
        ),
    }
