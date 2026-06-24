# Phase 0 Research: Remediator role

No `[NEEDS CLARIFICATION]` markers remained in the spec; the decisions below
record the approach and the alternatives weighed.

## D1 — Patch generation strategy

**Decision**: Dual-mode, mirroring the Triager. In `stub` mode the Remediator
applies a deterministic **control template** keyed on the finding's weakness
class (CWE). In `cli`/`api` mode the model proposes the change; the result is
verified identically before it can be labelled `verified`.

**Rationale**: Determinism keeps the test suite reproducible (NFR-004); the LLM
path shows the realistic use. Either way the *verifier*, not the generator,
decides success — consistent with Principle I.

**Alternatives considered**: LLM-only (rejected: non-deterministic tests,
unverifiable in CI); template-only (rejected: doesn't exercise the model path
the project already supports).

## D2 — Verification mechanism

**Decision**: Apply the candidate change to an **isolated copy** of the target
file under a sandbox-writable temp directory, then re-run the existing Indexer +
Detector over that copy. The candidate is `verified` iff (a) the finding's
fingerprint is absent from the new candidate set and (b) the total candidate
count does not increase (no new finding introduced).

**Rationale**: Reuses the real detection capability as an oracle, so "fixed"
means demonstrated, not asserted (Principle VII analogue). The target is never
mutated (Principle IX); writes go only to the temp path.

**Alternatives considered**: AST/structural assertion that the bad pattern is
gone (rejected: brittle, and re-detecting is the ground truth the project
already trusts); trusting the model's claim (rejected: violates Principle I).

## D3 — Control mapping (CWE → secure control)

**Decision**: A small table maps each detectable class to the secure control
already documented in the rule corpus and demonstrated in `target/secure/`:
CWE-89→parameterized query, CWE-78→argv+`shell=False`, CWE-639→ownership check,
CWE-798→read secret from environment. Classes with no entry (e.g. CWE-208, the
exploratory rule-gap class) yield "no control available".

**Rationale**: The secure twin is the project's ground-truth end state per
class, so the templates are already validated by `make scan-secure` (0
true-positives). Keeps the Remediator honest about what it can and cannot fix.

**Alternatives considered**: Inventing fixes for unmapped classes (rejected by
spec FR-008 — never force-patch); a generic "add a comment" stub (rejected:
provides no value, would falsely verify).

## D4 — Where the role runs

**Decision**: Optional stage after the Reporter, gated by
`fleet.remediator.enabled` in `config/evaluation.yaml` (default off — extension
roles are built/run after the core eight per spec §6).

**Rationale**: Keeps the core pipeline unchanged; the Remediator only consumes
findings the rest of the system already confirmed.

**Alternatives considered**: Always-on (rejected: §6 says extensions are opt-in);
a separate CLI entry point (deferred — reuse the engine run for now).
