# Showcase — run it yourself

A guided tour of hello-spec: clone → run → understand, in about five minutes.
Pair it with the [architecture diagrams](ARCHITECTURE.md) and the plain-language
[visual explainer](visual/index.html).

> **What this is:** a small, working demonstration that combines two open security
> standards — **Project CodeGuard** (the rules) and the **Foundry Security Spec**
> (the trustworthy AI inspector) — and makes an AI *prove its work*. The program it
> inspects is a teaching example with deliberate flaws (and a safe twin), not a
> real product.

## 1. Get it

```bash
git clone --recurse-submodules git@github.com:andrewkriley/hello-spec.git
cd hello-spec
```

The three submodules are the source specs you can read alongside the code:
`project-codeguard/`, `foundry-security-spec/`, `spec-kit/`.

## 2. Run the engine (offline, reproducible)

```bash
FOUNDRY_LLM_BACKEND=stub make scan
```

You'll see the **operator dashboard** (rendered from the substrate), then, below it,
the output of every role:

- **Findings by verdict** — the Triager's five verdicts. Only what survives the
  **evidence gate** is surfaced.
- **Remediator** — a proposed, *verified* fix per confirmed bug (it's applied to an
  isolated copy and re-scanned; the target is never touched).
- **Variant-Hunter** — the same weakness pattern found elsewhere (incl. out-of-scope).
- **Attack-Mapper** — findings chained into attack paths (foothold → impact).
- **Deep-Tester** — crashes found by *executing* a parser with generated input.
- **Self-Improver** — a real CodeGuard rule authored + verified for the class no
  rule caught (the detection→prevention flywheel).

A live capture of a real `claude -p` run is in [§6](#6-what-a-real-run-looks-like).

## 3. Prove the controls work

```bash
make scan-secure
```

Same engine, same rules, against the **secure twin** of the target — it finds
**zero** true-positives, zero variants, zero attack paths, zero crashes. The
CodeGuard controls close every finding.

## 4. Run the tests

```bash
make test          # 48 tests, deterministic stub backend
```

There's one test per **constitutional principle**, the evidence-gate worked
examples, idempotency, and one per success criterion for each extension role.

## 5. Exercise the CodeGuard tooling

```bash
make build-rules   # needs `uv`; validates our rules + converts to IDE bundles
```

This runs CodeGuard's **real** validator and format converter on the rules in
`rules/`, producing editor bundles under `build/`.

## 6. What a real run looks like

The capture below is a real `make scan` on the **live `claude -p` backend**
(detection and triage done by the model, verified by the architecture). Verdicts
vary run to run — that's a real model at work, which is exactly why the tests pin
the deterministic `stub` backend.

Captured 2026-06-24 · `backend=cli` · 96 detector + 6 triage model calls ·
~31k tokens · ≈ $0.14:

```text
================================================================
  HELLO-SPEC :: Foundry mini-engine — operator dashboard
================================================================
Agents:
   orch-1, indexer-1, carto-1, detector-1, triager-1,
   validator-1, coverage-1, reporter-1, improver-1   (all alive)

Findings by verdict:
   true-positive    5
   needs-review     1
   not-applicable   1
   code-quality     1
   by severity (true-positive): critical=2, high=2, medium=1
   exploited: 2          surfaced (published): 5

Coverage:  complete: True   items: 4/4
Budget:    spend: 0.1392 / 5.0   tokens: 31166   backoff: 0
Per-role cost rollup:
   detector     calls=96 tokens=26303 cost=0.1001
   triager      calls=6  tokens=3414  cost=0.0241
   remediator   calls=4  tokens=756   cost=0.0057
   cartographer calls=1  tokens=693   cost=0.0094

--- self-improver: authored CodeGuard rules (rule-gap flywheel) ---
  [verified  ] CWE-208 -> codeguard-0-hellospec-timing-comparison.md (matcher: timing_unsafe_compare)

--- remediator candidate fixes (proposed, not applied) ---
  [unverified ] CWE-89   parameterized-query
  [verified   ] CWE-78   argv-no-shell
  [verified   ] CWE-639  ownership-check
  [verified   ] CWE-798  env-secret
  [no-control ] CWE-208  no mapped secure control for CWE-208

--- variant-hunter leads (same pattern found elsewhere) ---
  CWE-89   also at samples/legacy.py::legacy_lookup [not-applicable]
  CWE-798  also at app.py::DEFAULT_TOKEN [code-quality]

--- attack-mapper chains (foothold → impact) ---
  CWE-798 (app.py::API_KEY) → CWE-89 (app.py::handle_export)
  CWE-798 (app.py::API_KEY) → CWE-78 (app.py::run_command)
  CWE-798 (app.py::API_KEY) → CWE-639 (app.py::get_payment)
  CWE-208 (app.py::check_token) → CWE-89/78/639
  ...

--- deep-tester crashes (found by running the code) ---
  IndexError   in parser.py::parse_record on input ''
  ValueError   in parser.py::parse_record on input 'id='
```

**Read the noise as a feature.** This run the SQL-injection remediation came back
`unverified` — the live model's verification (an LLM re-scan) is non-deterministic
and didn't clear it this time, even though the deterministic `stub` run verifies
it every time. That run-to-run variance is *exactly* why the test suite pins the
`stub` backend: the architecture is the constant, the model is the variable it
governs.

## 7. Where to look next

| You want… | Go to |
|---|---|
| The plain-language version | [`docs/visual/index.html`](visual/index.html) |
| The diagrams | [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) |
| How the 3 pieces relate (the canonical order) | [`docs/METHODOLOGY.md`](METHODOLOGY.md) |
| Every spec element → its file | [`docs/ELEMENT-MAP.md`](ELEMENT-MAP.md) |
| Whether the engine itself is secure | [`docs/security-review.md`](security-review.md) |
| How a feature was built | `specs/00X-*/` (spec → plan → tasks) |

## Switching backends

```bash
make scan                               # config default: live claude -p (cli)
FOUNDRY_LLM_BACKEND=stub make scan      # offline, deterministic
FOUNDRY_LLM_BACKEND=api ANTHROPIC_API_KEY=… make scan   # Anthropic API
```

Every backend is routed through the sandbox, so even the real ones can't reach a
host off the egress allowlist.
