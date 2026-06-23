"""The evidence gate (Foundry spec.md §7.3, Constitution I: Evidence Over
Assertion).

A finding may only be promoted to `true-positive` if it carries citations for
reachability, trust boundary, and impact, AND every citation mechanically
resolves to real code in the target. A confident argument with an
unresolvable citation is demoted to `needs-review` regardless of how fluent
the prose is. This is the structural defence against plausible fabrication.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .models import Finding, Verdict


@dataclass
class GateResult:
    passed: bool
    verdict: Verdict
    failed_legs: List[str]
    reason: str


def apply_gate(finding: Finding, index) -> GateResult:
    """FR-087/FR-088. Returns the verdict the gate permits.

    - Missing legs or unresolved citations -> demote to needs-review.
    - All three legs present and resolving  -> true-positive stands.
    """
    gate = finding.evidence
    if not gate.is_complete():
        present = [c.leg for c in gate.legs()]
        return GateResult(
            passed=False,
            verdict=Verdict.NEEDS_REVIEW,
            failed_legs=[leg for leg in ("reachability", "trust-boundary", "impact")
                         if leg not in present],
            reason="evidence gate incomplete: missing legs",
        )

    failed = gate.failed_legs(index)
    if failed:
        return GateResult(
            passed=False,
            verdict=Verdict.NEEDS_REVIEW,
            failed_legs=failed,
            reason="citation(s) did not resolve to real code: " + ", ".join(failed),
        )

    return GateResult(
        passed=True,
        verdict=Verdict.TRUE_POSITIVE,
        failed_legs=[],
        reason="all three legs resolve",
    )
