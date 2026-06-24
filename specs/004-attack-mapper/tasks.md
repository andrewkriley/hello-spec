---
description: "Task list for the Attack-Mapper role"
---

# Tasks: Attack-Mapper role

**Input**: `specs/004-attack-mapper/` (spec.md, plan.md)
**Tests**: Included (deterministic stub backend).

## Phase 1: Foundational
- [x] T001 Add `fleet.attack_mapper: { enabled: true }` to `config/evaluation.yaml`
- [x] T002 [P] Add an `AttackPath` dataclass to `hello_spec/foundry/lifecycle/models.py`
      (entry_class/location/fingerprint, impact_class/location/fingerprint, narrative, `to_dict()`)
- [x] T003 Add `AttackMapper(Role)` in `hello_spec/foundry/roles/extensions/attack_mapper.py`
      with a weakness-class → attack-role map (foothold/impact) and
      `map_attacks(store, sandbox, reports_dir, tick)`; re-export from `extensions/__init__.py`

## Phase 2: User Story 1 + 2 — chains (P1/P2)
- [x] T004 [P] [US1] `tests/test_attack_mapper.py`: `test_chains_credential_to_rce`,
      `test_paths_link_distinct_true_positives`
- [x] T005 [US1] Implement `map_attacks`: classify confirmed true-positives, link each
      foothold to each distinct impact as an `AttackPath` with a narrative (FR-001..004/006)

## Phase 3: User Story 3 — read-only (P3)
- [x] T006 [P] [US3] `test_no_findings_or_target_changed`, `test_zero_on_secure`
- [x] T007 [US3] Write the report atomically via the sandbox to
      `reports_dir/attack-paths.json` (FR-005); wire into `engine.py` after the
      Variant-Hunter, gated on `fleet.attack_mapper.enabled`; surface a path count

## Phase 4: Polish
- [x] T008 [P] Update the §6.3 Attack-Mapper row in `docs/ELEMENT-MAP.md`
- [x] T009 Run `make test` + a `make scan` spot-check of `build/reports/attack-paths.json`

## Dependencies
Foundational → US1/US2 → US3 → Polish. Maps: US1→SC-001/002, US3→SC-003/004.
