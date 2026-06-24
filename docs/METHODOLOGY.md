# How Foundry, spec-kit, and CodeGuard fit together

This project combines three open pieces. They are not interchangeable and they
sit in a specific order. This page is the canonical mental model — read it before
`README.md`'s feature tour.

## The three layers

| Layer | What it is | Role here |
|---|---|---|
| **Foundry Security Spec** | The **WHAT** — a seed `spec.md` + an 11-principle `constitution.md` describing a trustworthy AI vulnerability-discovery system. | The blueprint we implement, and the constitution that governs every plan/task. |
| **spec-kit** | The **HOW** — a spec-driven workflow (`/speckit-*`: clarify → specify → plan → tasks → implement → analyze). | The process that turns the Foundry seed into our implementation. |
| **Project CodeGuard** | Secure-coding **rules** + tooling. | Wears **two hats** (below). |

## The canonical order

Straight from Foundry's own README (steps 0–7) and CodeGuard's README:

```
 Foundry spec.md + constitution.md          (the WHAT + the invariants)
            │   consumed by
            ▼
 spec-kit:  clarify → specify → plan → tasks → implement
            │   governed against → the FOUNDRY CONSTITUTION  (Gate A)
            │   steered & reviewed by → CODEGUARD             (Gate B)
            ▼
 a working system  ── whose Detector ALSO consumes CodeGuard rules at runtime
```

So: **spec-kit comes first, driven by Foundry. CodeGuard reviews the plan and the
implementation.** That matches the intuition that prompted this doc — with one
important correction below.

## CodeGuard's two hats

CodeGuard is easy to mis-file as "just the rules the scanner uses." It is two
distinct things:

1. **Hat 1 — secure-coding overlay (a process gate).** CodeGuard's README says to
   use it *"before code generation… in the planning phase and for spec-driven
   development,"* *during* generation, and *after* (code review). So CodeGuard
   **steers the plan** toward secure patterns and **reviews the implementation**
   before merge. This is a gate on *the code we write*.
2. **Hat 2 — the Detector's rule corpus (a product feature).** Inside the Foundry
   system we build, the Detector evaluates a corpus of CodeGuard-format rules
   (`spec.md` §5.4 / FR-037). This is a *runtime input*, configured in the
   evaluation's `detection` section — not a process step.

In this repo: Hat 2 lives in `rules/` (consumed by `hello_spec/foundry/roles/
detector.py`) and the applied controls in `target/secure/`. Hat 1 is the gate
described next.

## Two gates, not one

The spec-kit loop is checked against **two independent gates**. Don't conflate
them:

| | Gate A — Foundry constitution | Gate B — CodeGuard security |
|---|---|---|
| Checks | architectural **invariants** (evidence over assertion, atomic claims, sandbox-by-infra, …) | **secure-coding** practices (no hardcoded secrets, input validation, safe file/subprocess handling, …) |
| Lives in | `.specify/memory/constitution.md`; enforced by the "Constitution Check" in `.specify/templates/plan-template.md` and `/speckit-analyze` | `.specify/templates/plan-template.md` "CodeGuard Security Check"; a CodeGuard review of the diff before merge |
| Applies to | the **design** | the **code** |

Both run during `/speckit-plan` and before `/speckit-implement` completes.

## The per-feature workflow (what to actually do)

1. `/speckit-specify` (+ `/speckit-clarify`) — the spec, Foundry-aligned.
2. `/speckit-plan` — design. The plan template now carries **both** gates:
   *Constitution Check* (Gate A) and *CodeGuard Security Check* (Gate B).
3. `/speckit-tasks` → `/speckit-implement` — build, steered secure-by-default by
   CodeGuard (Hat 1, planning/generation phase).
4. **Before merge:** run a CodeGuard review of the diff (CodeGuard's
   `security-review` skill / `codeguard-reviewer` agent, mirrored in
   `project-codeguard/sources/`). Record the result. See `docs/security-review.md`
   for the worked review of this engine.
5. `/speckit-analyze` — cross-artifact consistency vs the constitution.

## Honest history (why the repo doesn't *look* like this order)

This repo was built engine-first, then made disciplined. The order above is what
we'd do from scratch; the commit history shows the retrofit:

| PR | What | Followed the canonical order? |
|---|---|---|
| #1 | the engine + CodeGuard rules | no — built first |
| #2 | live `claude -p` triager | no |
| #3 | spec-kit + Foundry constitution adopted | — (this *introduced* the workflow) |
| #4 | Remediator role | **yes** — full spec-kit flow (Gate A) |
| #8 | Variant-Hunter role | **yes** — full spec-kit flow (Gate A) |
| this | methodology + **Gate B** (CodeGuard) added; engine reviewed | closes the gap |

From here, every feature goes spec-kit-first through **both** gates.
