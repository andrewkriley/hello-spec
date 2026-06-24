# Feature Specification: Variant-Hunter role

**Feature Branch**: `002-variant-hunter`

**Created**: 2026-06-24

**Status**: Draft

**Input**: "Add the Foundry Variant-Hunter extension role (spec §6.2): pattern replication — turn one confirmed finding into leads for its siblings elsewhere in the codebase."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One confirmed bug points at its siblings (Priority: P1)
As the operator, when a vulnerability is confirmed I want the system to show me
**every other place the same weakness pattern appears**, so a single confirmed
finding becomes a lead, not a dead end.

**Independent Test**: Run against the vulnerable target; confirm that for each
confirmed true-positive whose weakness class appears in more than one place, a
list of the other locations is produced.

**Acceptance Scenarios**:
1. **Given** a confirmed SQL-injection finding, **When** the hunter runs, **Then**
   it reports the other location(s) with the same weakness class as variants.
2. **Given** a confirmed finding whose class appears nowhere else, **When** the
   hunter runs, **Then** no variant is reported for it.

### User Story 2 - Nothing hides because it was filtered (Priority: P2)
As the operator I want variants to include locations that were marked
out-of-scope or non-security (e.g. a placeholder), each clearly labelled, so a
filtered-out sibling of a real bug is still surfaced for my awareness.

**Independent Test**: Confirm a variant points at an out-of-scope location
(the `samples/` SQL-injection sibling) and carries its current verdict.

**Acceptance Scenarios**:
1. **Given** a confirmed SQL injection and an out-of-scope sibling, **When** the
   hunter runs, **Then** the sibling appears as a variant labelled with its
   verdict (e.g. not-applicable).

### User Story 3 - Leads, not actions (Priority: P3)
As the operator I want the hunt to only *report* leads — never invent findings,
change verdicts, or touch the target — so it informs me without acting.

**Independent Test**: After a run, no finding/verdict changed and the target is
unchanged; variants exist only in the report.

**Acceptance Scenarios**:
1. **Given** any run, **When** the hunter completes, **Then** the finding store
   and the target source are unchanged.

### Edge Cases
- **No recurring class**: zero variants (e.g. the secure target — no confirmed bugs).
- **Same location**: a finding is never reported as a variant of itself.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: For each confirmed true-positive, the system MUST identify other
  findings that share its weakness class (different identity) and report them as
  variants.
- **FR-002**: Each variant MUST record the source true-positive it derives from,
  the location (path + symbol), the variant's current verdict, and its identity.
- **FR-003**: Variants MUST be included regardless of the sibling's verdict or
  scope, each labelled with that verdict.
- **FR-004**: The system MUST NOT create findings, change verdicts, or modify the
  target.
- **FR-005**: The system MUST write the variant report atomically through the
  sandbox to a designated output location.
- **FR-006**: When no weakness class recurs, the system MUST produce zero variants.

### Key Entities
- **Variant**: a lead derived from a confirmed finding — the source identity, the
  sibling's weakness class, location, current verdict, and identity.

## Success Criteria *(mandatory)*
- **SC-001**: Every recurring weakness class that has a confirmed true-positive
  yields at least one variant.
- **SC-002**: A confirmed SQL injection surfaces its out-of-scope sibling as a variant.
- **SC-003**: A weakness class present in only one place yields no variant.
- **SC-004**: No finding, verdict, or target byte is changed by the hunt.
- **SC-005**: Running against a target with no confirmed findings yields zero variants.

## Assumptions
- Operates over findings already produced and triaged by the core pipeline; it
  reads them, it does not re-detect (a fuller implementation could add an LLM
  hunt for instances the detector missed — out of scope here).
- "Same weakness pattern" is approximated by "same weakness class (CWE)".
- Optional extension role, run after the core eight; disabling it changes nothing else.
