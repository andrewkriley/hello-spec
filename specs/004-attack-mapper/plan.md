# Implementation Plan: Attack-Mapper role

**Branch**: `004-attack-mapper` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)

## Summary
Add the Foundry Attack-Mapper (§6.3). It reads confirmed true-positives, labels
each by attack role (foothold vs impact) from its weakness class, and links each
foothold to each impact as an **attack path** with a plain-language narrative
(e.g. hardcoded credential → remote code execution). Read-only: it invents no
findings, changes no verdicts, never touches the target; it writes an attack-path
report for review.

## Technical Context
- **Language**: Python 3.9+. **Deps**: stdlib; reuses `FindingStore`, `Sandbox`,
  `atomic_write_json`.
- **Testing**: pytest, deterministic stub backend (a pure read over the store).
- **Project type**: single project (extension role).

## Constitution Check (Gate A) — PASS
- [x] **II. Surface Only What Survives** — paths are leads built only from
      already-confirmed findings; nothing new is promoted.
- [x] **VIII. Fingerprints Stable Under Edit** — paths reference finding fingerprints.
- [x] **IX. Sandbox By Infrastructure** — the report is written only to a
      sandbox-writable path.
- [x] **X. The Operator Outranks Every Agent** — read-only; invents nothing,
      changes nothing.
- [x] **XI. Persist Atomically** — report via `atomic_write_json`.
- [N/A] I, III–VII — neither judges, claims, nor reproduces; chains existing verdicts.

**Result**: PASS.

## CodeGuard Security Check (Gate B) — PASS
- [x] **Secrets / injection / crypto / supply-chain** — N/A; pure read-only
      grouping over the store; no untrusted input handling, no subprocess.
- [x] **Safe file handling** — the report is written only to a sandbox-writable
      path via `atomic_write_json`; the target is never touched.
- [x] **Pre-merge review** — diff reviewed against CodeGuard before merge, recorded
      in the PR (Gate B per `docs/METHODOLOGY.md`).

**Result**: PASS.

## Project Structure
```text
hello_spec/foundry/
├── lifecycle/models.py                    # + AttackPath dataclass
├── roles/extensions/attack_mapper.py      # NEW: AttackMapper(Role).map_attacks(...)
├── roles/extensions/__init__.py           # re-export the real role
└── engine.py                              # opt-in run after the Variant-Hunter
config/evaluation.yaml                     # + fleet.attack_mapper.enabled
tests/test_attack_mapper.py                # SC-001..004
docs/ELEMENT-MAP.md                        # §6.3 row
```

**Structure Decision**: Same shape as Variant-Hunter — read-only over the store,
non-disruptive to the core pipeline and tests.

## Complexity Tracking
None — no constitution violations.
