# Implementation Plan: Remediator role

**Branch**: `001-remediator-role` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-remediator-role/spec.md`

## Summary

Add the Foundry **Remediator** extension role (spec §6.4). For each confirmed
true-positive whose vulnerability class maps to a known CodeGuard control, the
Remediator generates a **candidate remediation** and **verifies** it by applying
the patch to an isolated copy of the target and re-running detection: the
candidate is labelled `verified` only if the finding's fingerprint no longer
fires and no new finding appears. It never mutates the target and never
auto-applies — candidates are surfaced for human review. Findings whose class
has no mapped control are reported as "no control available".

## Technical Context

**Language/Version**: Python 3.9+ (`from __future__ import annotations`)

**Primary Dependencies**: standard library only (`ast`, `difflib`, `tempfile`,
`pathlib`); reuses the existing engine modules (`roles/indexer.py`,
`roles/detector.py`, `detection_rules.py`, `substrate/finding_store.py`,
`substrate/persistence.py`, `governance/sandbox.py`, `llm/adapter.py`).

**Storage**: filesystem — candidate artifacts written atomically under the
evaluation's `reports_dir` (a sandbox-writable path). No database.

**Testing**: pytest; deterministic `stub` backend so the role is reproducible.

**Target Platform**: local CLI engine (same as the rest of hello-spec).

**Project Type**: single project (the `hello_spec/foundry/` library + CLI).

**Performance Goals**: not performance-critical; cost scales with the number of
confirmed true-positives (typically a handful), one verification re-scan each.

**Constraints**: MUST NOT modify the target source; verification runs on an
isolated copy under a sandbox-writable temp path; deterministic in `stub` mode;
LLM use (cli/api) routes through the existing adapter + budget.

**Scale/Scope**: small — the demo target yields ≤6 confirmed true-positives.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against `.specify/memory/constitution.md` (Foundry 11 principles):

- [x] **I. Evidence Over Assertion** — a candidate is `verified` ONLY after a
      mechanical re-scan proves the fingerprint no longer fires and no new
      finding appears; never by the model's say-so.
- [x] **II. Surface Only What Survives** — verified candidates are the
      recommended output; unverified ones are recorded with a reason but never
      presented as fixes.
- [x] **III. Liveness By Heartbeat** — the role heartbeats through the existing
      `LivenessRegistry` like every other role; no wall-clock health signal.
- [x] **IV. Claims Are Atomic And Mortal** — reuses the existing work queue /
      liveness; no new shared-claim semantics are introduced.
- [x] **V. The Provider Is The Rate Arbiter** — patch generation in cli/api mode
      goes through the shared `LLMAdapter`/`Budget` (shared backoff); no new
      pre-throttle.
- [N/A] **VI. Coverage Before Yield** — the Remediator does not own the
      auto-stop decision; it consumes already-confirmed findings.
- [x] **VII. Exploited Means Demonstrated** — the remediation analogue: a fix is
      "verified" only by demonstration (re-scan), never inferred; the Remediator
      never sets `exploited`.
- [x] **VIII. Fingerprints Are Stable Under Edit** — candidates key on the
      finding fingerprint (path+symbol+class), so re-runs update, not duplicate.
- [x] **IX. Sandbox By Infrastructure** — verification writes the patched copy
      only to a sandbox-writable temp path; the target stays read-only.
- [x] **X. The Operator Outranks Every Agent** — proposes only; never
      auto-applies; output is reviewable and overridable.
- [x] **XI. Persist Atomically** — candidate artifacts written via
      `substrate/persistence.atomic_write_*`.

**Result**: PASS — no violations; Complexity Tracking not required.

## CodeGuard Security Check

*Gate B (secure-coding), parallel to the Constitution Check — see
[`docs/METHODOLOGY.md`](../../docs/METHODOLOGY.md). Added retrospectively; the
gate post-dates this plan.*

- [x] **Secrets** — N/A; the role reads no credentials.
- [x] **Input validation / injection** — the patch is built from the secure twin
      and applied to an isolated copy; no untrusted string-built commands/SQL.
- [x] **Safe subprocess & file handling** — temp copy via `tempfile.mkdtemp`,
      writes through the sandbox, target never modified.
- [x] **Deserialization / crypto / logging / supply-chain** — N/A or unchanged.
- [x] **Pre-merge review** — covered by the engine-wide CodeGuard review,
      verdict CLEAN ([`docs/security-review.md`](../../docs/security-review.md),
      2026-06-24).

## Project Structure

### Documentation (this feature)

```text
specs/001-remediator-role/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (role + artifact contracts)
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
hello_spec/foundry/
├── remediation.py                 # NEW: control-template map (CWE → fix) +
│                                   #      verify_candidate(patched_copy) helper
├── roles/
│   └── extensions/
│       ├── __init__.py            # MODIFIED: flesh out the Remediator stub, or
│       └── remediator.py          # NEW: Remediator(Role) — generate + verify
├── lifecycle/
│   └── models.py                  # MODIFIED (additive): CandidateRemediation dataclass
└── engine.py                      # MODIFIED: optionally run Remediator after the
                                    #           Reporter when enabled in fleet config

tests/
└── test_remediator.py             # NEW: verified/unverified, no-control, no-mutation,
                                    #       zero-on-secure, provenance (maps to SC-001..005)

docs/ELEMENT-MAP.md                # MODIFIED: fill the §6.4 Remediator row
config/evaluation.yaml             # MODIFIED (additive): fleet.remediator {enabled}
```

**Structure Decision**: Single project. The Remediator is an *extension* role, so
it slots into the existing `roles/extensions/` package and reuses the Indexer,
Detector, finding store, sandbox, and LLM adapter rather than introducing new
infrastructure. A small `remediation.py` holds the CWE→control template map and
the isolated-copy verification helper so the role stays thin.

## Complexity Tracking

> No constitution violations — section intentionally empty.
