"""Attack-Mapper role tests (Foundry §6.3) — one assertion per success criterion,
deterministic stub backend."""
from pathlib import Path

from hello_spec.foundry.engine import run_evaluation

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "evaluation.yaml"


def _run(target=None):
    return run_evaluation(CONFIG, backend="stub",
                          target_override=str(target) if target else None)


def _paths(target=None):
    return _run(target)["attack_paths"]


# SC-001 — credential exposure chains to code execution ------------------------
def test_chains_credential_to_rce():
    paths = _paths()
    assert any(p["entry_class"] == "CWE-798" and p["impact_class"] == "CWE-78"
               for p in paths), "expected hardcoded-credential → command-injection path"
    # the narrative reads as a chain
    chain = next(p for p in paths
                 if p["entry_class"] == "CWE-798" and p["impact_class"] == "CWE-78")
    assert "→" not in chain["narrative"] and "then reach" in chain["narrative"]


# SC-002 — every path links two distinct confirmed true-positives --------------
def test_paths_link_distinct_true_positives():
    tp_fps = {f["fingerprint"] for f in _run()["findings"]
              if f["verdict"] == "true-positive"}
    for p in _paths():
        assert p["entry_fingerprint"] != p["impact_fingerprint"]
        assert {p["entry_fingerprint"], p["impact_fingerprint"]} <= tp_fps


# SC-003 — no foothold or no impact -> zero paths ------------------------------
def test_zero_on_secure():
    assert _paths(target=ROOT / "target" / "secure") == []


# SC-004 — the mapper changes nothing ------------------------------------------
def test_no_findings_or_target_changed():
    target = ROOT / "target" / "vulnerable"
    before = (target / "app.py").read_bytes()
    result = _run()
    assert result["findings"]
    assert (target / "app.py").read_bytes() == before
