# Feature Specification: Attack-Mapper role

**Feature Branch**: `004-attack-mapper`

**Created**: 2026-06-24

**Status**: Draft

**Input**: "Add the Foundry Attack-Mapper extension role (spec §6.3): chain confirmed findings into attack paths — a foothold (access) leading to an impact (damage)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bugs become an attack narrative (Priority: P1)
As the operator I want confirmed findings connected into attack paths — how a
*foothold* (something that gives an attacker access) enables an *impact*
(the damage) — so a list of separate bugs becomes a story a stakeholder
understands (e.g. "a hardcoded credential → remote code execution").

**Independent Test**: Run against the vulnerable target; confirm a path links a
confirmed credential-exposure finding to a confirmed code-execution finding.

**Acceptance Scenarios**:
1. **Given** a confirmed hardcoded credential and a confirmed command injection,
   **When** the mapper runs, **Then** an attack path links the two with a
   plain-language narrative.

### User Story 2 - Each path is explained and located (Priority: P2)
As the operator I want each path to name both findings, their locations, and the
chain in plain terms, so I can act on it.

**Independent Test**: Each path carries the entry and impact weakness classes,
both `path::symbol` locations, and a narrative sentence.

### User Story 3 - Read-only leads (Priority: P3)
As the operator I want the mapper to only *report* paths — invent no findings,
change no verdicts, touch nothing — so it informs without acting.

**Independent Test**: After a run, no finding/verdict changed and the target is
unchanged; paths exist only in the report.

### Edge Cases
- **No foothold or no impact** among confirmed findings (e.g. the secure target):
  zero paths.
- A finding is never chained to itself.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: From confirmed true-positives, the system MUST classify each by
  attack role (foothold / impact) using its weakness class.
- **FR-002**: For each foothold × impact pair of distinct findings, the system
  MUST produce an attack path linking them with a narrative.
- **FR-003**: Each path MUST record the entry and impact weakness class, location,
  and fingerprint, plus the narrative.
- **FR-004**: The system MUST chain only confirmed true-positives.
- **FR-005**: The system MUST write the attack-path report atomically through the
  sandbox and MUST NOT change any finding, verdict, or the target.
- **FR-006**: When there is no foothold or no impact, the system MUST produce no paths.

### Key Entities
- **Attack Path**: a link from a foothold finding to an impact finding — entry
  class/location/identity, impact class/location/identity, and a narrative.

## Success Criteria *(mandatory)*
- **SC-001**: A confirmed credential exposure + a confirmed code execution yield an
  attack path linking them.
- **SC-002**: Every path links two distinct confirmed true-positives.
- **SC-003**: A target with no foothold or no impact yields zero paths.
- **SC-004**: No finding, verdict, or target byte is changed by the mapper.

## Assumptions
- Attack-role classification is approximated by weakness class: foothold =
  credential/authentication weaknesses (CWE-798, CWE-208); impact =
  execution/data weaknesses (CWE-78, CWE-89, CWE-639, CWE-22). A fuller
  implementation would use the security map's trust boundaries and data flows.
- Optional extension role (§6.3); the core pipeline is unchanged.
