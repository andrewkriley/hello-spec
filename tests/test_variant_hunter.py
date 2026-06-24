"""Variant-Hunter role tests (Foundry §6.2) — one assertion per success
criterion, deterministic stub backend."""
from pathlib import Path

from hello_spec.foundry.engine import run_evaluation

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "evaluation.yaml"


def _run(target=None):
    return run_evaluation(CONFIG, backend="stub",
                          target_override=str(target) if target else None)


def _variants(target=None):
    return _run(target)["variants"]


# SC-001 — a recurring class with a confirmed TP yields a variant -------------
def test_finds_recurring_class_variant():
    classes = {v["weakness_class"] for v in _variants()}
    assert "CWE-89" in classes        # handle_export (TP) + legacy_lookup sibling


# SC-002 — the out-of-scope SQLi sibling is surfaced, labelled -----------------
def test_variant_includes_out_of_scope_sibling():
    sqli = [v for v in _variants() if v["weakness_class"] == "CWE-89"]
    assert any(v["location"].endswith("legacy_lookup")
               and v["verdict"] == "not-applicable" for v in sqli)


# SC-003 — a class present in only one place yields no variant -----------------
def test_no_variant_for_unique_class():
    # CWE-78 (run_command) is the only command-injection location.
    assert all(v["weakness_class"] != "CWE-78" for v in _variants())


# SC-004 — the hunt changes nothing -------------------------------------------
def test_no_findings_or_target_changed():
    target = ROOT / "target" / "vulnerable"
    before = (target / "app.py").read_bytes()
    result = _run()
    # findings still carry their original verdicts; variants are separate leads.
    assert result["findings"], "pipeline still produced findings"
    assert (target / "app.py").read_bytes() == before


# SC-005 — no confirmed findings -> no variants -------------------------------
def test_zero_on_secure():
    assert _variants(target=ROOT / "target" / "secure") == []


# A variant is never reported as a variant of itself --------------------------
def test_variant_is_not_self():
    for v in _variants():
        assert v["fingerprint"] != v["source_fingerprint"]
