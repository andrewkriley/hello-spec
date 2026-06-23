# hello-spec — project guidance

A teaching app that wires **Project CodeGuard** (secure-coding rules) and the
**Foundry Security Spec** (an AI vulnerability-discovery blueprint) together:
CodeGuard supplies the detection rules; a miniature Foundry engine consumes them.

## Layout
- `hello_spec/foundry/` — the engine (roles, substrate, governance, lifecycle,
  observability, llm adapter). Start at `engine.py`.
- `rules/` — CodeGuard-format detection rules (validated/converted by `make build-rules`).
- `target/vulnerable/` (seeded bugs) and `target/secure/` (CodeGuard controls applied).
- `tests/` — one test per Foundry constitutional principle + evidence gate + idempotency.
- `docs/ELEMENT-MAP.md` — traces every spec element to its implementing file.

## Conventions
- Python ≥3.9, `from __future__ import annotations`; no third-party runtime deps
  beyond pyyaml (anthropic optional for the `api` backend).
- The governing principles are in `.specify/memory/constitution.md` (the Foundry
  constitution). Keep each principle's enforcing code and its test in sync.
- Tests pin the deterministic `stub` LLM backend; `make scan` may use `claude -p`.

## Commands
- `make scan` / `make scan-secure` — run the engine; `make test`; `make build-rules`.

## Spec-driven workflow (spec-kit)
<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->
