---
description: "Task list for the Deep-Tester role"
---

# Tasks: Deep-Tester role

**Input**: `specs/005-deep-tester/` (spec.md, plan.md)
**Tests**: Included (deterministic).

## Phase 1: Foundational
- [x] T001 Add the runnable target: `target/vulnerable/parser.py` (crashes on
      malformed input) and `target/secure/parser.py` (validated twin)
- [x] T002 Add `fleet.deep_tester: { enabled: true }` to `config/evaluation.yaml`
- [x] T003 [P] Add a `DeepTestFinding` dataclass to `hello_spec/foundry/lifecycle/models.py`
      (entry_point, crash_type, sample_input, `to_dict()`)
- [x] T004 Add `DeepTester(Role)` in `hello_spec/foundry/roles/extensions/deep_tester.py`
      with a fixed input corpus and `fuzz(target_dir, sandbox, reports_dir, tick)`
      that runs the corpus through `<target>/parser.py:parse_record` in one isolated
      subprocess and returns de-duplicated crashes; re-export from `extensions/__init__.py`

## Phase 2: User Story 1 + 2 — crashes (P1/P2)
- [x] T005 [P] [US1] `tests/test_deep_tester.py`: `test_finds_crash_inputs`,
      `test_distinct_crash_types_deduped`, `test_no_parser_no_findings`
- [x] T006 [US1] Implement `fuzz`: build the runner, spawn `subprocess.run([sys.executable,
      "-c", RUNNER, parser_path], shell=False, timeout=...)`, parse JSON crashes,
      de-dup by crash type (FR-001..004/006)

## Phase 3: User Story 3 — safe (P3)
- [x] T007 [P] [US3] `test_secure_parser_no_crashes`, `test_target_not_mutated`
- [x] T008 [US3] Write the report atomically via the sandbox to
      `reports_dir/deep-test.json` (FR-005); wire into `engine.py` after the
      Attack-Mapper, gated on `fleet.deep_tester.enabled`; surface a crash count

## Phase 4: Polish
- [x] T009 [P] Update the §6.1 Deep-Tester row in `docs/ELEMENT-MAP.md` (no stubs left)
- [x] T010 Run `make test` + a `make scan` spot-check of `build/reports/deep-test.json`

## Dependencies
Foundational → US1/US2 → US3 → Polish. Maps: US1→SC-001/003, US2→SC-003, US3→SC-002/004.
