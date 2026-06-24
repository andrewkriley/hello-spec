---
description: "Task list for the rule-gap flywheel"
---

# Tasks: Rule-gap flywheel

**Input**: `specs/003-rule-gap-flywheel/` (spec.md, plan.md)
**Tests**: Included (deterministic stub backend).

## Phase 1: Foundational
- [x] T001 Promote the exploratory CWE-208 heuristic to a named matcher
      `timing_unsafe_compare` in `hello_spec/foundry/roles/detector.py`, register it
      in `MATCHERS`, and refactor `_explore` to call it (behaviour unchanged: the
      matcher is not referenced by any committed rule, so the normal sweep still
      records the gap)
- [x] T002 [P] Add a `RuleProposal` dataclass to `hello_spec/foundry/lifecycle/models.py`
      (weakness_class, rule_id, filename, matcher, verified, path, `to_dict()`)
- [x] T003 Create `hello_spec/foundry/rule_authoring.py`: a CWE→rule template
      (`author_rule(gap)` → (filename, markdown)) producing valid CodeGuard
      frontmatter + a Detector contract, and `verify_rule(...)` that adds the rule
      to a temp corpus, re-runs Indexer+Detector over the target, and returns
      whether the gap's finding is now caught by a `rule:` technique

## Phase 2: User Story 1 + 2 — author & verify (P1/P2)
- [x] T004 [P] [US1] `tests/test_rule_gap_flywheel.py`: `test_matcher_registered_and_fires`,
      `test_self_improver_authors_valid_rule` (parses via `detection_rules.load_rules`,
      has matcher + CWE-208)
- [x] T005 [US1] Implement `SelfImprover.improve(rule_gaps, target_dir, rules_dir,
      index, sandbox, proposals_dir, tick)` in
      `hello_spec/foundry/roles/extensions/self_improver.py`: author a rule per gap,
      write atomically through the sandbox; re-export from `extensions/__init__.py`
- [x] T006 [P] [US2] `test_proposed_rule_closes_the_gap` (verified == true; the
      re-scan catches CWE-208 by rule)
- [x] T007 [US2] Wire verification into `improve()` (set `verified` per `verify_rule`)

## Phase 3: User Story 3 — proposed, not merged (P3)
- [x] T008 [P] [US3] `test_rules_corpus_unchanged`, `test_no_proposal_on_secure`
- [x] T009 [US3] Engine: replace `propose_rules(...)` with `improve(...)` in
      `hello_spec/foundry/engine.py`; write proposals under `reports_dir/proposals/`;
      surface a "authored + verified" summary; keep `rules/` untouched

## Phase 4: Polish
- [x] T010 [P] Update the §6.5 Self-Improver row in `docs/ELEMENT-MAP.md`
- [x] T011 Run `make test` + a `make scan` spot-check of `build/reports/proposals/`

## Dependencies
Foundational (T001-T003) → US1/US2 (T004-T007) → US3 (T008-T009) → Polish.
Maps: US1→SC-001, US2→SC-002, US3→SC-003/004.
