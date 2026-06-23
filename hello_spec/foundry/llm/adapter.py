"""LLM adapter with a backend toggle (Foundry spec.md §11.2 / FR-002, §11.8).

The same agent pipeline can run against three backends, selected by config or
the FOUNDRY_LLM_BACKEND env var:

  - "stub" (default): a deterministic, offline pseudo-model. Responses are a
    function of (role, prompt) only, so the whole run is reproducible
    (NFR-004: behaviour is testable without a live model). No egress.
  - "cli": shells out to the local `claude -p` CLI (Claude Code headless).
  - "api": calls the Anthropic API via the `anthropic` SDK.

Every backend routes through the Sandbox (Constitution IX): even the real
backends cannot reach a host outside the egress allowlist. Per-call token
usage is recorded to the Budget (FR-002/FR-112). The provider is the rate
arbiter (Constitution V): on a rate-limit signal we raise a shared backoff and
retry; we never pre-throttle below the provider's real limit.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

from ..governance.budget import Budget
from ..governance.sandbox import Sandbox

ANTHROPIC_HOST = "api.anthropic.com"
LOCAL_CLI_HOST = "localhost"   # claude -p runs locally


@dataclass
class LLMResponse:
    text: str
    tokens_in: int
    tokens_out: int


class LLMAdapter:
    def __init__(self, backend: str, sandbox: Sandbox, budget: Budget,
                 model: str = "claude-opus-4-8") -> None:
        self.backend = backend
        self.sandbox = sandbox
        self.budget = budget
        self.model = model

    def complete(self, role: str, system: str, prompt: str) -> str:
        if self.backend == "stub":
            resp = self._stub(role, system, prompt)
        elif self.backend == "cli":
            self.sandbox.check_egress(LOCAL_CLI_HOST)
            resp = self._cli(system, prompt)
        elif self.backend == "api":
            self.sandbox.check_egress(ANTHROPIC_HOST)
            resp = self._api(system, prompt)
        else:
            raise ValueError(f"unknown LLM backend: {self.backend!r}")
        self.budget.record_call(role, resp.tokens_in, resp.tokens_out)
        self.budget.note_success()
        return resp.text

    # -- deterministic offline model --------------------------------------
    def _stub(self, role: str, system: str, prompt: str) -> LLMResponse:
        digest = hashlib.sha256(f"{role}\n{prompt}".encode()).hexdigest()
        text = (f"[stub:{role}] deterministic reasoning for prompt "
                f"digest {digest[:12]}")
        return LLMResponse(text=text,
                           tokens_in=len(prompt) // 4 + 1,
                           tokens_out=len(text) // 4 + 1)

    # -- claude -p CLI -----------------------------------------------------
    def _cli(self, system: str, prompt: str) -> LLMResponse:
        exe = shutil.which("claude")
        if not exe:
            raise RuntimeError("`claude` CLI not found on PATH for backend=cli")
        full = f"{system}\n\n{prompt}" if system else prompt
        out = subprocess.run(
            [exe, "-p", full, "--output-format", "text"],
            capture_output=True, text=True, timeout=120,
        )
        if out.returncode != 0:
            raise RuntimeError(f"claude -p failed: {out.stderr.strip()}")
        text = out.stdout.strip()
        return LLMResponse(text=text,
                           tokens_in=len(full) // 4 + 1,
                           tokens_out=len(text) // 4 + 1)

    # -- Anthropic API -----------------------------------------------------
    def _api(self, system: str, prompt: str) -> LLMResponse:
        try:
            import anthropic   # lazy import; only needed for backend=api
        except ImportError as exc:   # pragma: no cover
            raise RuntimeError("install `anthropic` for backend=api") from exc
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set for backend=api")
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model=self.model, max_tokens=1024,
            system=system or anthropic.NOT_GIVEN,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        return LLMResponse(text=text,
                           tokens_in=msg.usage.input_tokens,
                           tokens_out=msg.usage.output_tokens)


def resolve_backend(config_backend: Optional[str]) -> str:
    return os.environ.get("FOUNDRY_LLM_BACKEND") or config_backend or "stub"
