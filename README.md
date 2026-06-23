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

Both are vendored here as git submodules (`project-codeguard/`,
`foundry-security-spec/`) so you can read the source specs alongside the code.

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
| `stub` (default) | `make scan` | deterministic, offline, reproducible (honours NFR-004) |
| `cli` | `FOUNDRY_LLM_BACKEND=cli make scan` | shells out to the local `claude -p` CLI |
| `api` | `FOUNDRY_LLM_BACKEND=api ANTHROPIC_API_KEY=… make scan` | Anthropic API (`pip install '.[api]'`) |

Every backend is routed through the sandbox, so even the real ones cannot reach
a host outside the egress allowlist (Constitution IX).

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

## Learning path

1. Read `docs/ELEMENT-MAP.md` and pick a concept.
2. Read its spec section in `foundry-security-spec/` or `project-codeguard/`.
3. Read the implementing file in `hello_spec/foundry/`.
4. Run `make scan` and read the dashboard + `build/reports/`.
5. Read `tests/test_principles.py` to see each constitutional principle asserted.

> ⚠️ `target/vulnerable/` contains intentional vulnerabilities for teaching. It
> is self-contained, does not run a server, and must never be deployed.
