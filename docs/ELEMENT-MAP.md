# Element map — where every CodeGuard & Foundry element lives

This is the learning index. Each row maps a concept from **Project CodeGuard**
or the **Foundry Security Spec** to the file (and function) in this repo that
exercises it. Read a spec section, then jump to the code that applies it.

Paths are relative to the repo root. Foundry refs are `spec.md` §/FR numbers and
`constitution.md` principles; CodeGuard refs are rule/tooling names.

---

## Foundry — the 8 core agent roles (spec §5)

| Role | Spec | Implementation |
|---|---|---|
| Orchestrator | §5.1 / FR-001–019 | `hello_spec/foundry/roles/orchestrator.py` (lifecycle, operator messages, override, status) |
| Indexer | §5.2 / FR-020–029 | `hello_spec/foundry/roles/indexer.py` (`ast` symbols, call graph, `resolves()`) |
| Cartographer | §5.3 / FR-030–036a | `hello_spec/foundry/roles/cartographer.py` (entry points, trust boundaries, data flows, threat model) |
| Detector | §5.4 / FR-037–049 | `hello_spec/foundry/roles/detector.py` (rule sweep, dep scan, secret scan, exploratory, rule-gap). The rule sweep is **LLM-evaluated** in `cli`/`api` (one model call per function, FR-037), deterministic matchers in `stub` (tests), with fallback to matchers on model error. |
| Triager | §5.5 / FR-050–059 | `hello_spec/foundry/roles/triager.py` (5 verdicts, evidence gate) |
| Validator | §5.6 / FR-060–066 | `hello_spec/foundry/roles/validator.py` (clean-room reproduction, sets `exploited`) |
| Coverage-Guide | §5.7 / FR-067–074 | `hello_spec/foundry/roles/coverage_guide.py` (checklist, coverage-complete) |
| Reporter | §5.8 / FR-075–084 | `hello_spec/foundry/roles/reporter.py` (severity rubric, per-finding report + rollup, only writer) |

## Foundry — extension roles (spec §6)

In `hello_spec/foundry/roles/extensions/`. The Self-Improver (§6.5) turns
rule-gap entries into proposed new rules. The **Remediator (§6.4)** is fully
implemented in `roles/extensions/remediator.py` (+ `foundry/remediation.py`): it
proposes a candidate fix per confirmed true-positive and **verifies** it against
an isolated copy before labelling it `verified` — see
[`specs/001-remediator-role/`](../specs/001-remediator-role/) for its
spec/plan/tasks. Deep-Tester, Variant-Hunter and Attack-Mapper remain stubs.

## Foundry — finding lifecycle (spec §7)

| Element | Spec | Implementation |
|---|---|---|
| States | §7.1 | `lifecycle/models.py::FindingState` |
| Verdicts (5) | §7.2 / FR-050 | `lifecycle/models.py::Verdict` |
| Evidence gate | §7.3 / FR-087–088 | `lifecycle/evidence_gate.py::apply_gate` |
| Exploited flag | §7.4 / FR-089 | `roles/validator.py` (set only here) |
| Fingerprint | §7.5 / FR-090 | `lifecycle/fingerprint.py::fingerprint` |
| Label taxonomy | §7.6 / FR-092–093 | `lifecycle/labels.py` |

## Foundry — coordination substrate (spec §8)

| Element | Spec | Implementation |
|---|---|---|
| Work queue (atomic claim, auto-block) | §8.1 / FR-094–099 | `substrate/work_queue.py` |
| Heartbeat liveness | §8.2 / FR-100–101 | `substrate/liveness.py` |
| Operator/peer messages | §8.3 / FR-102–103 | `roles/orchestrator.py` (dedup, kinds) |
| Shared notes (no "done") | §8.4 / FR-104 | `substrate/notes.py` |
| Rate governance | §8.5 / FR-105–106 | `governance/budget.py` (`note_rate_limit`/`note_success`) |
| Atomic persistence | §8.6 / FR-106a | `substrate/persistence.py` |
| Finding store / dedup | §5.4, §7 | `substrate/finding_store.py` |

## Foundry — governance & safety (spec §9–10, §13)

