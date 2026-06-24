"""Remediator role tests (Foundry §6.4) — one assertion per success criterion.

All on the deterministic `stub` backend (NFR-004), so the verdicts are stable.
"""
from pathlib import Path

from conftest import make_role

from hello_spec.foundry.engine import run_evaluation
from hello_spec.foundry.governance.sandbox import Sandbox
from hello_spec.foundry.remediation import verify_candidate
from hello_spec.foundry.roles.detector import Detector
from hello_spec.foundry.roles.indexer import Indexer
from hello_spec.foundry.substrate.finding_store import FindingStore

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "evaluation.yaml"
TARGET = ROOT / "target" / "vulnerable"
RULES = ROOT / "rules"


def _run(target=None):
    return run_evaluation(CONFIG, backend="stub",
                          target_override=str(target) if target else None)


# US1 / SC-001 -----------------------------------------------------------------
def test_candidate_per_mapped_true_positive():
    verified = [c for c in _run()["remediations"] if c["status"] == "verified"]
    assert {c["weakness_class"] for c in verified} == {
        "CWE-89", "CWE-78", "CWE-639", "CWE-798"}
    assert len(verified) == 4


# US1 / FR-008 -----------------------------------------------------------------
def test_no_control_for_cwe208():
    nc = [c for c in _run()["remediations"] if c["status"] == "no-control"]
    assert any(c["weakness_class"] == "CWE-208" for c in nc)
    for c in nc:
        assert c["control"] == "none" and c["change"] == "" and c["reason"]


# US2 / SC-002 -----------------------------------------------------------------
def test_verified_candidates_have_passing_verification():
    for c in _run()["remediations"]:
        if c["status"] == "verified":
            v = c["verification"]
            assert v["passed"] and v["finding_closed"] and v["new_findings"] == 0


# US2 — a fix that does not close the finding must be unverified ----------------
def test_unverified_when_fix_does_not_close(harness, tmp_path):
    index = make_role(Indexer, harness, "ix").build(TARGET, 1)
    store = FindingStore()
    make_role(Detector, harness, "det").detect(index, TARGET, RULES, store, 1)
    sqli = next(f for f in store.all()
                if f.weakness_class == "CWE-89" and f.symbol == "handle_export")
    sandbox = Sandbox(["localhost"], writable_paths=[str(tmp_path)], readonly_paths=[])
    baseline = {f.fingerprint for f in store.all()}
    unchanged = (TARGET / sqli.path).read_text()      # a no-op "patch"
    deps = (harness["llm"], harness["feed"], harness["log"], harness["liveness"])
    vr = verify_candidate(sqli, TARGET, sqli.path, unchanged, RULES, sandbox,
                          tmp_path, baseline, deps)
    assert vr.finding_closed is False and vr.passed is False


# US3 / SC-003 -----------------------------------------------------------------
def test_target_not_mutated():
    before = (TARGET / "app.py").read_bytes()
    _run()
    assert (TARGET / "app.py").read_bytes() == before


# US3 / SC-005 -----------------------------------------------------------------
def test_zero_candidates_on_secure():
    assert _run(target=ROOT / "target" / "secure")["remediations"] == []


# US3 / SC-004 -----------------------------------------------------------------
def test_provenance_present():
    for c in _run()["remediations"]:
        assert c["finding_fingerprint"] and c["control"]
