"""Identity for a tool with no users: signed capability tokens.

WHY NOT A LOGIN
---------------
The obvious answer to "bind roles to identity" is accounts and passwords, and it
is the wrong one here. A password store is a liability this application has no
use for: there are no users, there is one operator, and the entire API is
read-only. Storing hashes to protect a kill switch would add the most valuable
thing in the system — a credential database — in order to guard the least.

So identity is proved by holding a SECRET, not by knowing a password. Whoever
has `UPLIFT_SIGNING_SECRET` can mint a token; whoever does not, cannot. The
secret lives in the environment and is never written to disk, never returned by
an endpoint, and never logged.

WHAT A TOKEN IS
---------------
    v1.<base64url(payload)>.<base64url(hmac-sha256)>

The payload names a role, an expiry and a nonce. The signature covers the
version and the payload together, so nothing inside can be edited — including
the expiry, which is the field an attacker would most like to reach.

FOUR DECISIONS WORTH THE WORDS
------------------------------
*The algorithm is not in the token.* JWT's `alg` field is the source of its
best-known vulnerability: a verifier that reads the algorithm from the thing it
is verifying can be told `none`. Here the algorithm is HMAC-SHA256 because this
module says so, and a token cannot express an opinion about it.

*The signature is checked before the payload is parsed.* Parsing first means
running a JSON decoder over attacker-controlled bytes and then deciding whether
to trust them, which gets the order exactly backwards.

*Comparison is constant-time.* `hmac.compare_digest`, because a byte-at-a-time
comparison leaks the signature one byte per timing measurement.

*It fails closed.* With no secret configured, `verify` refuses everything and
the Admin role is unreachable rather than open. A deployment that forgets to set
the secret loses a capability; it does not silently grant one.

WHAT IS STILL TRUE OF ANY BEARER TOKEN
--------------------------------------
Whoever holds it can use it until it expires. That is inherent to a stateless
credential, and the answers are the ones taken here: short lifetimes by default,
and `revoke()` for the case where one leaks. On a free instance the revocation
set is process memory, so it clears on restart — the same semantics as the kill
switch, and stated for the same reason.
"""

from __future__ import annotations

import base64
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from hashlib import sha256

VERSION = "v1"
ENV_VAR = "UPLIFT_SIGNING_SECRET"

#: A short secret is brute-forceable offline against a single captured token, so
#: one is refused outright rather than accepted with a warning nobody reads.
MIN_SECRET_LENGTH = 32

DEFAULT_TTL_SECONDS = 8 * 3600
MAX_TTL_SECONDS = 30 * 24 * 3600


class IdentityError(RuntimeError):
    """Base for every refusal, so a caller cannot accidentally catch too little."""


class NoSecretConfigured(IdentityError):
    pass


class WeakSecret(IdentityError):
    pass


class InvalidToken(IdentityError):
    pass


@dataclass(frozen=True)
class Claims:
    role: str
    subject: str
    expires_at: int
    jti: str

    @property
    def expires_in(self) -> int:
        return max(0, self.expires_at - int(time.time()))


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def secret() -> bytes:
    raw = os.getenv(ENV_VAR, "")
    if not raw:
        raise NoSecretConfigured(
            f"{ENV_VAR} is not set, so no token can be minted or verified and the "
            "Admin role is unreachable. That is the intended state for a public "
            "deployment: see docs/deploy.md to enable it."
        )
    if len(raw) < MIN_SECRET_LENGTH:
        raise WeakSecret(
            f"{ENV_VAR} is {len(raw)} characters; {MIN_SECRET_LENGTH} is the minimum. "
            "A short secret is brute-forceable offline against one captured token."
        )
    return raw.encode("utf-8")


def configured() -> bool:
    try:
        secret()
    except IdentityError:
        return False
    return True


def _sign(signing_input: str, key: bytes) -> str:
    return _b64(hmac.new(key, signing_input.encode("ascii"), sha256).digest())


def mint(role: str, *, subject: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Issue a token. Requires the secret, which is the whole of the access control."""
    if not 0 < ttl_seconds <= MAX_TTL_SECONDS:
        raise IdentityError(f"ttl must be between 1 and {MAX_TTL_SECONDS} seconds")
    key = secret()
    payload = {
        "role": role,
        "sub": subject,
        "exp": int(time.time()) + ttl_seconds,
        "jti": secrets.token_hex(8),
    }
    body = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{VERSION}.{body}"
    return f"{signing_input}.{_sign(signing_input, key)}"


#: Revoked token ids. Process memory, like the kill switch: it clears on restart,
#: and on an instance that restarts hourly a leaked token's real bound is its
#: expiry rather than this set.
_REVOKED: set[str] = set()


def revoke(jti: str) -> None:
    _REVOKED.add(jti)


def revoked() -> frozenset[str]:
    return frozenset(_REVOKED)


def clear_revocations() -> None:
    _REVOKED.clear()


def verify(token: str) -> Claims:
    """Return the claims, or raise. Never returns a partial or unverified result."""
    key = secret()  # raises when unconfigured: fail closed

    parts = token.split(".")
    if len(parts) != 3:
        raise InvalidToken("malformed: expected three dot-separated segments")
    version, body, signature = parts
    if version != VERSION:
        raise InvalidToken(f"unsupported version {version!r}")

    expected = _sign(f"{version}.{body}", key)
    # Constant-time, and BEFORE the payload is decoded — the bytes are still
    # attacker-controlled until this line returns True.
    if not hmac.compare_digest(expected, signature):
        raise InvalidToken("signature does not verify")

    try:
        payload = json.loads(_unb64(body))
    except (ValueError, json.JSONDecodeError) as exc:
        # Reachable only for a payload this module signed, so it means a bug
        # here rather than an attack — and it is still not trusted.
        raise InvalidToken(f"signed payload is not readable: {exc}") from exc

    for field in ("role", "sub", "exp", "jti"):
        if field not in payload:
            raise InvalidToken(f"signed payload is missing {field!r}")

    if int(payload["exp"]) <= int(time.time()):
        raise InvalidToken("expired")
    if payload["jti"] in _REVOKED:
        raise InvalidToken("revoked")

    return Claims(
        role=str(payload["role"]),
        subject=str(payload["sub"]),
        expires_at=int(payload["exp"]),
        jti=str(payload["jti"]),
    )
