"""Rule-gap flywheel tests (Foundry §6.5) — one assertion per success criterion,
deterministic stub backend."""
from pathlib import Path

from conftest import make_role

from hello_spec.foundry.detection_rules import _parse_frontmatter, load_rules
from hello_spec.foundry.engine import run_evaluation
from hello_spec.foundry.roles.detector import MATCHERS, _m_timing_unsafe_compare
from hello_spec.foundry.roles.indexer import Indexer

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "evaluation.yaml"
TARGET = ROOT / "target" / "vulnerable"
SECURE = ROOT / "target" / "secure"


def _run(target=None):
    return run_evaluation(CONFIG, backend="stub",
                          target_override=str(target) if target else None)


# Foundational — the promoted matcher is registered and discriminates -----------
def test_matcher_registered_and_fires(harness):
    assert "timing_unsafe_compare" in MATCHERS
    vuln = make_role(Indexer, harness, "ix").build(TARGET, 1).get("app.py", "check_token")
    assert _m_timing_unsafe_compare(vuln)                 # vulnerable == compare
    safe = make_role(Indexer, harness, "ix2").build(SECURE, 1).get("app.py", "check_token")
    assert _m_timing_unsafe_compare(safe) is None         # uses compare_digest


# SC-001 — a CWE-208 gap yields a valid, parseable CodeGuard rule ---------------
def test_self_improver_authors_valid_rule():
    proposals = _run()["rule_proposals"]
    cwe208 = [p for p in proposals if p["weakness_class"] == "CWE-208"]
    assert cwe208, "expected an authored rule for the CWE-208 gap"
    p = cwe208[0]
    assert p["matcher"] == "timing_unsafe_compare"
    # The authored file parses as a CodeGuard rule and loads via our loader.
    text = Path(p["path"]).read_text()
    fm, _ = _parse_frontmatter(text)
    assert fm.get("tags") == ["secrets"] and fm.get("languages") == ["python"]
    rules = load_rules(Path(p["path"]).parent)
    assert any(r.weakness_class == "CWE-208" and r.matcher == "timing_unsafe_compare"
               for r in rules)


# SC-002 — the authored rule, added to the corpus, catches the class ------------
def test_proposed_rule_closes_the_gap():
    cwe208 = [p for p in _run()["rule_proposals"] if p["weakness_class"] == "CWE-208"]
    assert cwe208 and cwe208[0]["verified"] is True       # re-scan caught it by rule


# SC-003 — the committed corpus is never modified -------------------------------
def test_rules_corpus_unchanged():
    rules_dir = ROOT / "rules"
    before = {p.name: p.read_bytes() for p in rules_dir.glob("codeguard-*.md")}
    _run()
    after = {p.name: p.read_bytes() for p in rules_dir.glob("codeguard-*.md")}
    assert before == after                                # no new/changed rule files


# SC-004 — no rule-gaps -> no proposals ----------------------------------------
def test_no_proposal_on_secure():
    assert _run(target=SECURE)["rule_proposals"] == []
