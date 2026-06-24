# Implementation Plan: Rule-gap flywheel

**Branch**: `003-rule-gap-flywheel` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)

> First feature built under the two-gate flow — both Gate A (Constitution Check)
> and Gate B (CodeGuard Security Check) are evaluated below.

## Summary
Complete Foundry's detection→prevention flywheel. The exploratory CWE-208
heuristic is promoted to a named Detector matcher (`timing_unsafe_compare`). The
**Self-Improver (§6.5)** then, for each recorded rule-gap, authors a real
CodeGuard-format rule that references that matcher and **verifies** it by adding
it to a temp corpus and re-running the sweep — confirming the gap's finding is now
caught by a *rule*. Proposals are written to a sandbox path; the committed `rules/`
corpus is never modified (the operator accepts a proposal by copying it in).

## Technical Context
- **Language**: Python 3.9+. **Deps**: stdlib + pyyaml; reuses `Indexer`,
  `Detector`, `detection_rules.load_rules`, `Sandbox`, `atomic_write_*`.
- **Testing**: pytest, deterministic stub backend (authoring + verification are
  deterministic).
- **Project type**: single project (extension role).

## Constitution Check (Gate A) — PASS
- [x] **I. Evidence Over Assertion** — a proposal is `verified` only after a re-scan
      demonstrates the rule catches the class; never asserted.
- [x] **II. Surface Only What Survives** — proposals are leads for human
      acceptance, not auto-merged rules.
- [x] **VIII. Fingerprints Stable Under Edit** — verification keys on the gap's
      finding fingerprint.
- [x] **IX. Sandbox By Infrastructure** — proposals + temp corpora written only to
      sandbox-writable paths.
- [x] **X. The Operator Outranks Every Agent** — the corpus changes only when a
      human copies a proposal in; the system proposes.
- [x] **XI. Persist Atomically** — proposal artifacts via `atomic_write_*`.
- [N/A] III–VII — no liveness/claim/rate/coverage/exploited semantics introduced.

**Result**: PASS.

## CodeGuard Security Check (Gate B) — PASS
- [x] **Secrets / crypto** — N/A; authors markdown, reads code; the rule it writes
      *teaches* constant-time comparison (the secure pattern) but uses none itself.
- [x] **Input validation / injection** — the matcher inspects indexed source via
      fixed string checks; no untrusted input is executed or string-built.
- [x] **Safe file handling** — proposals and temp corpora are created under
      sandbox-writable paths via `tempfile`/`atomic_write`; cleaned up; `rules/`
      never written.
- [x] **Deserialization** — rule frontmatter parsed with the existing
      `yaml.safe_load`-based loader; no eval/exec.
- [x] **Pre-merge review** — the diff will be self-reviewed against CodeGuard
      before merge and recorded in the PR (Gate B per `docs/METHODOLOGY.md`).

**Result**: PASS.

## Project Structure
```text
hello_spec/foundry/
├── roles/detector.py                      # + timing_unsafe_compare matcher; _explore reuses it
├── rule_authoring.py                      # NEW: CWE→rule template + verify_rule()
├── lifecycle/models.py                    # + RuleProposal dataclass
├── roles/extensions/self_improver.py      # NEW: SelfImprover.improve(...) (authors + verifies)
├── roles/extensions/__init__.py           # re-export the real Self-Improver
└── engine.py                              # call improve() instead of propose_rules()
tests/test_rule_gap_flywheel.py            # SC-001..004
docs/ELEMENT-MAP.md                        # §6.5 row
```

**Structure Decision**: Mirror the Remediator/Variant-Hunter shape. The matcher
promotion keeps detection logic in one place; authoring+verification live in a
thin `rule_authoring.py` so the role stays small.

## Complexity Tracking
None — no constitution violations.
