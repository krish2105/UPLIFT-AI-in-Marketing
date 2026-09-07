"""The provider chain, the budgets, the kill switch and the roles.

These exist because the README makes claims about them. A claim in a document
about code that is not asserted anywhere is exactly what this project argues
against, so each sentence in that paragraph has a test here.
"""

from __future__ import annotations

import pytest

from services.api.core import killswitch
from services.api.core.llm import (
    AnthropicProvider,
    GeminiProvider,
    GroqProvider,
    LLMChain,
    LLMError,
    Message,
    OllamaProvider,
    StubProvider,
    _json_slice,
)
from services.api.core.quota import Quota
from services.api.core.rbac import ROLE_SCOPES, Role, Scope, current_role, scopes_for


class Boom:
    """A provider that is available, has budget, and always fails."""

    name = "boom"
    model = "explodes-v1"

    def available(self) -> bool:
        return True

    def complete(self, *a, **k):
        raise RuntimeError("upstream on fire")


@pytest.fixture(autouse=True)
def _switch_released():
    killswitch.release()
    yield
    killswitch.release()


class TestTheRefusalIsReal:
    """'Anthropic is present in the provider chain and permanently refuses to
    serve.' — README. Four assertions, because it is four claims."""

    def test_anthropic_is_in_the_default_chain(self):
        assert "anthropic" in [p.name for p in LLMChain.default().providers]

    def test_it_refuses_even_with_a_key_present(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-not-a-real-key")
        assert AnthropicProvider().available() is False

    def test_calling_it_directly_raises(self):
        with pytest.raises(RuntimeError, match="zero paid inference|Zero paid inference"):
            AnthropicProvider().complete("task: x", [Message("user", "hi")])

    def test_the_chain_never_selects_it(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-not-a-real-key")
        chain = LLMChain(
            [AnthropicProvider(), StubProvider()], Quota({"anthropic": 999, "stub": 999})
        )
        assert chain.complete("task: x", [Message("user", "hi")]).provider == "stub"

    def test_its_budget_is_zero_by_construction(self):
        assert Quota.from_env().limit("anthropic") == 0


class TestTheChainDegrades:
    """'a provider failure is degradation with a recorded reason, never an
    exception the caller must handle.'"""

    def test_a_failing_provider_is_skipped_with_its_reason(self):
        chain = LLMChain([Boom(), StubProvider()], Quota({"boom": 9, "stub": 9}))
        r = chain.complete("task: x", [Message("user", "hi")])
        assert r.provider == "stub"
        assert r.degraded_from == ("boom(RuntimeError)",)

    def test_an_unavailable_provider_is_skipped(self):
        chain = LLMChain(
            [GeminiProvider(api_key=""), StubProvider()], Quota({"gemini": 9, "stub": 9})
        )
        r = chain.complete("task: x", [Message("user", "hi")])
        assert r.degraded_from == ("gemini(unavailable)",)

    def test_an_exhausted_budget_is_skipped_and_named(self):
        chain = LLMChain([Boom(), StubProvider()], Quota({"boom": 0, "stub": 9}))
        r = chain.complete("task: x", [Message("user", "hi")])
        assert r.degraded_from == ("boom(quota exhausted)",)

    def test_the_stub_is_appended_if_a_caller_forgets_it(self):
        """Which is what makes complete() total. A chain that could run out of
        providers would push the failure onto every caller.

        Note the quota here funds only "boom". An earlier version metered the
        stub too, so the appended fallback was instantly exhausted and
        complete() raised — totality that depended on the caller remembering to
        fund the fallback, which is not totality."""
        chain = LLMChain([Boom()], Quota({"boom": 9}))
        assert chain.providers[-1].name == "stub"
        assert chain.complete("task: x", [Message("user", "hi")]).provider == "stub"

    def test_the_stub_is_never_metered(self):
        """It is arithmetic over a hash. There is no cost to protect."""
        chain = LLMChain([StubProvider()], Quota({"stub": 0}))
        assert chain.complete("task: x", [Message("user", "hi")]).provider == "stub"

    def test_completion_never_raises_on_provider_failure(self):
        chain = LLMChain([Boom(), Boom(), StubProvider()], Quota({"boom": 9, "stub": 9}))
        assert chain.complete("task: x", [Message("user", "hi")]).text


class TestBudgetsAreRequestsNotTokens:
    def test_a_budget_is_spent_one_request_at_a_time(self):
        q = Quota({"p": 3})
        assert [q.consume("p") for _ in range(4)] == [True, True, True, False]

    def test_exhaustion_returns_false_rather_than_raising(self):
        """Running out of a free tier is an operational fact, not an error."""
        q = Quota({"p": 0})
        assert q.consume("p") is False

    def test_an_unknown_provider_has_no_budget(self):
        assert Quota({}).consume("whoever") is False

    def test_counts_survive_a_restart_when_persisted(self, tmp_path):
        from services.api.core.db import connect

        conn = connect(tmp_path / "q.db")
        Quota({"gemini": 5}, conn).consume("gemini")
        assert Quota({"gemini": 5}, conn).remaining("gemini") == 4


class TestTheKillSwitch:
    def test_it_stops_the_chain_before_any_provider_is_touched(self):
        """Checked before availability, before quota, before any network call.
        A switch you have to route a request through to trip is not a switch."""
        q = Quota({"stub": 9})
        chain = LLMChain([StubProvider()], q)
        killswitch.engage("demo over")
        with pytest.raises(killswitch.KillSwitchEngaged, match="demo over"):
            chain.complete("task: x", [Message("user", "hi")])
        assert q.remaining("stub") == 9, "the switch fired after spending budget"

    def test_releasing_restores_service(self):
        chain = LLMChain([StubProvider()], Quota({"stub": 9}))
        killswitch.engage("x")
        killswitch.release()
        assert chain.complete("task: x", [Message("user", "hi")]).provider == "stub"


class TestTheStubIsDeterministic:
    def test_identical_input_gives_identical_output(self):
        s = StubProvider()
        a = s.complete("task: x", [Message("user", "same")])
        b = s.complete("task: x", [Message("user", "same")])
        assert a.text == b.text

    def test_different_input_gives_different_output(self):
        s = StubProvider()
        assert (
            s.complete("task: x", [Message("user", "a")]).text
            != s.complete("task: x", [Message("user", "b")]).text
        )

    def test_it_says_it_is_a_stub(self):
        """So it can never be mistaken for a model's reasoning in a report."""
        text = StubProvider().complete("task: x", [Message("user", "hi")]).text
        assert "stub" in text.lower()


class TestStructuredOutput:
    def test_it_raises_rather_than_returning_prose(self):
        """An absence the caller must know about, not a degraded answer."""
        from pydantic import BaseModel

        class Verdict(BaseModel):
            ok: bool

        chain = LLMChain([StubProvider()], Quota({"stub": 99}))
        with pytest.raises(LLMError, match="valid Verdict"):
            chain.structured("task: x", [Message("user", "hi")], model_cls=Verdict, retries=0)

    def test_json_is_recovered_from_fences_and_prose(self):
        assert _json_slice('Sure!\n```json\n{"a": 1}\n```') == '{"a": 1}'
        assert _json_slice('Here you go: {"a": 1} — hope that helps') == '{"a": 1}'
        with pytest.raises(ValueError, match="no JSON object"):
            _json_slice("no object here")


class TestHealthReportsTheWholeChain:
    def test_every_provider_appears_with_its_budget(self):
        health = LLMChain.default().health()
        assert [h["name"] for h in health] == ["ollama", "gemini", "groq", "anthropic", "stub"]
        assert all("quota_remaining" in h for h in health)

    def test_anthropic_publishes_why_it_is_off(self):
        anthropic = next(h for h in LLMChain.default().health() if h["name"] == "anthropic")
        assert anthropic["available"] is False
        assert "zero paid inference" in str(anthropic["disabled_reason"]).lower()


class TestRoles:
    def test_an_absent_role_is_a_viewer(self):
        assert current_role(None) is Role.VIEWER

    def test_an_unrecognised_role_is_a_viewer_not_an_error(self):
        """Least privilege. A typo should not escalate, and should not 500."""
        assert current_role("superuser") is Role.VIEWER

    def test_scopes_are_strictly_nested(self):
        assert scopes_for(Role.VIEWER) < scopes_for(Role.ANALYST) < scopes_for(Role.ADMIN)

    def test_only_admin_can_touch_the_switch(self):
        assert Scope.ADMIN_WRITE in ROLE_SCOPES[Role.ADMIN]
        assert Scope.ADMIN_WRITE not in ROLE_SCOPES[Role.ANALYST]

    def test_a_role_cannot_be_claimed_in_a_header_any_more(self):
        """This assertion used to read `current_role("  ADMIN ") is Role.ADMIN`.

        It passed, the mechanism worked as designed, and the design was the
        vulnerability — the red-team harness engaged the kill switch with that
        exact string. Roles are proved by a signed token now; the attacks on it
        live in tests/security/test_identity.py.
        """
        for claim in ("admin", "  ADMIN ", "analyst"):
            assert current_role(claim) is Role.VIEWER


class TestProviderConstructionIsSideEffectFree:
    @pytest.mark.parametrize(
        "cls", [OllamaProvider, GeminiProvider, GroqProvider, AnthropicProvider, StubProvider]
    )
    def test_constructing_a_provider_makes_no_network_call(self, cls, monkeypatch):
        def explode(*a, **k):
            raise AssertionError(f"{cls.__name__} made a network call at construction")

        monkeypatch.setattr("httpx.get", explode)
        monkeypatch.setattr("httpx.post", explode)
        cls()
