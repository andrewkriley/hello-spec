"""Deep-Tester role tests (Foundry §6.1) — one assertion per success criterion.

The corpus is fixed and the parser is pure, so the crash set is deterministic.
"""
from pathlib import Path

from conftest import make_role

from hello_spec.foundry.engine import run_evaluation
from hello_spec.foundry.governance.sandbox import Sandbox
from hello_spec.foundry.roles.extensions import DeepTester

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "evaluation.yaml"
VULN = ROOT / "target" / "vulnerable"
SECURE = ROOT / "target" / "secure"


def _deep_test(target=None):
    return run_evaluation(CONFIG, backend="stub",
                          target_override=str(target) if target else None)["deep_test"]


# SC-001 — the vulnerable parser crashes on generated input ---------------------
def test_finds_crash_inputs():
    crashes = _deep_test()
    types = {c["crash_type"] for c in crashes}
    assert types & {"IndexError", "ValueError"}, "expected crashes from fuzzing"
    for c in crashes:
        assert c["entry_point"].endswith("parse_record") and c["sample_input"] is not None


# SC-003 — distinct crash types are de-duplicated ------------------------------
def test_distinct_crash_types_deduped():
    crashes = _deep_test()
    types = [c["crash_type"] for c in crashes]
    assert len(types) == len(set(types))      # one entry per distinct crash type


# SC-002 — the validated parser yields no crashes ------------------------------
def test_secure_parser_no_crashes():
    assert _deep_test(target=SECURE) == []


# FR-006 — a target with no runnable entry point yields nothing -----------------
def test_no_parser_no_findings(harness, tmp_path):
    (tmp_path / "app.py").write_text("def f():\n    return 1\n")  # no parser.py
    dt = make_role(DeepTester, harness, "dt")
    sandbox = Sandbox(["localhost"], writable_paths=[str(tmp_path)], readonly_paths=[])
    assert dt.fuzz(tmp_path, sandbox, tmp_path, tick=1) == []


# SC-004 — fuzzing changes nothing in the target -------------------------------
def test_target_not_mutated():
    before = (VULN / "parser.py").read_bytes()
    _deep_test()
    assert (VULN / "parser.py").read_bytes() == before
