---
description: "Task list for the Remediator role"
---

# Tasks: Remediator role

**Input**: Design documents from `specs/001-remediator-role/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — hello-spec is test-driven (one assertion per success criterion).

**Organization**: Grouped by user story (P1 → P3) so each is independently testable.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 Add `fleet.remediator: { enabled: false }` to `config/evaluation.yaml` (additive; extension is opt-in per spec §6)

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 [P] Add `CandidateRemediation` and `VerificationResult` dataclasses (+ a `RemediationStatus` enum) to `hello_spec/foundry/lifecycle/models.py` per data-model.md
- [x] T003 Create `hello_spec/foundry/remediation.py` with `CONTROL_MAP` (CWE → control id) and a `apply_control(finding, source)` helper returning patched source text (template mode)
- [x] T004 Add `Remediator(Role)` skeleton in `hello_spec/foundry/roles/extensions/remediator.py` with the `remediate(...)` signature from contracts/remediator-role.md (returns `[]` for now) and re-export it from `hello_spec/foundry/roles/extensions/__init__.py` (replacing the stub)

**Checkpoint**: models + control map + role skeleton exist; stories can begin.

---

## Phase 3: User Story 1 - Reviewable fix for every confirmed finding (Priority: P1) 🎯 MVP

**Goal**: Each confirmed true-positive with a mapped control gets exactly one candidate; unmapped classes get `no-control`.

**Independent Test**: Run against `target/vulnerable/`; assert 4 candidates for the mapped classes (CWE-89/78/639/798) and 1 `no-control` for CWE-208.

### Tests for User Story 1

- [x] T005 [P] [US1] Create `tests/test_remediator.py` with `test_candidate_per_mapped_true_positive` (4 candidates) and `test_no_control_for_cwe208` (status `no-control`, no invented change) — stub backend

### Implementation for User Story 1

- [x] T006 [US1] Implement the per-CWE control templates in `hello_spec/foundry/remediation.py` (CWE-89→parameterized, CWE-78→argv+`shell=False`, CWE-639→ownership check, CWE-798→env secret)
- [x] T007 [US1] Implement the generation loop in `Remediator.remediate()` (`roles/extensions/remediator.py`): consider only `verdict == true-positive` (FR-007); produce a `CandidateRemediation` per finding; emit `no-control` for unmapped classes (FR-008); record provenance (`finding_fingerprint`, `control`) (FR-006)

**Checkpoint**: US1 produces candidates; MVP is demonstrable.

---

## Phase 4: User Story 2 - Verified, not asserted (Priority: P2)

**Goal**: A candidate is `verified` only after a re-scan proves the finding is closed and no new finding appears.

**Independent Test**: For a generated candidate, run verification and assert `verified` when the patch closes the finding, `unverified` (with reason) when it does not.

### Tests for User Story 2

- [x] T008 [P] [US2] Add `test_verified_when_fix_closes_finding` and `test_unverified_when_fix_fails` to `tests/test_remediator.py`

### Implementation for User Story 2

- [x] T009 [US2] Implement `verify_candidate(finding, patched_source, ...)` in `hello_spec/foundry/remediation.py`: write the patched copy under a sandbox-writable temp dir, re-run `Indexer` + `Detector` over it, return a `VerificationResult` (`finding_closed`, `new_findings`, `passed`)
- [x] T010 [US2] Wire verification into `Remediator.remediate()`: set `status = verified` iff `passed`, else `unverified` with `reason` (FR-003/FR-004); never set `exploited`

**Checkpoint**: US1 + US2 work — candidates carry a trustworthy verdict.

---

## Phase 5: User Story 3 - Operator stays in control (Priority: P3)

**Goal**: Candidates are surfaced for review, written atomically, and the target is never mutated.

**Independent Test**: After a run, `git diff --quiet target/` passes; secure target yields 0 candidates; each artifact has provenance.

### Tests for User Story 3

- [x] T011 [P] [US3] Add `test_target_not_mutated`, `test_zero_candidates_on_secure`, and `test_provenance_present` to `tests/test_remediator.py`

### Implementation for User Story 3

- [x] T012 [US3] Write each candidate to `reports_dir/remediation-<fingerprint>.json` via `substrate/persistence.atomic_write_json` routed through the `Sandbox` (FR-005/FR-006, Principles IX & XI)
- [x] T013 [US3] Add the post-condition no-mutation assertion (target bytes unchanged) at the end of `Remediator.remediate()`
- [x] T014 [US3] Wire the Remediator into `hello_spec/foundry/engine.py` after the Reporter, gated on `fleet.remediator.enabled`; surface a candidate count on the dashboard/rollup

**Checkpoint**: All three stories functional and independently testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T015 [P] Fill the §6.4 Remediator row in `docs/ELEMENT-MAP.md` (role → `roles/extensions/remediator.py`)
- [x] T016 [P] Add a short "Remediator (opt-in)" note to `README.md`
- [x] T017 Run `make test` (incl. `tests/test_remediator.py`) and the quickstart validation (`make scan`; inspect `build/reports/remediation-*.json`)

---

## Dependencies & Execution Order

- **Setup (T001)** → no dependencies.
- **Foundational (T002–T004)** → after Setup; **blocks all stories**.
- **US1 (T005–T007)** → after Foundational. MVP.
- **US2 (T008–T010)** → after Foundational; builds on US1's candidates but is independently testable.
- **US3 (T011–T014)** → after Foundational; T014 (engine wiring) is best after US1/US2 produce verified candidates.
- **Polish (T015–T017)** → after the desired stories.

### Parallel Opportunities

- T002 is [P] (models) alongside reading; T003/T004 touch different files.
- Each story's test task ([P]) can be written first, in parallel with sibling tests.
- T015 and T016 (docs) are [P].

## Implementation Strategy

**MVP** = Phase 1 + Phase 2 + Phase 3 (US1): candidates are produced and
reviewable. **Increment**: add US2 (verification) → US3 (operator control +
engine wiring) → Polish. Each story is a working, testable slice.

## Notes

- Tests pin the `stub` backend for reproducibility; `make test` stays offline.
- Every task names exact files; commit after each task or logical group.
- Maps to success criteria: US1→SC-001, US2→SC-002, US3→SC-003/004/005.
