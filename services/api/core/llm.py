"""Provider-agnostic inference, ordered free-first.

WHY AN ABSTRACTION AND NOT AN SDK CALL
--------------------------------------
UPLIFT has a hard constraint — zero paid inference — and a soft one: it must
behave identically on the owner's Mac, where Ollama is a local process, and on a
free Render instance, where it is not. Which vendor serves a turn is an
operational detail. Binding the application to one SDK would make that detail
structural and would make the zero-cost promise a matter of discipline rather
than of architecture.

Five providers, one interface, tried in this order:

  OllamaProvider     local, free, no key, no egress. Preferred wherever it exists.
  GeminiProvider     free tier. What a deployed instance would think with.
  GroqProvider       free tier. A second cloud opinion, and fast.
  AnthropicProvider  PRESENT AND PERMANENTLY DISABLED. It is in the chain so
                     that the refusal is visible in the code and testable,
                     rather than being an absence a future contributor might
                     helpfully "fix".
  StubProvider       deterministic, dependency-free, always last. Not a mock: it
                     derives its output from a hash of its input, so the chain,
                     the budgets and the degradation path are genuinely
                     exercised with no model and no network at all.

The stub being terminal is what makes `complete()` total with respect to
provider failure: a failure is degradation with a recorded reason, never an
exception the caller has to handle. The one thing that DOES raise is the kill
switch, checked first.

WHAT THIS CHAIN IS AND IS NOT USED FOR
--------------------------------------
Nothing in UPLIFT's decision path calls it. The forecast, the segmentation, the
allocation, the lift estimate and every compliance verdict are computed in code,
because each has a correct answer and an established method, and routing them
through a model would make them unreproducible without making them better. This
chain exists to write PROSE about those results — and the Auditor's rule is that
a sentence without a citation does not ship.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Literal, Protocol, TypeVar, runtime_checkable

import httpx
from pydantic import BaseModel, ValidationError

from services.api.core import killswitch
from services.api.core.quota import Quota

Role = Literal["system", "user", "assistant"]
T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """Raised when the chain cannot produce a valid structured result."""


@dataclass(frozen=True)
class Message:
    role: Role
    content: str


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model: str
    latency_s: float = 0.0
    #: True when the model stopped because it ran out of token budget rather
    #: than because it had finished. Under schema-constrained decoding this is
    #: the dangerous case: the grammar forces the object closed, so the result
    #: PARSES and VALIDATES while carrying a sentence cut in half. Nothing
    #: downstream can detect that from the value, so it is caught here.
    truncated: bool = False
    #: Providers passed over, in order, each with its reason —
    #: e.g. ("ollama(unreachable)", "gemini(quota exhausted)").
    degraded_from: tuple[str, ...] = field(default_factory=tuple)


@runtime_checkable
class LLMProvider(Protocol):
    name: str
    model: str

    def available(self) -> bool: ...

    def complete(
        self,
        system: str,
        messages: list[Message],
        *,
        max_tokens: int = 512,
        temperature: float = 0.0,
        schema: dict | None = None,
    ) -> LLMResponse: ...


# ── the CI substrate ────────────────────────────────────────────────────────


class StubProvider:
    """Deterministic, free, always available.

    Given identical input it returns identical output, which is what makes the
    determinism tests meaningful rather than circular. Its text is marked as
    stub output so it can never be mistaken for a model's reasoning in a
    transcript or a report.
    """

    name = "stub"

    def __init__(self, model: str = "deterministic-v1") -> None:
        self.model = model
        self._handlers: dict[str, object] = {}

    def register(self, task: str, handler) -> None:
        """Bind a task id to a deterministic structured generator."""
        self._handlers[task] = handler

    def available(self) -> bool:
        return True

    def complete(self, system, messages, *, max_tokens=512, temperature=0.0, schema=None):
        t0 = time.perf_counter()
        digest = hashlib.sha256(
            json.dumps(
                [system, [(m.role, m.content) for m in messages]], ensure_ascii=False
            ).encode()
        ).hexdigest()
        handler = self._handlers.get(_task_of(system))
        text = (
            handler(system, messages, digest)
            if handler
            else f"[stub:{digest[:12]}] Deterministic output from the stub provider. "
            "This is not a model's reasoning and must not be presented as one."
        )
        return LLMResponse(
            text=text,
            provider=self.name,
            model=self.model,
            latency_s=time.perf_counter() - t0,
        )


def _task_of(system: str) -> str:
    """Task id, declared as `task: <id>` on the system prompt's first line."""
    first = system.strip().splitlines()[0] if system.strip() else ""
    return first.split("task:", 1)[1].strip() if "task:" in first else "unknown"


