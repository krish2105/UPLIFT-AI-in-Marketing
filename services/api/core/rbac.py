"""Roles, scopes, and where a role now comes from.

UPLIFT has three roles because it has three genuinely different relationships to
the work:

  VIEWER   reads the plan, the creatives and the results. A colleague you sent
           the link to. This is what an unauthenticated caller gets.
  ANALYST  additionally runs a check and asks the corpus.
  ADMIN    additionally pulls the kill switch and resets budgets.

AUTHENTICATION, NOT JUST AUTHORISATION
--------------------------------------
This module used to read the role from `X-Mawsim-Role`, a header the caller sets
about itself. The project said so plainly and the red-team harness scored it as
a break, because it was one: `X-Mawsim-Role: ADMIN ` engaged the kill switch,
and "we documented it" is not a control.

A role now comes from a signed capability token in the Authorization header, and
the header is gone rather than kept for compatibility — a vestigial input that
once granted privilege is exactly what gets re-enabled by accident. See
`identity.py` for the token and why it is not a login.

Least privilege remains the default in both directions: no token is a Viewer, and
so is an unreadable, expired, revoked or unsigned one. There is no path from a
bad credential to anything above Viewer, and no error either — a caller who
sends nonsense is simply a Viewer, which is what they would have been in silence.
"""

from __future__ import annotations

from enum import StrEnum

from fastapi import Header, HTTPException, status

from services.api.core import identity


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

AUTH_HEADER = "Authorization"
SCHEME = "Bearer"


def current_role(authorization: str | None = Header(default=None)) -> Role:
    """Least privilege by default, and by failure.

    Every way of getting this wrong lands on Viewer: no header, the wrong
    scheme, a forged signature, an expired or revoked token, a role the enum
    does not know, or a deployment with no secret configured at all.
    """
    return current_identity(authorization)[0]


def current_identity(
    authorization: str | None = Header(default=None),
) -> tuple[Role, identity.Claims | None]:
    """The role and, when there is one, the token that proved it.

    Returned together because an endpoint that reports WHO acted needs the
    subject and the token id, and re-verifying to get them would mean verifying
    twice per request.
    """
    if not authorization:
        return Role.VIEWER, None
    scheme, _, token = authorization.partition(" ")
    if scheme.strip().lower() != SCHEME.lower() or not token.strip():
        return Role.VIEWER, None
    try:
        claims = identity.verify(token.strip())
        return Role(claims.role.strip().lower()), claims
    except (identity.IdentityError, ValueError):
        return Role.VIEWER, None


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
                f"{role} does not have {scope}. Send {AUTH_HEADER}: {SCHEME} <token>.",
            )
        return role

    return dependency
