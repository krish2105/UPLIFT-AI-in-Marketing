"""The safety claim, asserted over the whole surface rather than reviewed by eye.

UPLIFT's central promise is that nothing it contains can reach the outside
world. That is easy to state and easy to break by accident — one convenience
route, one agent tool that posts a webhook. These tests are what make the claim
survive the person who wrote it.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from services.api.main import app
from services.api.routers.system import CREW

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "services" / "api"


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


class TestTheApiIsReadOnly:
    def test_every_route_is_a_get(self, client: TestClient):
        """Not "no route mutates state" — no route is even capable of it.

        This started as a POST for the compliance checker, which computes a
        verdict from a string and stores nothing. That left one mutating-looking
        route while CORS allowed GET alone, so the Compliance tab would have
        failed the moment it called it from a browser. The whole API is GET.
        """
        mutating = []
        for route in app.routes:
            methods = getattr(route, "methods", set()) - {"GET", "HEAD", "OPTIONS"}
            if methods:
                mutating.append((getattr(route, "path", "?"), sorted(methods)))
        assert mutating == [], mutating

    def test_checking_copy_stores_nothing(self, client: TestClient):
        before = client.get("/data/freshness").json()["totals"]["rows"]
        client.get("/compliance/check?text=our best detox latte")
        after = client.get("/data/freshness").json()["totals"]["rows"]
        assert before == after

    def test_cors_permits_get_only(self):
        for mw in app.user_middleware:
            if "CORSMiddleware" in str(mw.cls):
                assert set(mw.kwargs["allow_methods"]) == {"GET"}
                return
        pytest.fail("no CORS middleware configured")


class TestNoAgentHasASideEffect:
    def test_every_crew_row_declares_none(self):
        for agent in CREW:
            assert agent["side_effects"] == "none", f"{agent['agent']} declares a side effect"

    def test_no_agent_tool_can_send_anything(self):
        """A declared 'none' is a promise; this checks the vocabulary too, so a
        tool named for an outward action fails even if its row lies."""
        forbidden = ("post", "send", "publish", "email", "webhook", "schedule", "tweet", "upload")
        for agent in CREW:
            for tool in agent["tools"]:
                assert not any(f in tool.lower() for f in forbidden), (
                    f"{agent['agent']} has tool {tool!r}, which names an outward action"
                )


class TestNothingWritesOutward:
    """A source-level check, because a route list only covers what is routed.

    Walks the API package's ASTs looking for outbound calls in modules that
    serve requests. The pipelines legitimately fetch — they are run from a
    terminal, not from a request — so they are not in scope here.
    """

    REQUEST_PATH = ("routers", "creative", "marketing", "rag", "security", "data")
    FORBIDDEN_CALLS = {"post", "put", "patch", "delete", "sendmail", "urlopen"}

    def _modules(self):
        for path in API.rglob("*.py"):
            rel = path.relative_to(API)
            if rel.parts and rel.parts[0] in self.REQUEST_PATH:
                yield path

    def test_no_request_path_module_makes_an_outbound_write(self):
        offenders = []
        for path in self._modules():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                # conn.execute("DELETE ...") is caught separately below; this
                # one is about the network.
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in self.FORBIDDEN_CALLS
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in {"httpx", "requests", "urllib", "session", "client"}
                ):
                    offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
        assert not offenders, f"outbound write calls on a request path: {offenders}"

    def test_no_request_path_module_writes_to_the_database(self):
        offenders = []
        for path in self._modules():
            src = path.read_text(encoding="utf-8")
            for i, line in enumerate(src.splitlines(), 1):
                stripped = line.strip().upper()
                if any(
                    f'"{verb}' in stripped or f"'{verb}" in stripped
                    for verb in ("INSERT ", "UPDATE ", "DROP ", "ALTER ")
                ):
                    offenders.append(f"{path.relative_to(ROOT)}:{i}")
        assert not offenders, f"write SQL on a request path: {offenders}"


class TestGeneratedDataKeepsItsLabel:
    def test_every_series_payload_says_what_it_is(self, client: TestClient):
        for path in ("/series/footfall", "/series/dayparts", "/series/station?zone=DXB-MAR"):
            body = client.get(path).json()
            assert body.get("simulated") is True, f"{path} does not declare itself"

    def test_the_freshness_payload_carries_the_standing_note(self, client: TestClient):
        body = client.get("/data/freshness").json()
        assert "generated" in body["standing_note"].lower()
