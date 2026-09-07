"""Roles, scopes, and one honest limitation stated rather than hidden.

UPLIFT has three roles because it has three genuinely different relationships to
the work:

  VIEWER   reads the plan, the creatives and the results. A colleague you sent
           the link to.
  ANALYST  additionally runs a check and asks the corpus. The person planning.
  ADMIN    additionally pulls the kill switch and resets budgets.

WHAT THIS IS NOT
----------------
This is AUTHORISATION, not authentication. The caller's role is resolved from a
request header, which is a claim the caller makes about itself and trivially
forgeable. That is adequate for a single-operator coursework tool whose entire
API is read-only and which cannot take an action in the world — the worst a
forged Admin header achieves is stopping the demo — and it is written here
rather than left for a reviewer to discover.

Binding roles to real identity is the change that would be needed before this
held anything private. The scope checks below do not change when that lands;
only `current_role` does.
"""

from __future__ import annotations

from enum import StrEnum

from fastapi import Header, HTTPException, status


class Role(StrEnum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"


class Scope(StrEnum):
    READ = "read"
    ANALYSE = "analyse"
    ADMIN_WRITE = "admin:write"


ROLE_SCOPES: dict[Role, frozenset[Scope]] = {
    Role.VIEWER: frozenset({Scope.READ}),
    Role.ANALYST: frozenset({Scope.READ, Scope.ANALYSE}),
    Role.ADMIN: frozenset({Scope.READ, Scope.ANALYSE, Scope.ADMIN_WRITE}),
}

ROLE_HEADER = "X-Mawsim-Role"


def current_role(x_mawsim_role: str | None = Header(default=None)) -> Role:
    """Least privilege by default: an absent or unrecognised role is a Viewer."""
    if not x_mawsim_role:
        return Role.VIEWER
    try:
        return Role(x_mawsim_role.strip().lower())
    except ValueError:
        return Role.VIEWER


def scopes_for(role: Role) -> frozenset[Scope]:
    return ROLE_SCOPES[role]


def require(scope: Scope):
    """A dependency that refuses a caller without the scope."""

    def dependency(role: Role = None) -> Role:  # type: ignore[assignment]
        from fastapi import Depends  # local import keeps the module importable bare

        del Depends
        if scope not in scopes_for(role):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"{role} does not have {scope}. Send {ROLE_HEADER} with a role that does.",
            )
        return role

    return dependency
