"""One test per Foundry constitutional principle (constitution.md I–XI).

Each asserts the structural behaviour the principle requires — the same failure
modes the seed authors documented.
"""
from pathlib import Path

import pytest
from conftest import make_role

from hello_spec.foundry.governance.budget import Budget
from hello_spec.foundry.governance.sandbox import Sandbox, SandboxViolation
from hello_spec.foundry.governance.yield_stop import YieldGovernor
from hello_spec.foundry.lifecycle.evidence_gate import apply_gate
from hello_spec.foundry.lifecycle.fingerprint import fingerprint
from hello_spec.foundry.lifecycle.models import (Citation, EvidenceGate,
                                                 Finding, FindingState,
                                                 Severity, Verdict)
from hello_spec.foundry.roles.orchestrator import Orchestrator
from hello_spec.foundry.roles.validator import Validator
from hello_spec.foundry.substrate.finding_store import FindingStore
from hello_spec.foundry.substrate.liveness import LivenessRegistry
from hello_spec.foundry.substrate.notes import NotesRejected, SharedNotes
from hello_spec.foundry.substrate.persistence import atomic_write_text
from hello_spec.foundry.substrate.work_queue import Task, TaskState, WorkQueue


class _Idx:
    def resolves(self, file, symbol, line):
        return line >= 1


def _tp_finding():
    f = Finding(path="a.py", symbol="h", weakness_class="CWE-89", title="t",
                description="d", technique="rule")
    f.evidence = EvidenceGate(
        reachability=Citation("reachability", "a.py", "h", 1, ""),
        trust_boundary=Citation("trust-boundary", "a.py", "h", 1, ""),
        impact=Citation("impact", "a.py", "h", 1, ""))
    return f


# I. Evidence Over Assertion -------------------------------------------------
def test_i_unresolved_citation_is_demoted():
    class BadIdx:
        def resolves(self, *a):
            return False
    assert apply_gate(_tp_finding(), BadIdx()).verdict == Verdict.NEEDS_REVIEW


# II. Surface Only What Survives --------------------------------------------
def test_ii_only_survivors_surface():
    store = FindingStore()
    survivor = _tp_finding()
    survivor.verdict = Verdict.TRUE_POSITIVE
    survivor.state = FindingState.PUBLISHED
    noise = Finding(path="b.py", symbol="x", weakness_class="CWE-1",
                    title="t", description="d", technique="rule")
    noise.verdict = Verdict.NEEDS_REVIEW
    store.upsert(survivor)
    store.upsert(noise)
    surfaced = store.surfaced()
    assert survivor in surfaced and noise not in surfaced


# III. Liveness By Heartbeat, Never By Clock --------------------------------
def test_iii_liveness_is_heartbeat_not_clock():
    live = LivenessRegistry(stale_after=2)
    live.heartbeat("a")
    live.tick(1)
    assert live.is_alive("a")          # recent heartbeat -> alive
    live.tick(5)                        # lots of wall-clock, no heartbeat
    assert not live.is_alive("a")       # stale heartbeat -> not alive
    live.heartbeat("a")
    assert live.is_alive("a")           # heartbeat revives regardless of runtime


# IV. Claims Are Atomic And Mortal ------------------------------------------
def test_iv_claims_atomic_and_mortal():
    live = LivenessRegistry(stale_after=1)
    q = WorkQueue(live)
    q.add(Task(id="t1", title="t1", description="", priority=1))
    q.add(Task(id="t2", title="t2", description="", priority=2))
    live.heartbeat("agentA")
    live.heartbeat("agentB")
    a = q.claim("agentA")
    b = q.claim("agentB")
    assert a.id != b.id                 # atomic: two claimers, different units
    live.tick(5)                        # agentA's heartbeat goes stale
    q.reclaim_stale()
    assert q._tasks[a.id].state == TaskState.OPEN   # mortal: claim released


# V. The Provider Is The Rate Arbiter ---------------------------------------
def test_v_provider_is_rate_arbiter():
    b = Budget()
    assert b.backoff_level == 0
    b.note_rate_limit()                 # provider pushed back -> back off
    assert b.backoff_level == 1
    b.note_success()                    # recovered -> ease off (adaptive)
    assert b.backoff_level == 0
    # No internal pre-throttle: with caps unset the budget never blocks a call.
    assert not Budget().exceeded()


# VI. Coverage Before Yield --------------------------------------------------
def test_vi_coverage_before_yield():
    gov = YieldGovernor(threshold=1.0, window=2, min_runtime=1)
    gov.sample(0.0, 1.0)
    gov.sample(0.0, 1.0)                 # low yield, window full
    assert not gov.should_stop(coverage_complete=False, runtime=10)
    assert gov.should_stop(coverage_complete=True, runtime=10)


# VII. Exploited Means Demonstrated -----------------------------------------
def test_vii_exploited_requires_validator_and_testbed(harness):
    validator = make_role(Validator, harness, "validator-1")
    store = FindingStore()
    f = _tp_finding()
    f.verdict = Verdict.TRUE_POSITIVE
    store.upsert(f)
    validator.validate(store, testbed=None, tick=1)
    assert f.exploited is False         # no testbed -> never exploited
    validator.validate(store, testbed={"reset": True}, tick=2)
    assert f.exploited is True          # validator + testbed reproduction


# VIII. Fingerprints Are Stable Under Edit ----------------------------------
def test_viii_fingerprint_stable_under_edit():
    # Same path/symbol/class, different line numbers -> identical fingerprint.
    assert fingerprint("a.py", "h", "CWE-89") == fingerprint("./a.py", "h", "cwe-89")
    # Different symbol -> different fingerprint.
    assert fingerprint("a.py", "h", "CWE-89") != fingerprint("a.py", "g", "CWE-89")


# IX. Sandbox By Infrastructure, Not By Prompt ------------------------------
def test_ix_sandbox_enforced(tmp_path):
    ro = tmp_path / "ro"
    ro.mkdir()
    sb = Sandbox(["api.anthropic.com"], writable_paths=[str(tmp_path / "out")],
                 readonly_paths=[str(ro)])
    with pytest.raises(SandboxViolation):
        sb.check_egress("evil.example.com")
    with pytest.raises(SandboxViolation):
        sb.check_write(str(ro / "x"))


# X. The Operator Outranks Every Agent --------------------------------------
def test_x_operator_outranks_agents(harness):
    orch = make_role(Orchestrator, harness, "orch-1")
    store = FindingStore()
    f = _tp_finding()
    f.verdict = Verdict.TRUE_POSITIVE
    store.upsert(f)
    orch.override_verdict(store, f.fingerprint, Verdict.FALSE_POSITIVE,
                          "operator reviewed", tick=1)
    assert f.verdict == Verdict.FALSE_POSITIVE
    assert orch.overrides                          # override recorded (NFR-009)
    # Agent notes may not assert coverage/done (agents talk each other out of work).
    with pytest.raises(NotesRejected):
        SharedNotes().append("agentA", "this area is fully covered, done")


# XI. Persist Atomically -----------------------------------------------------
def test_xi_persist_atomically(tmp_path):
    p = tmp_path / "artifact.json"
    atomic_write_text(p, "first-complete-state")
    atomic_write_text(p, "second-complete-state")
    assert p.read_text() == "second-complete-state"   # fully replaced
    # No partial temp files left behind by the write-then-swap.
    assert list(tmp_path.glob("*.tmp")) == []
