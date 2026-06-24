# Implementation Plan: Deep-Tester role

**Branch**: `005-deep-tester` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)

## Summary
Add the Foundry Deep-Tester (§6.1). It generates a deterministic corpus of inputs
and executes a runnable entry point (`parse_record` in `<target>/parser.py`) in an
**isolated subprocess** with a timeout, reporting de-duplicated crashes (one per
exception type) with a representative input. The vulnerable parser crashes
(IndexError/ValueError) on malformed input; the secure twin validates and yields
none. Read-only with respect to the target; writes a report through the sandbox.

## Technical Context
- **Language**: Python 3.9+. **Deps**: stdlib (`subprocess`, `json`, `importlib`).
- **Testing**: pytest. The corpus is fixed and the parser is pure, so crashes are
  deterministic. One subprocess per run (the child fuzzes the whole corpus).
- **Project type**: single project (extension role).

## Constitution Check (Gate A) — PASS
- [x] **IX. Sandbox By Infrastructure** — target code executes in a separate
      process with a timeout; the report writes only to a sandbox-writable path.
- [x] **X. The Operator Outranks Every Agent** — the target source is never
      modified; the role reports leads.
- [x] **XI. Persist Atomically** — report via `atomic_write_json`.
- [x] **II. Surface Only What Survives** — de-duplicated, representative crashes.
- [N/A] I, III–VIII — no verdict/claim/fingerprint semantics introduced; results
      are execution observations.

**Result**: PASS.

## CodeGuard Security Check (Gate B) — PASS
- [x] **Safe subprocess** — `subprocess.run([sys.executable, "-c", RUNNER, path])`,
      argv form, `shell=False`, `timeout` set; the input corpus is passed as data
      to the child, never to a shell.
- [x] **Executing target code** — isolated in a child process (Principle IX), with
      a timeout; documented as the teaching-grade equivalent of containerized
      isolation (same posture as the in-process Sandbox).
- [x] **Input validation / injection** — no untrusted value reaches a shell, SQL,
      or path; the parser path is a known target file.
- [x] **Safe file handling** — only the report is written, via `atomic_write_json`
      to a sandbox path; the target is never written.
- [x] **Pre-merge review** — diff reviewed against CodeGuard, recorded in the PR.

**Result**: PASS.

## Project Structure
```text
target/vulnerable/parser.py                 # NEW: runnable parser with a crash bug
target/secure/parser.py                     # NEW: validated twin (no crashes)
hello_spec/foundry/
├── lifecycle/models.py                      # + DeepTestFinding dataclass
├── roles/extensions/deep_tester.py          # NEW: DeepTester(Role).fuzz(...)
├── roles/extensions/__init__.py             # re-export the real role
└── engine.py                                # opt-in run after the Attack-Mapper
config/evaluation.yaml                       # + fleet.deep_tester.enabled
tests/test_deep_tester.py                    # SC-001..004
docs/ELEMENT-MAP.md                          # §6.1 row (no stubs left)
```

**Structure Decision**: One subprocess fuzzes the whole corpus and returns JSON,
so isolation is honoured with a single spawn per run. The parser is a tiny,
self-contained addition that triggers no static matcher, so existing finding
counts and tests are unaffected.

## Complexity Tracking
None — no constitution violations.
