# Quickstart: validating the Remediator role

Prerequisites: Python 3.9+, `pyyaml`. Run from the repo root. The Remediator is
opt-in via `fleet.remediator.enabled: true` in `config/evaluation.yaml`.

## Run it

```bash
# Deterministic (stub) — reproducible
FOUNDRY_LLM_BACKEND=stub make scan

# Candidate artifacts land under the reports dir
ls build/reports/remediation-*.json
```

## What to expect (maps to Success Criteria)

| Check | Expected | Maps to |
|---|---|---|
| One candidate per confirmed TP with a mapped control (CWE-89/78/639/798) | 4 candidates, all `status: verified` | SC-001, FR-001 |
| Each verified candidate's verification block | `finding_closed: true`, `new_findings: 0`, `passed: true` | SC-002, FR-003/4 |
| The unmapped class (CWE-208, the rule-gap) | 1 candidate `status: no-control` | FR-008 |
| Target source after the run | byte-for-byte unchanged | SC-003, FR-005 |
| Each candidate artifact | carries `finding_fingerprint` + `control` | SC-004, FR-006 |
| Run against the secure target | zero candidates produced | SC-005 |

```bash
# No-mutation + zero-on-secure checks
git diff --quiet target/ && echo "target unchanged (SC-003 ok)"
make scan-secure   # then: ls build/reports/remediation-*.json 2>/dev/null | wc -l  -> 0
```

## Automated validation

```bash
make test    # includes tests/test_remediator.py
```

`tests/test_remediator.py` asserts, on the `stub` backend: verified vs
unverified labelling, the `no-control` path for CWE-208, no target mutation,
zero candidates on the secure target, and provenance presence — one assertion
per success criterion.

## References
- Role contract: [contracts/remediator-role.md](./contracts/remediator-role.md)
- Artifact schema: [contracts/candidate-remediation.schema.json](./contracts/candidate-remediation.schema.json)
- Data model: [data-model.md](./data-model.md)
