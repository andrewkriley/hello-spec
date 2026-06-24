# Phase 1 Data Model: Remediator role

## Entities

### CandidateRemediation
A proposed fix for exactly one finding.

| Field | Type | Notes |
|---|---|---|
| `finding_fingerprint` | string | the finding this addresses (path+symbol+class); the join key (Principle VIII) |
| `weakness_class` | string | CWE of the finding, e.g. `CWE-89` |
| `control` | string | the secure control applied, e.g. `parameterized-query`, or `none` |
| `change` | string | human-readable description / unified diff of the proposed change |
| `status` | enum | `verified` \| `unverified` \| `no-control` |
| `reason` | string | why unverified / why no control (recorded, never silent) |
| `generated_by` | enum | `template` (stub) \| `llm` (cli/api) |

**Validation rules**
- `status = verified` requires a passing `VerificationResult` (FR-004).
- `control = none` ⇒ `status = no-control` and no `change` is invented (FR-008).
- exactly one `CandidateRemediation` per confirmed-true-positive-with-control (FR-001/SC-001).

### VerificationResult
The outcome of checking one candidate against an isolated patched copy.

| Field | Type | Notes |
|---|---|---|
| `finding_closed` | bool | the finding's fingerprint is absent after the patch |
| `new_findings` | int | count of findings introduced by the patch (must be 0) |
| `passed` | bool | `finding_closed and new_findings == 0` |

**State transition (per candidate)**
```
generate → (control? no → no-control)
         → (control? yes → patch isolated copy → re-scan → VerificationResult)
                                                         → passed  → verified
                                                         → !passed → unverified(reason)
```

## Control map (CWE → control)

| Weakness | Control | Source of truth |
|---|---|---|
| CWE-89 | parameterized query | `rules/codeguard-0-hellospec-sql-injection.md`, `target/secure` |
| CWE-78 | argv form, `shell=False` | `rules/codeguard-0-hellospec-command-injection.md`, `target/secure` |
| CWE-639 | ownership check before return | `rules/codeguard-0-hellospec-idor.md`, `target/secure` |
| CWE-798 | read secret from environment | `rules/codeguard-1-hellospec-hardcoded-credentials.md`, `target/secure` |
| CWE-208 | *(none)* | rule-gap class → `no-control` |
| CWE-22 | *(n/a — already safe)* | false-positive in demo; not remediated |

## Relationships

- `CandidateRemediation.finding_fingerprint` → `Finding.fingerprint` (existing
  model in `lifecycle/models.py`).
- The Remediator reads confirmed findings from the existing `FindingStore` and
  writes `CandidateRemediation` artifacts to the `reports_dir` via atomic writes.
