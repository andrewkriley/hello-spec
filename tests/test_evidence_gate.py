"""The evidence gate, reproducing docs/worked-examples/example-evidence-gate.md.

Finding A passes (all legs resolve); Finding B is demoted (a citation does not
resolve); an incomplete-legs finding is demoted too.
"""
from hello_spec.foundry.lifecycle.evidence_gate import apply_gate
from hello_spec.foundry.lifecycle.models import (Citation, EvidenceGate,
                                                 Finding, Verdict)


class FakeIndex:
    def __init__(self, spans):
        self.spans = spans       # (file, symbol) -> (lo, hi)

    def resolves(self, file, symbol, line):
        span = self.spans.get((file, symbol))
        return bool(span) and span[0] <= line <= span[1]


def _finding(ev):
    f = Finding(path="app/routes/admin.py", symbol="handle_export",
                weakness_class="CWE-89", title="SQLi", description="d",
                technique="rule:codeguard-py-sql-injection")
    f.evidence = ev
    return f


def test_finding_a_passes():
    idx = FakeIndex({("app/routes/admin.py", "handle_export"): (1, 5)})
    ev = EvidenceGate(
        reachability=Citation("reachability", "app/routes/admin.py",
                              "handle_export", 1, "route registered"),
        trust_boundary=Citation("trust-boundary", "app/routes/admin.py",
                                "handle_export", 2, "reads query string"),
        impact=Citation("impact", "app/routes/admin.py",
                        "handle_export", 3, "string-interpolated SQL"))
    result = apply_gate(_finding(ev), idx)
    assert result.passed
    assert result.verdict == Verdict.TRUE_POSITIVE


def test_finding_b_demoted_when_citation_does_not_resolve():
    # Reachability cites line 31, but the function span is only lines 1..5
    # (the real registration is elsewhere) — Principle I demotes it.
    idx = FakeIndex({("app/routes/admin.py", "handle_export"): (1, 5)})
    ev = EvidenceGate(
        reachability=Citation("reachability", "app/routes/admin.py",
                              "handle_export", 31, "WRONG line"),
        trust_boundary=Citation("trust-boundary", "app/routes/admin.py",
                                "handle_export", 2, "reads query string"),
        impact=Citation("impact", "app/routes/admin.py",
                        "handle_export", 3, "string-interpolated SQL"))
    result = apply_gate(_finding(ev), idx)
    assert not result.passed
    assert result.verdict == Verdict.NEEDS_REVIEW
    assert "reachability" in result.failed_legs


def test_incomplete_legs_demoted():
    idx = FakeIndex({("app/routes/admin.py", "handle_export"): (1, 5)})
    ev = EvidenceGate(
        reachability=Citation("reachability", "app/routes/admin.py",
                              "handle_export", 1, "only one leg"))
    result = apply_gate(_finding(ev), idx)
    assert result.verdict == Verdict.NEEDS_REVIEW
    assert {"trust-boundary", "impact"}.issubset(set(result.failed_legs))
