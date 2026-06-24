# Feature Specification: Remediator role

**Feature Branch**: `001-remediator-role`

**Created**: 2026-06-24

**Status**: Draft

**Input**: User description: "Add the Foundry Remediator extension role (spec §6.4): candidate patch generation + verification for confirmed findings."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A reviewable fix for every confirmed finding (Priority: P1)

As the operator of an evaluation, after the engine confirms a true-positive
vulnerability I want a concrete *candidate fix* attached to that finding, so
remediation starts from a reviewable proposal instead of a blank page.

**Why this priority**: This is the role's core value. Without a proposed change
the Remediator does nothing useful. A confirmed finding plus a candidate fix is
the smallest slice that delivers value on its own.

**Independent Test**: Run an evaluation against the vulnerable target; confirm
that each confirmed true-positive that maps to a known secure control receives
exactly one candidate remediation describing the change and the control it
applies.

**Acceptance Scenarios**:

1. **Given** a confirmed true-positive for SQL injection, **When** the
   Remediator runs, **Then** a candidate remediation is produced that applies
   the corresponding input-validation control and is linked to the finding.
2. **Given** a confirmed true-positive whose vulnerability class has no mapped
   secure control, **When** the Remediator runs, **Then** no patch is invented;
   the finding is reported as "no control available" for human attention.

---

### User Story 2 - Trustworthy candidates (verified, not asserted) (Priority: P2)

As the operator I want each candidate fix to be *verified* — shown to actually
remove the finding without breaking the target — so I can trust a "verified"
label and triage proposals quickly.

**Why this priority**: A proposal I cannot trust is noise. Verification is what
makes the candidate worth a reviewer's time, and it mirrors the project
principle that nothing is "done" by assertion.

**Independent Test**: For a produced candidate, re-run detection against the
patched code and confirm the finding's identity no longer fires and no new
findings appear; confirm the candidate is labelled verified only when both hold.

**Acceptance Scenarios**:

1. **Given** a candidate fix that, when applied, removes the finding and
   introduces no new findings, **When** verification runs, **Then** the
   candidate is labelled **verified**.
2. **Given** a candidate fix that does not remove the finding, or introduces a
   new finding, **When** verification runs, **Then** the candidate is labelled
   **unverified** with the reason recorded.

---

### User Story 3 - Operator stays in control (Priority: P3)

As the operator I want candidate fixes surfaced for my review and **never**
applied to the target automatically, so I remain the authority on what changes.

**Why this priority**: Safety and trust. It enforces the project's "operator
outranks every agent" and "no silent changes" principles. Important, but only
meaningful once candidates exist (P1) and are verified (P2).

**Independent Test**: Run the Remediator and confirm the target source is
unchanged afterwards; all candidates appear only in the review output.

**Acceptance Scenarios**:

1. **Given** any set of candidate fixes, **When** the Remediator completes,
   **Then** the target source is byte-for-byte unchanged.
2. **Given** the review output, **When** the operator inspects a candidate,
   **Then** they can trace it to its finding identity and the control it applies.

---

### Edge Cases

- **No confirmed findings** (e.g. the secure target): the Remediator produces
  zero candidates and reports nothing to fix.
- **Finding without a mapped control** (e.g. the exploratory timing-comparison
  rule-gap class): reported as "no control available", never force-patched.
- **A candidate that would change behaviour beyond the fix**: flagged unverified
  because verification detects new findings or a structural break.
- **Non-true-positive findings** (needs-review, code-quality, false-positive,
  not-applicable): skipped — the Remediator does not act on unconfirmed findings.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST produce a candidate remediation for each confirmed
  true-positive finding whose vulnerability class maps to a known secure control.
- **FR-002**: The system MUST associate each candidate with a single secure
  control and describe the change it makes.
- **FR-003**: The system MUST verify each candidate by checking, against the
  patched code, that (a) the finding's stable identity no longer fires and
  (b) no new findings are introduced.
- **FR-004**: The system MUST label a candidate **verified** only when both
  verification checks pass, and **unverified** with a recorded reason otherwise
  (no candidate may be called fixed by assertion).
- **FR-005**: The system MUST NOT modify the target source; candidates are
  surfaced for human review only.
- **FR-006**: The system MUST record provenance for each candidate: the finding
  identity it addresses and the control it applies.
- **FR-007**: The system MUST act only on confirmed true-positives and MUST skip
  all other verdicts.
- **FR-008**: When a confirmed finding has no mapped control, the system MUST
  report it as "no control available" rather than inventing a fix.
- **FR-009**: The system MUST operate within the evaluation's safety boundary,
  writing only to designated output locations and never to the protected target.

### Key Entities *(include if feature involves data)*

- **Candidate Remediation**: a proposed fix for one finding — references the
  finding identity, names the control applied, describes the change, and carries
  a verification status (verified / unverified) with a reason.
- **Verification Result**: the outcome of checking a candidate — whether the
  finding was closed and whether any new finding appeared.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of confirmed true-positives that map to a known control
  receive exactly one candidate remediation.
- **SC-002**: Every candidate labelled "verified" genuinely removes its finding
  on re-check (zero false "verified" — a labelled-verified candidate that does
  not close the finding is a defect).
- **SC-003**: Zero modifications are made to the target source by the Remediator
  (it proposes; it never applies).
- **SC-004**: 100% of candidates are traceable to their finding identity and the
  control applied.
- **SC-005**: Running the Remediator over a target with no confirmed findings
  (e.g. the secure target) yields zero candidates.

## Assumptions

- Only confirmed true-positives are remediated; needs-review, code-quality,
  false-positive, and not-applicable findings are out of scope for this role.
- Findings whose class has no mapped secure control are reported, not patched.
- The Remediator *proposes*; a human applies. This follows the project
  constitution (Operator Outranks Every Agent; no silent changes).
- Verification reuses the existing detection capability and the secure-control
  knowledge already present in the rule corpus; the secure target demonstrates
  the intended end state for each class.
- This role is an optional extension, built and run after the core eight roles;
  disabling it does not affect the rest of the evaluation.
