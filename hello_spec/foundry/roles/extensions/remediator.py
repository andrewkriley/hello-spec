"""Remediator (Foundry spec.md §6.4) — candidate patch generation + verification.

For each confirmed true-positive whose class maps to a secure control, the
Remediator proposes a candidate fix and VERIFIES it against an isolated copy of
the target (the finding must close and nothing new may appear) before labelling
it `verified`. It never mutates the target and never auto-applies — candidates
are written, with provenance, for human review (Constitution X). Classes with no
mapped control are reported honestly as `no-control`, never force-patched.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

from ...lifecycle.models import (CandidateRemediation, RemediationStatus,
                                 Verdict)
from ...remediation import (apply_control, control_for, secure_symbol_source,
                            verify_candidate)
from ...substrate.persistence import atomic_write_json
from ..base import Role
from ..indexer import CodeIndex, Indexer


class Remediator(Role):
    name = "remediator"

    def remediate(self, store, index: CodeIndex, target_dir: Path, rules_dir: Path,
                  sandbox, reports_dir: Path, secure_dir: Path,
                  tick: int) -> List[CandidateRemediation]:
        self.heartbeat()
        target_dir, reports_dir, secure_dir = map(Path, (target_dir, reports_dir, secure_dir))
        deps = (self.llm, self.feed, self.log, self.liveness)

        secure_index = (Indexer(f"{self.agent_id}-sec", *deps).build(secure_dir, tick)
                        if secure_dir.exists() else CodeIndex())
        baseline = {f.fingerprint for f in store.all()}
        before = self._snapshot(target_dir)        # FR-005 no-mutation guard

        candidates: List[CandidateRemediation] = []
        for f in store.with_verdict(Verdict.TRUE_POSITIVE):   # FR-007
            cand = self._remediate_one(f, index, target_dir, secure_index,
                                       rules_dir, sandbox, reports_dir, baseline, deps)
            candidates.append(cand)
            artifact = reports_dir / f"remediation-{f.fingerprint}.json"
            sandbox.check_write(str(artifact))                # Principle IX
            atomic_write_json(artifact, cand.to_dict())       # Principle XI

        after = self._snapshot(target_dir)
        if before != after:                                   # FR-005 enforced
            raise RuntimeError("Remediator modified the target — must only propose")

        verified = sum(c.status == RemediationStatus.VERIFIED for c in candidates)
        self.emit(tick, "remediate",
                  f"{len(candidates)} candidate(s): {verified} verified, "
                  f"{sum(c.status == RemediationStatus.NO_CONTROL for c in candidates)} no-control")
        return candidates

    def _remediate_one(self, f, index, target_dir, secure_index, rules_dir,
                       sandbox, reports_dir, baseline, deps) -> CandidateRemediation:
        control = control_for(f.weakness_class)
        if not control:                                       # FR-008
            return CandidateRemediation(
                f.fingerprint, f.weakness_class, "none",
                RemediationStatus.NO_CONTROL,
                reason=f"no mapped secure control for {f.weakness_class}")

        vuln_text = (target_dir / f.path).read_text(encoding="utf-8")

        # 1) cli/api: let the model propose the fix; accept ONLY if it verifies
        #    (the model reasons, the re-scan decides — Constitution I).
        if self.llm.backend in ("cli", "api"):
            cand = self._try_patch(f, control, self._llm_patch(f, index, control),
                                   "llm", index, target_dir, rules_dir, sandbox,
                                   reports_dir, baseline, deps)
            if cand and cand.status == RemediationStatus.VERIFIED:
                return cand

        # 2) deterministic fallback: the secure twin as the control template.
        secure_src = secure_symbol_source(secure_index, f.path, f.symbol)
        if not secure_src:
            return CandidateRemediation(
                f.fingerprint, f.weakness_class, control,
                RemediationStatus.UNVERIFIED,
                reason="no secure reference implementation for this symbol")
        cand = self._try_patch(f, control, secure_src, "template", index,
                               target_dir, rules_dir, sandbox, reports_dir,
                               baseline, deps)
        return cand

    def _try_patch(self, f, control, replacement, generated_by, index, target_dir,
                   rules_dir, sandbox, reports_dir, baseline, deps):
        """Apply a proposed replacement for the finding's symbol and verify it by
        re-scan. Returns a CandidateRemediation, or None if the replacement was
        empty or produced unparseable code."""
        if not replacement:
            return None
        try:
            vuln_text = (target_dir / f.path).read_text(encoding="utf-8")
            patched_text, diff = apply_control(vuln_text, index, f, replacement)
            vr = verify_candidate(f, target_dir, f.path, patched_text, rules_dir,
                                  sandbox, reports_dir, baseline, deps)
        except Exception:                 # e.g. the model returned unparseable code
            return None
        status = (RemediationStatus.VERIFIED if vr.passed
                  else RemediationStatus.UNVERIFIED)
        reason = "" if vr.passed else (
            f"re-scan did not clear it: finding_closed={vr.finding_closed}, "
            f"new_findings={vr.new_findings}")
        return CandidateRemediation(
            f.fingerprint, f.weakness_class, control, status, change=diff,
            reason=reason, generated_by=generated_by, verification=vr)

    def _llm_patch(self, f, index, control) -> str:
        """Ask the model to rewrite the vulnerable symbol applying the control.
        Returns the replacement code (fences stripped), or "" on any failure."""
        fn = index.get(f.path, f.symbol)
        if not fn:
            return ""
        system = ("You are a secure-coding assistant. Rewrite the given Python "
                  "symbol to fix the vulnerability. Output ONLY the replacement "
                  "code for that symbol — no fences, no prose, no explanation.")
        prompt = (f"Weakness: {f.weakness_class}. Apply the control '{control}'.\n"
                  f"Vulnerable `{f.symbol}` (replace it entirely, keep the same "
                  f"name and signature):\n{fn.source}")
        try:
            raw = self.llm.complete(self.name, system, prompt)
        except Exception as exc:
            self.log.discarded(f"llm-patch:{f.symbol}", f"error: {exc}")
            return ""
        return self._strip_fences(raw)

    @staticmethod
    def _strip_fences(raw: str) -> str:
        txt = raw.strip()
        if txt.startswith("```"):
            txt = re.sub(r"^```[a-zA-Z]*\n?", "", txt).rstrip("`").rstrip()
        return txt

    @staticmethod
    def _snapshot(root: Path) -> Dict[str, bytes]:
        return {str(p.relative_to(root)): p.read_bytes()
                for p in sorted(Path(root).rglob("*")) if p.is_file()}