def _gemini_schema(schema: dict) -> dict:
    """Strip the JSON Schema keywords Gemini's responseSchema rejects.

    Gemini takes a subset of OpenAPI rather than full JSON Schema: no $defs or
    $ref, and it chokes on additionalProperties and several annotations pydantic
    emits by default. Flattening the pydantic schema here is better than
    hand-writing a second one and letting the two drift.
    """
    defs = schema.get("$defs", {})

    def walk(node):
        if isinstance(node, list):
            return [walk(n) for n in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            return walk(defs.get(node["$ref"].rsplit("/", 1)[-1], {"type": "string"}))
        return {
            k: walk(v)
            for k, v in node.items()
            if k
            not in {
                "$defs",
                "additionalProperties",
                "title",
                "default",
                "exclusiveMinimum",
                "exclusiveMaximum",
                "minLength",
                "maxLength",
                "minimum",
                "maximum",
                "minItems",
                "maxItems",
            }
        }

    return walk({k: v for k, v in schema.items() if k != "$defs"})


# ── local ───────────────────────────────────────────────────────────────────


class OllamaProvider:
    name = "ollama"

    def __init__(self, host: str | None = None, model: str | None = None, timeout: float = 120.0):
        self.host = (host or os.getenv("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        self.model = model or os.getenv("OLLAMA_CHAT_MODEL") or "qwen3:8b"
        self.timeout = timeout

    def available(self) -> bool:
        try:
            return httpx.get(f"{self.host}/api/tags", timeout=2.0).status_code == 200
        except httpx.HTTPError:
            return False

    def complete(self, system, messages, *, max_tokens=512, temperature=0.0, schema=None):
        t0 = time.perf_counter()
        body: dict = {}
        if schema is not None:
            # Ollama accepts a JSON Schema directly and constrains decoding to
            # it, which is stronger than asking for JSON in the prompt and hoping.
            body["format"] = schema
        r = httpx.post(
            f"{self.host}/api/chat",
            json={
                "model": self.model,
                "messages": [{"role": "system", "content": system}]
                + [{"role": m.role, "content": m.content} for m in messages],
                "stream": False,
                # Keep the model resident. Retrieval touches the embedding model
                # between turns and without this the two evict each other, so
                # every turn pays a cold load.
                "keep_alive": "30m",
                # qwen3 reasons by default. A marketing brief is an output, not a
                # scratchpad, and thinking tokens triple the wall clock for text
                # the report then has to discard.
                "think": False,
                "options": {"num_predict": max_tokens, "temperature": temperature},
                **body,
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        payload = r.json()
        return LLMResponse(
            text=payload["message"]["content"],
            provider=self.name,
            model=self.model,
            latency_s=time.perf_counter() - t0,
            truncated=payload.get("done_reason") == "length",
        )


# ── free cloud ──────────────────────────────────────────────────────────────


class GeminiProvider:
    name = "gemini"
    ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: float = 60.0):
        self._key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL") or "gemini-2.0-flash"
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self._key)

    def complete(self, system, messages, *, max_tokens=512, temperature=0.0, schema=None):
        t0 = time.perf_counter()
        generation: dict[str, object] = {"maxOutputTokens": max_tokens, "temperature": temperature}
        if schema is not None:
            generation["responseMimeType"] = "application/json"
            generation["responseSchema"] = _gemini_schema(schema)
        r = httpx.post(
            f"{self.ENDPOINT}/{self.model}:generateContent",
            params={"key": self._key},
            json={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [
                    {
                        "role": "model" if m.role == "assistant" else "user",
                        "parts": [{"text": m.content}],
                    }
                    for m in messages
                ],
                "generationConfig": generation,
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        candidate = r.json()["candidates"][0]
        return LLMResponse(
            text="".join(p.get("text", "") for p in candidate["content"]["parts"]),
            provider=self.name,
            model=self.model,
            latency_s=time.perf_counter() - t0,
            truncated=candidate.get("finishReason") == "MAX_TOKENS",
        )


class GroqProvider:
    name = "groq"
    ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: float = 60.0):
        self._key = api_key if api_key is not None else os.getenv("GROQ_API_KEY", "")
        self.model = model or os.getenv("GROQ_MODEL") or "llama-3.3-70b-versatile"
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self._key)

    def complete(self, system, messages, *, max_tokens=512, temperature=0.0, schema=None):
        t0 = time.perf_counter()
        extra: dict[str, object] = {}
        if schema is not None:
            # Groq's OpenAI-compatible endpoint offers json_object, not a schema,
            # so the schema is also stated in the prompt and validated on return.
            extra["response_format"] = {"type": "json_object"}
        r = httpx.post(
            self.ENDPOINT,
            headers={"Authorization": f"Bearer {self._key}"},
            json={
                "model": self.model,
                "messages": [{"role": "system", "content": system}]
                + [{"role": m.role, "content": m.content} for m in messages],
                "max_tokens": max_tokens,
                "temperature": temperature,
                **extra,
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        choice = r.json()["choices"][0]
        return LLMResponse(
            text=choice["message"]["content"],
            provider=self.name,
            model=self.model,
            latency_s=time.perf_counter() - t0,
            truncated=choice.get("finish_reason") == "length",
        )


# ── present, and permanently off ────────────────────────────────────────────


class AnthropicProvider:
    """Wired into the chain and unable to serve a single request.

    This class is deliberately not deleted. UPLIFT's constraint is zero paid
    inference, and the honest way to hold that line is to show the paid option
    sitting in the chain and refusing — with the refusal covered by a test —
    rather than to leave a gap that reads as an oversight and invites a
    well-meaning contributor to fill it.

    `available()` returns False even when ANTHROPIC_API_KEY is set, and
    `complete()` raises if called directly. Both are asserted.
    """

    name = "anthropic"
    why_disabled = (
        "Zero paid inference is a project constraint, not a default. Anthropic is "
        "metered, so this provider refuses even when a key is present. Removing this "
        "refusal is a budget decision for the owner, not a code change."
    )

    def __init__(self, model: str = "claude-opus-5") -> None:
        self.model = model

    def available(self) -> bool:
        return False

    def complete(self, system, messages, *, max_tokens=512, temperature=0.0, schema=None):
        raise RuntimeError(self.why_disabled)


# ── the chain ───────────────────────────────────────────────────────────────


class LLMChain:
    """Tries providers in order and records why each was passed over."""

    def __init__(self, providers: list[LLMProvider], quota: Quota) -> None:
        if not providers or providers[-1].name != "stub":
            providers = [*providers, StubProvider()]
        self.providers = providers
        self.quota = quota

    @classmethod
    def default(cls, quota: Quota | None = None) -> LLMChain:
        return cls(
            [
                OllamaProvider(),
                GeminiProvider(),
                GroqProvider(),
                AnthropicProvider(),
                StubProvider(),
            ],
            quota or Quota.from_env(),
        )

    def complete(
        self,
        system: str,
        messages: list[Message],
        *,
        max_tokens: int = 512,
        temperature: float = 0.0,
        schema: dict | None = None,
    ) -> LLMResponse:
        killswitch.check()

        skipped: list[str] = []
        for provider in self.providers:
            if not provider.available():
                skipped.append(f"{provider.name}(unavailable)")
                continue
            # The stub is never metered. It is arithmetic over a hash — there is
            # no cost to protect and no rate limit to respect — and metering it
            # breaks the one guarantee this chain exists to provide. A caller
            # that builds a chain without listing "stub" in its budget got an
            # appended stub with a limit of zero, so the terminal provider was
            # instantly "exhausted" and complete() raised. Totality cannot
            # depend on the caller remembering to fund the fallback.
            if provider.name != "stub" and not self.quota.consume(provider.name):
                skipped.append(f"{provider.name}(quota exhausted)")
                continue
            try:
                response = provider.complete(
                    system,
                    messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    schema=schema,
                )
            except Exception as exc:  # noqa: BLE001 — degrade on anything a provider does
                skipped.append(f"{provider.name}({type(exc).__name__})")
                continue
            return LLMResponse(
                text=response.text,
                provider=response.provider,
                model=response.model,
                latency_s=response.latency_s,
                truncated=response.truncated,
                degraded_from=tuple(skipped),
            )

        # Unreachable in practice: the stub is always present and always available.
        raise LLMError(f"no provider could serve the request; tried {skipped}")

    def structured(
        self,
        system: str,
        messages: list[Message],
        *,
        model_cls: type[T],
        max_tokens: int = 700,
        temperature: float = 0.0,
        retries: int = 1,
    ) -> tuple[T, LLMResponse]:
        """Return a validated object, or raise after exhausting the chain.

        Unlike `complete`, this CAN fail, deliberately. A turn that comes back as
        prose instead of the requested object is not a degraded answer a caller
        can render anyway — it is an absence, and the caller has to know.
        """
        schema = model_cls.model_json_schema()
        attempts: list[str] = []
        conversation = list(messages)

        for attempt in range(retries + 1):
            response = self.complete(
                system,
                conversation,
                max_tokens=max_tokens,
                temperature=temperature,
                schema=schema,
            )
            try:
                if response.truncated:
                    raise ValueError(
                        "the model ran out of token budget mid-object; under constrained "
                        "decoding the grammar closes it anyway, so this validates while "
                        "carrying a half-finished sentence"
                    )
                return model_cls.model_validate_json(_json_slice(response.text)), response
            except (ValidationError, ValueError) as exc:
                attempts.append(f"{response.provider}: {type(exc).__name__}")
                if attempt == retries:
                    break
                conversation = [
                    *messages,
                    Message("assistant", response.text[:1500]),
                    Message(
                        "user",
                        "That did not validate against the required schema. Return ONLY a "
                        f"JSON object matching it, correcting this: {str(exc)[:400]}",
                    ),
                ]

        raise LLMError(
            f"no provider returned a valid {model_cls.__name__} after {retries + 1} "
            f"attempts: {attempts}"
        )

    def health(self) -> list[dict[str, object]]:
        return [
            {
                "name": p.name,
                "model": p.model,
                "available": p.available(),
                "quota_remaining": self.quota.remaining(p.name),
                "disabled_reason": getattr(p, "why_disabled", None),
            }
            for p in self.providers
        ]


def _json_slice(text: str) -> str:
    """Pull the JSON object out of a reply wrapped in prose or fences.

    Unnecessary under constrained decoding on Ollama and Gemini; Groq's JSON mode
    and any model answering without schema support will happily wrap the object.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("```")[1]
        if stripped.startswith("json"):
            stripped = stripped[4:]
        stripped = stripped.strip()
    start, end = stripped.find("{"), stripped.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"no JSON object in reply: {text[:120]!r}")
    return stripped[start : end + 1]
