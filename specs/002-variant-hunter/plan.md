# Implementation Plan: Variant-Hunter role

**Branch**: `002-variant-hunter` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)

## Summary
Add the Foundry Variant-Hunter (§6.2). It reads the triaged finding store and,
for each confirmed true-positive, surfaces every other location sharing the same
weakness class as a **variant** (a lead) — including out-of-scope / non-security
siblings, each labelled with its verdict. It creates no findings, changes no
verdicts, and never touches the target; it writes a variant report for review.

## Technical Context
- **Language**: Python 3.9+. **Deps**: standard library; reuses `FindingStore`,
  `Sandbox`, `substrate/persistence.atomic_write_json`.
- **Testing**: pytest, deterministic stub backend (the hunt is a pure read over
  the store, so it is reproducible regardless of LLM backend).
- **Project type**: single project (extension role).

## Constitution Check (Foundry 11 principles) — PASS
- [x] **II. Surface Only What Survives** — variants are *leads* for a human, not
      promoted findings; they never enter the issue tracker as confirmed.
- [x] **VIII. Fingerprints Stable Under Edit** — variants key on the finding
      fingerprint; the same sibling is identified stably across runs.
- [x] **IX. Sandbox By Infrastructure** — the report is written only to a
      sandbox-writable path.
- [x] **X. The Operator Outranks Every Agent** — reports leads only; no findings
      invented, no verdicts changed.
- [x] **XI. Persist Atomically** — the report is written via atomic_write_json.
- [N/A] I, III–VII — the hunter neither judges, claims, nor reproduces; it groups
      already-judged findings. No new claim semantics introduced.

**Result**: PASS — no violations.

## CodeGuard Security Check

*Gate B (secure-coding), parallel to the Constitution Check — see
[`docs/METHODOLOGY.md`](../../docs/METHODOLOGY.md). Added retrospectively; the
gate post-dates this plan.*

- [x] **Secrets / injection / crypto / supply-chain** — N/A; the role is a pure,
      read-only grouping over the finding store. No untrusted input handling.
- [x] **Safe file handling** — the variant report is written only to a
      sandbox-writable path via `atomic_write_json`; the target is never touched.
- [x] **Pre-merge review** — covered by the engine-wide CodeGuard review,
      verdict CLEAN ([`docs/security-review.md`](../../docs/security-review.md),
      2026-06-24).

## Project Structure
```text
hello_spec/foundry/
├── lifecycle/models.py                    # + Variant dataclass
├── roles/extensions/variant_hunter.py     # NEW: VariantHunter(Role).hunt(...)
├── roles/extensions/__init__.py           # re-export the real role
└── engine.py                              # opt-in run after the Remediator
config/evaluation.yaml                     # + fleet.variant_hunter.enabled
tests/test_variant_hunter.py               # SC-001..005
docs/ELEMENT-MAP.md                        # §6.2 row
```

**Structure Decision**: Extension role, same shape as the Remediator. Pure read
over the existing store keeps it non-disruptive to the core pipeline and tests.

## Complexity Tracking
None — no constitution violations.
