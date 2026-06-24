# Feature Specification: Deep-Tester role

**Feature Branch**: `005-deep-tester`

**Created**: 2026-06-24

**Status**: Draft

**Input**: "Add the Foundry Deep-Tester extension role (spec §6.1): input-generation testing — fuzz a runnable entry point and report inputs that crash it."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find bugs by running the code (Priority: P1)
As the operator I want the system to **generate inputs and actually run** a target
entry point, reporting the inputs that crash it, so I catch robustness/validation
bugs that static rules can't see.

**Independent Test**: Run against the vulnerable target; confirm the fuzz reports
at least one crashing input for the parser entry point, with the exception type.

**Acceptance Scenarios**:
1. **Given** a parser that crashes on malformed input, **When** the Deep-Tester
   runs, **Then** it reports the crashing input(s) and the exception type(s).
2. **Given** a validated parser, **When** the Deep-Tester runs, **Then** it
   reports no crashes.

### User Story 2 - Distinct, de-duplicated crashes (Priority: P2)
As the operator I want one entry per distinct crash type (not hundreds of the
same), so the report is actionable.

**Independent Test**: Each reported crash type appears once with a representative
input.

### User Story 3 - Safe to run (Priority: P3)
As the operator I want the target code executed in **isolation** and the run to
change nothing in my source, so fuzzing is safe.

**Independent Test**: After a run, the target source is unchanged; execution
happens in a separate process.

### Edge Cases
- **No runnable entry point** (target has no `parser.py`): report nothing.
- **An input that hangs**: bounded by a timeout and reported as a hang, not a freeze.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: The system MUST generate a corpus of inputs and execute a target
  entry point on each, recording inputs that cause an unhandled crash.
- **FR-002**: Each finding MUST record the entry point, the exception type, and a
  representative crashing input.
- **FR-003**: Findings MUST be de-duplicated to one per distinct crash type.
- **FR-004**: Target execution MUST happen in an isolated subprocess with a timeout
  (Principle IX); a hang MUST be bounded and reported, not left to freeze.
- **FR-005**: The system MUST write its report atomically through the sandbox and
  MUST NOT modify the target.
- **FR-006**: When the target has no runnable entry point, the system MUST report nothing.

### Key Entities
- **Deep-Test Finding**: a crash discovered by execution — entry point, exception
  type, and a representative input.

## Success Criteria *(mandatory)*
- **SC-001**: The vulnerable parser yields at least one crashing input with its
  exception type.
- **SC-002**: The validated (secure) parser yields zero crashes.
- **SC-003**: Each distinct crash type is reported once.
- **SC-004**: The target source is unchanged by a run.

## Assumptions
- The entry point is a function `parse_record(str)` in `<target>/parser.py`
  (a convention for the demo); a fuller implementation would discover entry points
  from the security map and support more signatures.
- Execution isolation here is a subprocess with a timeout; a production deployment
  would containerize it (consistent with the in-process Sandbox simplification).
- Optional extension role (§6.1); the core pipeline is unchanged.
