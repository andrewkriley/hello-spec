# hello-spec — project guidance

A teaching app that wires **Project CodeGuard** (secure-coding rules) and the
**Foundry Security Spec** (an AI vulnerability-discovery blueprint) together:
CodeGuard supplies the detection rules; a miniature Foundry engine consumes them.

**Order of operations** (see [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md)): Foundry
spec + constitution → spec-kit (**Gate A**: Foundry constitution) → CodeGuard
secure-coding review (**Gate B**) → implementation. CodeGuard has two roles — the
Detector's rule corpus *and* the secure-coding gate on the code we write.

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
- Every feature clears two gates in the plan template: the **Constitution Check**
  (Foundry invariants) and the **CodeGuard Security Check** (secure-coding); review
  the diff against CodeGuard before merge (see `docs/security-review.md`).
- Tests pin the deterministic `stub` LLM backend; `make scan` may use `claude -p`.

## Commands
- `make scan` / `make scan-secure` — run the engine; `make test`; `make build-rules`.

## Spec-driven workflow (spec-kit)
<!-- SPECKIT START -->
Active feature: **Remediator role** (Foundry §6.4).
For technologies, project structure, and approach, read the current plan:
`specs/001-remediator-role/plan.md` (spec, research, data-model, contracts, and
quickstart live alongside it under `specs/001-remediator-role/`).
<!-- SPECKIT END -->
