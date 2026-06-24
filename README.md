# hello-spec

A **hello-world that learns and applies** the design patterns and controls of two
security projects, by wiring them together into one small, runnable system:

- **[Project CodeGuard](https://github.com/cosai-oasis/project-codeguard)** —
  model-agnostic, secure-by-default **rules** for AI coding agents (markdown +
  YAML frontmatter, tags, languages, IDE/agent format converters).
- **[Foundry Security Spec](https://github.com/CiscoDevNet/foundry-security-spec)**
  — a **blueprint** for an AI vulnerability-discovery engine (8 agent roles, 143
  functional requirements, an 11-principle constitution, an evidence gate, a
  coordination substrate, governance and observability).

A third submodule, **[spec-kit](https://github.com/github/spec-kit)**, provides
the spec-driven-development workflow Foundry is designed to be consumed with
(see [Spec-driven development](#spec-driven-development-spec-kit) below).

All three are vendored here as git submodules (`project-codeguard/`,
`foundry-security-spec/`, `spec-kit/`) so you can read the source specs
alongside the code.

> 🟢 **New here, or not technical?** Open the plain-language, illustrated
> explainer at **[`docs/visual/index.html`](docs/visual/index.html)** — or the
> one-page **[`docs/visual/poster.pdf`](docs/visual/poster.pdf)**. No jargon required.

## The idea in one sentence

> **CodeGuard supplies the detection knowledge; Foundry is the engine that
> consumes it.** Foundry's own worked example says CodeGuard is "the format the
> seed assumes" — so this repo makes that literal.

A tiny, deliberately-vulnerable target app is scanned by **CodeGuard-format
rules** inside a miniature **Foundry engine** that implements all 8 roles, the
full finding lifecycle, the coordination substrate, governance, observability,
and demonstrably honours all 11 constitutional principles. The *fixes* in the
secure twin apply CodeGuard's secure-by-default controls — and the engine then
finds nothing.

## What's here

```
rules/                     5 CodeGuard-format detection rules (authored here)
target/vulnerable/         the seeded-vulnerable "hello world" app
target/secure/             the same app with CodeGuard controls applied
hello_spec/foundry/        the miniature Foundry engine (roles, substrate,
                           governance, lifecycle, observability, llm adapter)
config/evaluation.yaml     the Foundry §12 configuration (all sections)
tests/                     11 principle tests + evidence gate + idempotency
docs/ELEMENT-MAP.md        traceability: every spec element -> the file that applies it
scripts/build_rules.sh     runs the REAL CodeGuard validate + convert tooling
```

Start with **[`docs/ELEMENT-MAP.md`](docs/ELEMENT-MAP.md)** — it maps every
CodeGuard and Foundry element to the exact file that exercises it.

## Quick start

```bash
git clone --recurse-submodules git@github.com:andrewkriley/hello-spec.git
cd hello-spec

# 1. Run the engine against the vulnerable target (offline, deterministic)
make scan

# 2. Run against the secure target — expect ZERO true-positives
make scan-secure

# 3. Run the test suite (principles, evidence gate, idempotency)
make test

# 4. Exercise the real CodeGuard tooling: validate + convert to IDE bundles
make build-rules     # needs `uv` (https://docs.astral.sh/uv/) for the CodeGuard repo
```

`make scan` needs only Python 3.9+ and `pyyaml`. `make build-rules` runs
CodeGuard's own scripts, which require Python ≥3.11 — the script uses `uv` to
provide that automatically.

## LLM backend toggle

Foundry agents reach a model through one sandboxed adapter
(`hello_spec/foundry/llm/adapter.py`). Pick a backend without changing code:

| Backend | How | Notes |
|---|---|---|
| `cli` (config default) | `make scan` | shells out to the local `claude -p` CLI |
| `stub` | `FOUNDRY_LLM_BACKEND=stub make scan` | deterministic, offline, reproducible (honours NFR-004); pinned by the tests |
| `api` | `FOUNDRY_LLM_BACKEND=api ANTHROPIC_API_KEY=… make scan` | Anthropic API (`pip install '.[api]'`) |

In `cli`/`api` the **Detector** evaluates the rules and the **Triager** assigns
verdicts using the model (the Cartographer also narrates with it); in `stub` all
of these are deterministic. Every backend is routed through the sandbox, so even
the real ones cannot reach a host outside the egress allowlist (Constitution IX).

## What a run shows

Against `target/vulnerable/` the engine produces all five Triager verdicts,
each grounded in real investigation:

| Verdict | Example finding |
|---|---|
| `true-positive` | SQL injection, command injection, IDOR, hardcoded `sk_live_…` key, timing-unsafe token compare |
| `false-positive` | a `safe_join` whose `commonpath` check already defeats traversal |
| `needs-review` | a vulnerable dependency (no in-code evidence to satisfy the gate) |
| `code-quality` | a `changeme-please` placeholder (a defect, not an exploitable secret) |
| `not-applicable` | a finding in the out-of-scope `samples/` path |

It also records a **rule-gap** for the timing-comparison class that no authored
rule covers, and the Self-Improver proposes a new rule for it — the CodeGuard
rule-gap flywheel.

Against `target/secure/` the same pipeline finds **zero** true-positives: the
CodeGuard controls close every finding.

## Spec-driven development (spec-kit)

This repo is initialised with [spec-kit](https://github.com/github/spec-kit), the
toolkit Foundry's README assumes. That gives you the spec-driven workflow as
Claude Code slash commands (`/speckit-constitution`, `/speckit-specify`,
`/speckit-clarify`, `/speckit-plan`, `/speckit-tasks`, `/speckit-implement`,
`/speckit-analyze`), backed by `.specify/` (templates + scripts).

The project's governing constitution lives at
**`.specify/memory/constitution.md`** — it adopts the **Foundry constitution's
11 principles**, which is exactly where Foundry says to place them before running
the workflow. `/speckit-plan` and `/speckit-analyze` then check any plan or task
list against those principles.

To (re)install or update spec-kit's scaffolding:

```bash
uvx --from ./spec-kit specify init --here --integration claude --script sh --force
```

This makes hello-spec a worked example of the *whole* Foundry loop: the seed spec
(`foundry-security-spec/`) → spec-kit workflow → an implementation
(`hello_spec/`) that the constitution governs and the tests verify.

## Remediator (opt-in extension role)

The Foundry **Remediator** (§6.4) is implemented as a worked example of the
spec-driven workflow (`specs/001-remediator-role/`). When enabled
(`fleet.remediator.enabled` in `config/evaluation.yaml`), after reporting it
proposes a candidate fix for each confirmed true-positive and **verifies** it by
applying the patch to an isolated copy and re-running detection — labelling it
`verified` only if the finding closes and nothing new appears. It never mutates
the target and never auto-applies (Constitution X); unmapped classes are reported
`no-control`. `make scan` prints the candidate fixes; artifacts land in
`build/reports/remediation-*.json`.

## Learning path

1. Read `docs/ELEMENT-MAP.md` and pick a concept.
2. Read its spec section in `foundry-security-spec/` or `project-codeguard/`.
3. Read the implementing file in `hello_spec/foundry/`.
4. Run `make scan` and read the dashboard + `build/reports/`.
5. Read `tests/test_principles.py` to see each constitutional principle asserted.

> ⚠️ `target/vulnerable/` contains intentional vulnerabilities for teaching. It
> is self-contained, does not run a server, and must never be deployed.
