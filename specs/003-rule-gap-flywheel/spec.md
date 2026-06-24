# Feature Specification: Rule-gap flywheel (Self-Improver authors + verifies rules)

**Feature Branch**: `003-rule-gap-flywheel`

**Created**: 2026-06-24

**Status**: Draft

**Input**: "Close the detection→prevention flywheel: when exploration finds a weakness class no rule covers, the Self-Improver (§6.5) authors a REAL CodeGuard rule for it and verifies the next sweep catches that class."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A lesson becomes a reusable rule (Priority: P1)
As the operator, when exploration confirms a weakness class that no existing rule
catches, I want the system to **author a real, valid CodeGuard rule** for that
class, so the one-off discovery becomes a repeatable check.

**Independent Test**: Run against the vulnerable target; confirm the recorded
CWE-208 rule-gap produces a CodeGuard-format rule file that parses and names a
matcher + weakness class.

**Acceptance Scenarios**:
1. **Given** a recorded rule-gap for CWE-208, **When** the Self-Improver runs,
   **Then** a CodeGuard rule file is authored with valid frontmatter and a
   Detector contract (`id`, `severity`, `weakness_class`, `matcher`).

### User Story 2 - The new rule actually works (Priority: P2)
As the operator I want the authored rule **verified** — shown to catch the class
on a fresh sweep — so I trust it before accepting it into the corpus.

**Independent Test**: Add the authored rule to the corpus and re-run detection;
confirm the gap's finding is now caught by a *rule* (not just exploration).

**Acceptance Scenarios**:
1. **Given** an authored rule for the gap, **When** verification re-runs the
   sweep with it added, **Then** the gap's finding is produced with a
   `rule:<id>` technique and the proposal is labelled verified.

### User Story 3 - Proposed, not silently merged (Priority: P3)
As the operator I want new rules **proposed for my acceptance**, never written
straight into the committed corpus, so I decide what becomes permanent.

**Independent Test**: After a run, the committed `rules/` directory is unchanged;
proposals exist only in the run's output location.

**Acceptance Scenarios**:
1. **Given** any run, **When** the Self-Improver completes, **Then** `rules/` is
   unchanged and proposals are written only under the sandbox output path.

### Edge Cases
- **No rule-gaps** (e.g. the secure target): author nothing.
- **A gap whose class has no authoring template**: report it, do not fabricate a
  rule that cannot verify.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: For each recorded rule-gap, the system MUST author a CodeGuard-format
  rule file (valid frontmatter + Detector contract) targeting that weakness class.
- **FR-002**: The authored rule MUST reference a real matcher so it can fire on a sweep.
- **FR-003**: The system MUST verify the authored rule by re-running detection with
  it added to the corpus and confirming the gap's finding is caught by a rule.
- **FR-004**: The system MUST label each proposal verified/unverified accordingly.
- **FR-005**: The system MUST write proposals to a sandbox-writable location and
  MUST NOT modify the committed rule corpus (the operator accepts a proposal by
  copying it into `rules/`).
- **FR-006**: When there are no rule-gaps, the system MUST author nothing.

### Key Entities
- **Rule Proposal**: an authored CodeGuard rule for one gap — weakness class,
  rule id, filename, matcher, the rule markdown, and a verified flag.

## Success Criteria *(mandatory)*
- **SC-001**: A CWE-208 rule-gap yields a CodeGuard rule file that parses and names
  a matcher + weakness class.
- **SC-002**: The authored rule, added to the corpus, catches the gap's finding by
  rule on re-scan (verified = true).
- **SC-003**: The committed `rules/` corpus is byte-for-byte unchanged by the run.
- **SC-004**: A target with no rule-gaps yields zero proposals.

## Assumptions
- Authoring uses a small per-class template keyed on weakness class; the matcher
  the rule references already exists in the Detector's matcher registry (the
  exploratory heuristic is promoted to a named, reusable matcher).
- The operator accepts a proposal by copying it into `rules/`; an accepted rule
  then validates under the real CodeGuard tooling (`make build-rules`).
- Optional extension behaviour (§6.5); the core pipeline is unchanged.
