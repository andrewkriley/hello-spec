---
description: "Task list for the Variant-Hunter role"
---

# Tasks: Variant-Hunter role

**Input**: `specs/002-variant-hunter/` (spec.md, plan.md)
**Tests**: Included (deterministic stub backend).

## Phase 1: Setup
- [x] T001 Add `fleet.variant_hunter: { enabled: true }` to `config/evaluation.yaml`

## Phase 2: Foundational
- [x] T002 [P] Add a `Variant` dataclass to `hello_spec/foundry/lifecycle/models.py` (source fingerprint, weakness_class, location, verdict, fingerprint) with `to_dict()`
- [x] T003 Add `VariantHunter(Role)` in `hello_spec/foundry/roles/extensions/variant_hunter.py` with `hunt(store, sandbox, reports_dir, tick)`; re-export from `roles/extensions/__init__.py` (replace the stub)

## Phase 3: User Story 1 — siblings of a confirmed bug (P1)
- [x] T004 [P] [US1] `tests/test_variant_hunter.py`: `test_finds_recurring_class_variant`, `test_no_variant_for_unique_class`
- [x] T005 [US1] Implement the hunt: for each confirmed true-positive, collect other findings with the same `weakness_class` and a different fingerprint as `Variant`s (FR-001/FR-002/FR-006)

## Phase 4: User Story 2 — nothing hides (P2)
- [x] T006 [P] [US2] `test_variant_includes_out_of_scope_sibling` (the `samples/` SQLi sibling, labelled `not-applicable`)
- [x] T007 [US2] Ensure variants include siblings of any verdict/scope, each carrying its verdict label (FR-003)

## Phase 5: User Story 3 — leads, not actions (P3)
- [x] T008 [P] [US3] `test_no_findings_or_target_changed`, `test_zero_on_secure`
- [x] T009 [US3] Write the report atomically via the sandbox to `reports_dir/variants.json` (FR-004/FR-005); wire the hunter into `engine.py` after the Remediator, gated on `fleet.variant_hunter.enabled`; surface a variant count

## Phase 6: Polish
- [x] T010 [P] Fill the §6.2 Variant-Hunter row in `docs/ELEMENT-MAP.md`
- [x] T011 Run `make test` + a `make scan` spot-check of `build/reports/variants.json`

## Dependencies
Setup → Foundational → US1 → US2 → US3 → Polish. Maps: US1→SC-001/003, US2→SC-002, US3→SC-004/005.
