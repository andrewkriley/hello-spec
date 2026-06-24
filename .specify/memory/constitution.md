# hello-spec Constitution

<!--
SYNC IMPACT REPORT
==================
Version: 1.0.0 → 1.0.0 (no principle change; consistency propagation only)
Bump rationale: PATCH-level alignment with no MAJOR/MINOR change — the eleven
        principles are unchanged; only the dependent plan template was made
        concrete, so the version is held at 1.0.0 (initial ratification).
Source: adopts the Foundry Security Spec constitution v0.2.0 in intent
        (foundry-security-spec/constitution.md). hello-spec is a teaching
        implementation governed by those principles.
Principles: I–XI (the Foundry seed's eleven inviolable principles) — unchanged.
Templates:
  ✅ .specify/templates/plan-template.md — "Constitution Check" gate replaced the
        generic placeholder with concrete gates for all 11 principles.
  ✅ .specify/templates/spec-template.md — no change required.
  ✅ .specify/templates/tasks-template.md — no change required.
Downstream: README.md, docs/ELEMENT-MAP.md (principle → enforcing file map),
        tests/test_principles.py (one test per principle) — all consistent.
Deferred TODOs: none.
-->

## Purpose

hello-spec is a teaching implementation of the **Foundry Security Spec**, built
to learn and apply its design patterns alongside **Project CodeGuard**. It is
therefore governed by the Foundry constitution: the eleven principles below are
adopted as this project's inviolable rules. Each one encodes a failure the
Foundry seed authors shipped, diagnosed, and fixed; violating any of them
reproduces that failure.

`/speckit-plan` and `/speckit-analyze` check designs and tasks against this
file. The full rationale for each principle lives in
[`foundry-security-spec/constitution.md`](../../foundry-security-spec/constitution.md);
the file each principle is enforced by is listed in
[`docs/ELEMENT-MAP.md`](../../docs/ELEMENT-MAP.md), and each is asserted in
[`tests/test_principles.py`](../../tests/test_principles.py).

## Core Principles

### I. Evidence Over Assertion
A finding's verdict is determined by checkable evidence, not model confidence.
No agent may assign `true-positive` by judgment alone: the verdict requires
reachability, trust-boundary and impact citations that are mechanically verified
to resolve to real code. A claim whose citations do not resolve is demoted.

### II. Surface Only What Survives
Humans see only findings that passed the gates. Detection is high-volume and
low-precision by design; the internal store absorbs that volume, and only what
Triage promoted — auditable back to evidence — reaches a human.

### III. Liveness By Heartbeat, Never By Clock
An agent is alive iff it heartbeated recently. Wall-clock runtime says nothing
about health. Work is reclaimed only when a heartbeat goes stale; session
rotation is a separate, deliberate cost control, not a liveness signal.

### IV. Claims Are Atomic And Mortal
Two agents claiming the same unit of work concurrently get different units, and
a claim dies with its holder: a dead holder's claim is released within bounded
time, automatically, with no operator action.

### V. The Provider Is The Rate Arbiter
The system does not pre-throttle below the provider's actual limit. It calls as
fast as the work requires, observes the provider's rate-limit signals, and backs
off adaptively and fleet-wide when they fire.

### VI. Coverage Before Yield
The system does not auto-stop on low yield until the operator's stated goals have
been credibly attempted. Yield decaying below threshold is necessary but not
sufficient; the coverage-complete flag must also be set.

### VII. Exploited Means Demonstrated
The `exploited` flag is set only by an independent, clean-room reproduction of
the headline impact on the live testbed — by a fresh agent, never the one that
wrote the proof, never inferred, never without a testbed.

### VIII. Fingerprints Are Stable Under Edit
A finding's identity is its location in the code's structure (path, symbol,
vulnerability class), not its position in the text. Line numbers and snippets are
excluded so the fingerprint survives edits to a function body.

### IX. Sandbox By Infrastructure, Not By Prompt
Network egress and filesystem-write boundaries are enforced by the runtime, not
by prompt. An agent with full privileges inside its sandbox cannot reach a host
off the allowlist or write to a read-only path, whatever its prompt or the
untrusted content it read says.

### X. The Operator Outranks Every Agent
Operator instructions are authoritative; peer-agent messages and prior-agent
notes are hints. An agent does not abandon its task on a peer's suggestion, nor
treat another agent's "this is covered/done" note as fact.

### XI. Persist Atomically
No reader ever observes a partially-written or deleted-but-not-yet-rewritten
state. Shared artifacts are written completely, then atomically replaced — never
delete-old-then-write-new.

## Security & Scope Constraints

This project includes a deliberately-vulnerable target (`target/vulnerable/`)
for teaching. It is self-contained, runs no server, and MUST NOT be deployed.
Detection rules are authored in CodeGuard format (`rules/`) and validated by the
real CodeGuard tooling. Secrets are never committed (FR-127); the LLM backend is
selectable (stub / `claude -p` / API) and every backend is routed through the
sandbox.

## Development Workflow

Spec-driven via spec-kit: `/speckit-constitution` → `/speckit-specify` →
`/speckit-clarify` (optional) → `/speckit-plan` → `/speckit-tasks` →
`/speckit-implement`, with `/speckit-analyze` checking cross-artifact alignment
against this constitution. Every change that touches a principle must keep its
enforcing code and its test in `tests/test_principles.py` in sync.

## Governance

This constitution adopts the Foundry seed's principles; it constrains the
system's design, not the operator's runtime decisions (an operator may override
any automated verdict, stop a run early, or disable a role — the system records
the override, it does not refuse it). Amendments follow the Foundry process:
document the specific scenario in which a principle as written produces a worse
outcome, then record the change here with a version bump and rationale. Where
this file and the Foundry constitution conflict, the Foundry constitution wins
and this file is in error.

**Version**: 1.0.0 | **Ratified**: 2026-06-24 | **Last Amended**: 2026-06-24