| Element | Spec | Implementation |
|---|---|---|
| Sandbox | §9.1 / FR-107–109 | `governance/sandbox.py` (egress allowlist, read-only mounts) |
| Scope / hard rules | §9.2 / FR-110–111 | `governance/scope_rules.py` |
| Budget | §9.3 / FR-112–114 | `governance/budget.py` |
| Yield auto-stop | §9.4 / FR-115–117 | `governance/yield_stop.py` |
| Session lifecycle limits | §9.5 / FR-118–119a | `governance/agent_lifecycle.py` |
| Dashboard | §10 / FR-120,124–125 | `observability/dashboard.py` |
| Activity feed | §10 / FR-121 | `observability/activity_feed.py` |
| Session logs / auditability | §10 / FR-122–123, NFR-007 | `observability/session_log.py` |
| Idempotency (NFR-002) | §13 | `substrate/finding_store.py` + `tests/test_idempotency.py` |
| Determinism without a model (NFR-004) | §13 | `llm/adapter.py` stub backend |

## Foundry — integration surfaces & config (spec §11–12)

| Element | Spec | Implementation |
|---|---|---|
| LLM provider (+ tiering hook) | §11.2 | `llm/adapter.py` (stub / cli / api toggle) |
| Issue tracker binding | §11.1 | `integrations/issue_tracker.py` (filesystem) |
| Severity & classification | §11.9 | `roles/reporter.py::SEVERITY_RUBRIC` |
| Configuration model (all sections) | §12 / FR-126–129 | `config/evaluation.yaml`, `foundry/config.py` |
| Secret separation | FR-127 | `config/secrets.env.example`, `config.py::_reject_inline_secrets` |

## Foundry — the 11 constitutional principles

Each is enforced in code and asserted in `tests/test_principles.py`:

| # | Principle | Enforced by |
|---|---|---|
| I | Evidence Over Assertion | `lifecycle/evidence_gate.py` |
| II | Surface Only What Survives | `substrate/finding_store.py::surfaced` |
| III | Liveness By Heartbeat | `substrate/liveness.py` |
| IV | Claims Are Atomic And Mortal | `substrate/work_queue.py` |
| V | The Provider Is The Rate Arbiter | `governance/budget.py` |
| VI | Coverage Before Yield | `governance/yield_stop.py::should_stop` |
| VII | Exploited Means Demonstrated | `roles/validator.py` |
| VIII | Fingerprints Are Stable Under Edit | `lifecycle/fingerprint.py` |
| IX | Sandbox By Infrastructure | `governance/sandbox.py` |
| X | The Operator Outranks Every Agent | `roles/orchestrator.py`, `substrate/notes.py` |
| XI | Persist Atomically | `substrate/persistence.py` |

---

## Project CodeGuard

| Element | CodeGuard ref | Where it is exercised |
|---|---|---|
| Rule format (frontmatter: description/languages/tags/alwaysApply) | `sources/rules/core/*` | `rules/codeguard-*.md` (5 authored rules) |
| Always-apply tier (`alwaysApply: true`, no languages) | tier `codeguard-1-*` | `rules/codeguard-1-hellospec-hardcoded-credentials.md` |
| Glob-scoped tier (languages set) | tier `codeguard-0-*` | the four `codeguard-0-hellospec-*.md` rules |
| Known tags constraint | `src/tag_mappings.py::KNOWN_TAGS` | tags used: `secrets`, `web` |
| Language→glob mapping | `src/language_mappings.py` | `languages: [python]` |
| Rule validation | `src/validate_unified_rules.py` | `scripts/build_rules.sh` step 2 |
| IDE/agent format conversion (Cursor, Windsurf, Copilot, Codex, OpenCode, OpenClaw, Hermes, Claude, Antigravity) | `src/convert_to_ide_formats.py` | `scripts/build_rules.sh` step 3 → `build/codeguard-bundles/` |
| Custom-rule source workflow | `docs/custom-rules.md` | staging into `sources/rules/hellospec/` |
| Detection rule consumed by Foundry | `example-detection-rule.md` | `## Detector contract` parsed by `foundry/detection_rules.py` |
| Secure-by-default controls applied | core rule guidance | `target/secure/app.py` (parameterized SQL, argv subprocess, ownership check, env secret, constant-time compare) |

## The bridge: CodeGuard rule → Foundry finding

`docs/worked-examples/example-detection-rule.md` in the spec says CodeGuard is
"the format the seed assumes". Here that is literal:

1. A rule in `rules/` carries CodeGuard frontmatter **and** a `## Detector
   contract` block (`id`, `severity`, `weakness_class`, `matcher`).
2. `foundry/detection_rules.py` loads both; `foundry/roles/detector.py` applies
   the matcher function-by-function (FR-037).
3. The finding flows: candidate → Triager verdict + evidence gate → Validator
   `exploited` → Reporter issue, deduped by fingerprint.
4. When exploration finds a class no rule covers (CWE-208 here), a rule-gap is
   recorded (FR-042) and the Self-Improver proposes a new rule — the flywheel.
