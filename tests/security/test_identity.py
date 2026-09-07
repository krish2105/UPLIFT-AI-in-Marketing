"""Attacks on the token, and the one thing the old header could not survive.

Every test here is an attempt to obtain Admin without the secret. They are
written as attacks rather than as "it works" cases because the previous
mechanism passed every "it works" test it had — `X-Mawsim-Role: admin` resolved
to Admin exactly as designed, and that was the vulnerability.
"""

from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "services"))

from fastapi.testclient import TestClient  # noqa: E402

from services.api.core import identity, rbac  # noqa: E402
from services.api.main import app  # noqa: E402

SECRET = "s" * 48
OTHER_SECRET = "z" * 48


@pytest.fixture
def signed(monkeypatch):
    monkeypatch.setenv(identity.ENV_VAR, SECRET)
    identity.clear_revocations()
    yield
    identity.clear_revocations()


@pytest.fixture
def unsigned(monkeypatch):
    monkeypatch.delenv(identity.ENV_VAR, raising=False)
    yield


def admin_token(**kw) -> str:
    return identity.mint("admin", subject=kw.pop("subject", "op"), **kw)


def _repack(token: str, **changes) -> str:
    """Edit a token's payload, keeping its original signature.

    The attack a signed token exists to stop, and the one an implementation that
    parses before it verifies will fall for.
    """
    version, body, sig = token.split(".")
    pad = "=" * (-len(body) % 4)
    payload = json.loads(base64.urlsafe_b64decode(body + pad))
    payload.update(changes)
    new = (
        base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        )
        .decode()
        .rstrip("=")
    )
    return f"{version}.{new}.{sig}"


class TestTheTokenItself:
    def test_a_valid_token_carries_its_role(self, signed):
        claims = identity.verify(admin_token())
        assert claims.role == "admin"
        assert claims.expires_in > 0

    def test_the_payload_cannot_be_edited(self, signed):
        """Escalation by rewriting the role, signature untouched."""
        viewer = identity.mint("viewer", subject="op")
        with pytest.raises(identity.InvalidToken, match="signature"):
            identity.verify(_repack(viewer, role="admin"))

    def test_the_expiry_cannot_be_extended(self, signed):
        """The expiry is inside the signature, which is the point of putting it there."""
        token = admin_token(ttl_seconds=1)
        with pytest.raises(identity.InvalidToken, match="signature"):
            identity.verify(_repack(token, exp=int(time.time()) + 99999))

    def test_an_expired_token_is_refused(self, signed, monkeypatch):
        token = admin_token(ttl_seconds=1)
        monkeypatch.setattr(time, "time", lambda: 1.0e12)  # far past its expiry
        with pytest.raises(identity.InvalidToken, match="expired"):
            identity.verify(token)

    def test_a_token_signed_with_another_secret_is_refused(self, signed, monkeypatch):
        token = admin_token()
        monkeypatch.setenv(identity.ENV_VAR, OTHER_SECRET)
        with pytest.raises(identity.InvalidToken, match="signature"):
            identity.verify(token)

    @pytest.mark.parametrize(
        "mangle",
        [
            pytest.param(lambda t: t.rsplit(".", 1)[0] + ".", id="empty signature"),
            pytest.param(lambda t: t.rsplit(".", 1)[0], id="signature removed"),
            pytest.param(lambda t: t[: t.rindex(".") + 6], id="truncated signature"),
            pytest.param(lambda t: t + ".extra", id="extra segment"),
            pytest.param(lambda t: "v2" + t[2:], id="version bumped"),
            pytest.param(lambda t: t.replace("v1.", "none."), id="algorithm swapped"),
            pytest.param(lambda t: "", id="empty"),
        ],
    )
    def test_malformed_tokens_are_refused(self, signed, mangle):
        with pytest.raises(identity.InvalidToken):
            identity.verify(mangle(admin_token()))

    def test_a_revoked_token_stops_working(self, signed):
        token = admin_token()
        identity.revoke(identity.verify(token).jti)
        with pytest.raises(identity.InvalidToken, match="revoked"):
            identity.verify(token)

    def test_without_a_secret_nothing_verifies_or_mints(self, unsigned):
        assert identity.configured() is False
        with pytest.raises(identity.NoSecretConfigured):
            identity.mint("admin", subject="op")
        with pytest.raises(identity.NoSecretConfigured):
            identity.verify("v1.abc.def")

    def test_a_short_secret_is_refused_rather_than_warned_about(self, monkeypatch):
        monkeypatch.setenv(identity.ENV_VAR, "short")
        with pytest.raises(identity.WeakSecret):
            identity.mint("admin", subject="op")

    def test_the_comparison_is_constant_time(self):
        """Asserted at the source, because timing cannot be measured reliably here.

        A byte-at-a-time `==` leaks the signature one measurement per byte, and
        it is the kind of line that gets 'simplified' back later.
        """
        src = (ROOT / "services" / "api" / "core" / "identity.py").read_text()
        assert "hmac.compare_digest" in src
        assert "if expected == signature" not in src


class TestTheRoleThatReachesTheApplication:
    def test_the_old_header_grants_nothing(self, signed):
        """The specific break this replaces: `X-Mawsim-Role: ADMIN ` engaged the switch."""
        c = TestClient(app)
        for value in ("admin", "ADMIN ", "Admin", "admin\nX-Mawsim-Role: admin"):
            r = c.get("/admin/killswitch/engage?reason=probe", headers={"X-Mawsim-Role": value})
            assert r.status_code == 403, f"{value!r} was accepted"

    def test_a_signed_admin_token_engages_the_switch(self, signed):
        c = TestClient(app)
        token = admin_token(subject="tester")
        r = c.get(
            "/admin/killswitch/engage?reason=under+test",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        # The latch records WHO, which "by: admin" never did.
        assert r.json()["by"] == "tester"
        c.get("/admin/killswitch/release", headers={"Authorization": f"Bearer {token}"})

    def test_an_analyst_token_cannot_reach_admin(self, signed):
        """Escalation across roles, with a genuinely signed token."""
        token = identity.mint("analyst", subject="planner")
        c = TestClient(app)
        r = c.get(
            "/admin/killswitch/engage?reason=probe", headers={"Authorization": f"Bearer {token}"}
        )
        assert r.status_code == 403

    @pytest.mark.parametrize(
        "header",
        [
            "Bearer",
            "Bearer ",
            "Basic dXNlcjpwYXNz",
            "bearer not-a-token",
            "Bearer v1.aaa.bbb",
            "Token abc",
        ],
    )
    def test_every_bad_credential_is_a_viewer_not_an_error(self, signed, header):
        """Least privilege by failure: nonsense lands on Viewer, silently.

        Returning 401 here would turn the endpoint into an oracle that says
        which of several wrong things a caller sent.
        """
        assert rbac.current_role(header) is rbac.Role.VIEWER

    def test_admin_is_absent_rather_than_open_without_a_secret(self, unsigned):
        c = TestClient(app)
        body = c.get("/admin/roles").json()
        assert body["admin_available_on_this_instance"] is False
        assert body["you_are"] == "viewer"
        assert c.get("/admin/killswitch/engage?reason=probe").status_code == 403
