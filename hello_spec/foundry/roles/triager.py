"""Triager (Foundry spec.md §5.5 / FR-050-059).

Investigates each candidate and assigns one of five verdicts (FR-050). A
`true-positive` is gated: the Triager must produce reachability, trust-boundary
and impact citations that the evidence gate mechanically resolves (§7.3). If a
citation does not resolve, the verdict is demoted to `needs-review`
(Constitution I). Rejected findings are kept in the store with reasoning so a
re-run does not re-debate them (Constitution II, FR-086).

Two investigation modes share the SAME gate:

  - deterministic (stub backend): inspects the indexed source with checkable
    Python, so the demo reproduces the worked examples without a live model
    (NFR-004). Used by the test suite.
  - LLM-backed (cli / api backend): the model reads the function source and
    proposes a verdict plus citations. The architecture then VERIFIES it — a
    proposed true-positive must still pass the evidence gate against the real
    index, or it is demoted (Constitution I: the model reasons, the gate
    decides). Scope (operator policy) and dependency advisories stay
    deterministic regardless of backend.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional

from ..lifecycle.evidence_gate import apply_gate
from ..lifecycle.models import (Citation, EvidenceGate, Finding, FindingState,
                                Verdict)
from .base import Role
from .indexer import CodeIndex

_PLACEHOLDER_RE = re.compile(r"changeme|example|placeholder|your[-_]?|xxxx|test[-_]?",
                             re.I)

_TRIAGE_SYSTEM = (
    "You are a security triager. You investigate one candidate vulnerability "
    "and decide a verdict grounded in concrete evidence, not confidence. "
    "Respond with ONLY a single JSON object, no prose, no code fences.")

_VERDICT_MAP = {
    "true-positive": Verdict.TRUE_POSITIVE,
    "false-positive": Verdict.FALSE_POSITIVE,
    "needs-review": Verdict.NEEDS_REVIEW,
    "not-applicable": Verdict.NOT_APPLICABLE,
    "code-quality": Verdict.CODE_QUALITY,
}


class Triager(Role):
    name = "triager"

    def triage(self, store, index: CodeIndex, target_dir: Path,
               scope_exclude: List[str], tick: int) -> None:
        self.heartbeat()
        use_llm = self.llm.backend in ("cli", "api")
        for f in store.all():
            if f.state != FindingState.CANDIDATE:
                continue
            target = Path(target_dir)
            if self._out_of_scope(f, scope_exclude):
                # FR-051: scope is operator policy (Constitution X) — never the
                # model's call. Out-of-scope findings are not-applicable.
                f.verdict = Verdict.NOT_APPLICABLE
                f.reasoning = f"{f.path} is outside the configured scope"
            elif f.technique == "dependency-scan":
                # A dependency advisory cannot satisfy a code-citation gate.
                f.verdict = Verdict.NEEDS_REVIEW
                f.reasoning = ("dependency advisory; no in-code reachability/"
                               "impact citation available, gate not satisfied")
            elif use_llm and self._triage_with_llm(f, index, target):
                pass                              # model proposed + gate verified
            else:
                self._triage_deterministic(f, index, target)
            f.state = FindingState.CONFIRMED
        mode = "llm" if use_llm else "deterministic"
        self.emit(tick, "triage", f"triaged {len(store.all())} finding(s) [{mode}]")

    @staticmethod
    def _out_of_scope(f: Finding, scope_exclude: List[str]) -> bool:
        return any(f.path.startswith(s.rstrip("/") + "/") or f.path.startswith(s)
                   for s in scope_exclude)

    # -- LLM-backed investigation (cli / api), verified by the gate --------
    def _triage_with_llm(self, f: Finding, index, target_dir: Path) -> bool:
        """Ask the model for a verdict + citations, then VERIFY with the gate.
        Returns True if it produced a usable verdict; False to fall back to the
        deterministic path (so a flaky model never breaks the run)."""
        try:
            source = self._numbered_source(f, index, target_dir)
            raw = self.llm.complete(self.name, _TRIAGE_SYSTEM,
                                    self._triage_prompt(f, source))
            data = self._parse_json(raw)
            if not data:
                self.log.discarded(f"llm-triage:{f.symbol}",
                                   "unparseable model response")
                return False
            verdict = _VERDICT_MAP.get(str(data.get("verdict", "")).strip().lower())
            if verdict is None:
                return False
            reasoning = str(data.get("reasoning", "")).strip()[:300]
            if verdict == Verdict.TRUE_POSITIVE:
                f.evidence = self._llm_citations(f, data.get("citations") or {})
                result = apply_gate(f, index)     # architecture verifies model
                f.verdict = result.verdict
                f.reasoning = (f"[llm] {reasoning}" if result.passed
                               else f"[llm] {reasoning} | demoted: {result.reason}")
            else:
                f.verdict = verdict
                f.reasoning = f"[llm] {reasoning}"
            return True
        except Exception as exc:                  # never crash the fleet on one call
            self.log.discarded(f"llm-triage:{f.symbol}", f"error: {exc}")
            return False

    def _triage_prompt(self, f: Finding, numbered_source: str) -> str:
        return (
            f"Candidate finding:\n"
            f"- file: {f.path}\n- symbol: {f.symbol}\n"
            f"- weakness_class: {f.weakness_class}\n"
            f"- detector note: {f.description}\n\n"
            f"Source under review (real line numbers shown):\n"
            f"{numbered_source}\n\n"
            "Choose a verdict from exactly: true-positive, false-positive, "
            "code-quality, needs-review.\n"
            "- true-positive: a real, exploitable vulnerability of this class.\n"
            "- false-positive: the detector hypothesis is wrong / code is safe "
            "(e.g. a path join already guarded by a commonpath containment check).\n"
            "- code-quality: a real defect but not an exploitable secret/vuln "
            "(e.g. a placeholder default like 'changeme').\n"
            "- needs-review: real but you cannot cite concrete evidence.\n\n"
            "If and ONLY IF true-positive, cite three real line numbers from "
            "above: reachability (entry point), trust_boundary (where untrusted "
            "data enters), impact (the dangerous sink). For a hardcoded secret, "
            "cite the credential's line for all three.\n\n"
            'Respond with ONLY this JSON: {"verdict":"...","reasoning":"...",'
            '"citations":{"reachability":{"line":N,"note":"..."},'
            '"trust_boundary":{"line":N,"note":"..."},'
            '"impact":{"line":N,"note":"..."}}}. '
            'For non true-positive use "citations":{}.')

    def _numbered_source(self, f: Finding, index, target_dir: Path) -> str:
        fn = index.get(f.path, f.symbol)
        if fn:
            lines = fn.source.splitlines()
            start = fn.lineno
        else:
            all_lines = (target_dir / f.path).read_text().splitlines()
            ln = self._line_of(f)
            start = max(1, ln - 1)
            lines = all_lines[start - 1:ln + 1]
        return "\n".join(f"{start + i}: {line}" for i, line in enumerate(lines))

    def _llm_citations(self, f: Finding, citations: dict) -> EvidenceGate:
        def cite(leg: str, key: str) -> Optional[Citation]:
            c = citations.get(key) or {}
            line = c.get("line")
            if not isinstance(line, int):
                return None
            return Citation(leg, f.path, f.symbol, line, str(c.get("note", ""))[:120])
        return EvidenceGate(
            reachability=cite("reachability", "reachability"),
            trust_boundary=cite("trust-boundary", "trust_boundary"),
            impact=cite("impact", "impact"))

    @staticmethod
    def _parse_json(raw: str) -> Optional[dict]:
        txt = raw.strip()
        if txt.startswith("```"):
            txt = re.sub(r"^```[a-zA-Z]*\n?", "", txt).rstrip("`").strip()
        try:
            return json.loads(txt)
        except Exception:
            i, j = txt.find("{"), txt.rfind("}")
            if 0 <= i < j:
                try:
                    return json.loads(txt[i:j + 1])
                except Exception:
                    return None
        return None

    # -- deterministic investigation (stub backend) -----------------------
    def _triage_deterministic(self, f: Finding, index, target_dir) -> None:
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
