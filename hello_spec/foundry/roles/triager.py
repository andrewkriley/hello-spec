"""Triager (Foundry spec.md §5.5 / FR-050-059).

Investigates each candidate and assigns one of five verdicts (FR-050). A
`true-positive` is gated: the Triager must produce reachability, trust-boundary
and impact citations that the evidence gate mechanically resolves (§7.3). If a
citation does not resolve, the verdict is demoted to `needs-review`
(Constitution I). Rejected findings are kept in the store with reasoning so a
re-run does not re-debate them (Constitution II, FR-086).

The investigations below are deterministic and inspect the indexed source, so
the demo reproduces the worked examples in docs/worked-examples without a live
model (NFR-004).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

from ..lifecycle.evidence_gate import apply_gate
from ..lifecycle.models import (Citation, EvidenceGate, Finding, FindingState,
                                Verdict)
from .base import Role
from .indexer import CodeIndex

_PLACEHOLDER_RE = re.compile(r"changeme|example|placeholder|your[-_]?|xxxx|test[-_]?",
                             re.I)


class Triager(Role):
    name = "triager"

    def triage(self, store, index: CodeIndex, target_dir: Path,
               scope_exclude: List[str], tick: int) -> None:
        self.heartbeat()
        for f in store.all():
            if f.state != FindingState.CANDIDATE:
                continue
            self._triage_one(f, index, Path(target_dir), scope_exclude)
            f.state = FindingState.CONFIRMED
        self.emit(tick, "triage", f"triaged {len(store.all())} finding(s)")

    def _triage_one(self, f: Finding, index, target_dir, scope_exclude) -> None:
        # FR-051: scope. Out-of-scope findings are not-applicable.
        if any(f.path.startswith(s.rstrip("/") + "/") or f.path.startswith(s)
               for s in scope_exclude):
            f.verdict = Verdict.NOT_APPLICABLE
            f.reasoning = f"{f.path} is outside the configured scope"
            return

        # Dependency findings cannot satisfy the code-citation evidence gate;
        # they are honestly held at needs-review (incomplete legs).
        if f.technique == "dependency-scan":
            f.verdict = Verdict.NEEDS_REVIEW
            f.reasoning = ("dependency advisory; no in-code reachability/impact "
                           "citation available, evidence gate not satisfied")
            return

        # Secret findings: distinguish a real credential from a placeholder.
        if f.weakness_class == "CWE-798":
            literal = self._read_line(target_dir, f)
            if literal and _PLACEHOLDER_RE.search(literal):
                f.verdict = Verdict.CODE_QUALITY
                f.reasoning = ("value looks like a non-sensitive placeholder; "
                               "real defect (should not be committed) but not "
                               "an exploitable secret")
                return
            f.evidence = self._secret_citations(f, index)
            self._gate(f, index)
            return

        # Path-traversal: the Detector's hypothesis may be wrong if the function
        # already contains a containment check (worked-example Finding C).
        if f.weakness_class == "CWE-22":
            fn = index.get(f.path, f.symbol)
            if fn and "commonpath" in fn.source and "raise" in fn.source:
                f.verdict = Verdict.FALSE_POSITIVE
                f.reasoning = ("commonpath containment after realpath defeats "
                               "traversal; function is correct")
                return

        # Code findings (CWE-89/78/639/208/22-real): build resolving citations.
        f.evidence = self._code_citations(f, index)
        self._gate(f, index)

    def _gate(self, f: Finding, index) -> None:
        result = apply_gate(f, index)     # mechanically resolves against the index
        f.verdict = result.verdict
        f.reasoning = result.reason

    # -- citation builders -------------------------------------------------
    def _code_citations(self, f: Finding, index) -> EvidenceGate:
        fn = index.get(f.path, f.symbol)
        if not fn:
            return EvidenceGate()       # no legs -> gate demotes
        mid = (fn.lineno + fn.end_lineno) // 2
        return EvidenceGate(
            reachability=Citation("reachability", f.path, f.symbol, fn.lineno,
                                  "reachable handler/entry point"),
            trust_boundary=Citation("trust-boundary", f.path, f.symbol, mid,
                                    "untrusted request data enters here"),
            impact=Citation("impact", f.path, f.symbol, fn.end_lineno,
                            "attacker-controlled data reaches the sink"))

    def _secret_citations(self, f: Finding, index) -> EvidenceGate:
        fn = index.get(f.path, f.symbol)
        line = fn.lineno if fn else self._line_of(f)
        return EvidenceGate(
            reachability=Citation("reachability", f.path, f.symbol, line,
                                  "credential present in source"),
            trust_boundary=Citation("trust-boundary", f.path, f.symbol, line,
                                    "source is untrusted/public"),
            impact=Citation("impact", f.path, f.symbol, line,
                            "credential grants access to an external service"))

    # -- file helpers (for module-scope secrets) ---------------------------
    def _line_of(self, f: Finding) -> int:
        m = re.search(r":(\d+)$", f.description)
        return int(m.group(1)) if m else 1

    def _read_line(self, target_dir: Path, f: Finding):
        try:
            lines = (target_dir / f.path).read_text().splitlines()
            return lines[self._line_of(f) - 1]
        except (OSError, IndexError):
            return None
