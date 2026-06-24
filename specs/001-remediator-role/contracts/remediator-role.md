# Contract: Remediator role interface

The Remediator is a Foundry extension role. It exposes one entry point, mirroring
the other roles in `hello_spec/foundry/roles/`.

## Method

```
Remediator.remediate(store, index, target_dir, rules_dir, sandbox, reports_dir, tick)
  -> list[CandidateRemediation]
```

### Inputs
- `store`: the `FindingStore` after triage/validation (read-only use here).
- `index`: the `CodeIndex` from the Indexer.
- `target_dir`: the target source root (read-only; never written).
- `rules_dir`: the CodeGuard rule corpus (for control lookup / re-scan).
- `sandbox`: the `Sandbox`; all writes go through it.
- `reports_dir`: sandbox-writable output location for candidate artifacts.
- `tick`: logical clock for heartbeat + activity feed.

### Behaviour (must hold)
1. Considers ONLY findings with `verdict == true-positive` (FR-007).
2. For each, looks up the control by `weakness_class`:
   - no mapping → emit `CandidateRemediation(status=no-control)` (FR-008); continue.
   - mapping → generate `change` (template in stub mode; LLM in cli/api).
3. Verifies by writing the patched copy under a temp path inside `reports_dir`'s
   sandbox boundary, re-running Indexer+Detector over it, and producing a
   `VerificationResult`. Sets `status = verified` iff `passed` (FR-003/FR-004).
4. MUST NOT modify any file under `target_dir` (FR-005). A post-condition check
   asserts the target's bytes are unchanged.
5. Writes each candidate artifact atomically to `reports_dir` (Principle XI) with
   provenance: `finding_fingerprint` + `control` (FR-006).
6. Heartbeats and emits to the activity feed/session log like any role.

### Outputs
- Returns the list of `CandidateRemediation`.
- Side effect: one `remediation-<fingerprint>.json` per candidate under
  `reports_dir` (see the artifact schema).

### Error handling
- LLM/parse failure in cli/api mode → fall back to the template, or emit
  `unverified(reason="generation failed")`; never crash the fleet (matches the
  Triager's fallback posture).
