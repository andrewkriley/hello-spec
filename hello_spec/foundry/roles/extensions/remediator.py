"""Remediator (Foundry spec.md §6.4) — candidate patch generation + verification.

For each confirmed true-positive whose class maps to a secure control, the
Remediator proposes a candidate fix and VERIFIES it against an isolated copy of
the target (the finding must close and nothing new may appear) before labelling
it `verified`. It never mutates the target and never auto-applies — candidates
are written, with provenance, for human review (Constitution X). Classes with no
mapped control are reported honestly as `no-control`, never force-patched.
"""
from __future__ import annotations

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

        secure_src = secure_symbol_source(secure_index, f.path, f.symbol)
        if not secure_src:
            return CandidateRemediation(
                f.fingerprint, f.weakness_class, control,
                RemediationStatus.UNVERIFIED,
                reason="no secure reference implementation for this symbol")

        vuln_text = (target_dir / f.path).read_text(encoding="utf-8")
        patched_text, diff = apply_control(vuln_text, index, f, secure_src)
        vr = verify_candidate(f, target_dir, f.path, patched_text, rules_dir,
                              sandbox, reports_dir, baseline, deps)
        status = (RemediationStatus.VERIFIED if vr.passed
                  else RemediationStatus.UNVERIFIED)
        reason = "" if vr.passed else (
            f"re-scan did not clear it: finding_closed={vr.finding_closed}, "
            f"new_findings={vr.new_findings}")
        return CandidateRemediation(
            f.fingerprint, f.weakness_class, control, status,
            change=diff, reason=reason, generated_by="template", verification=vr)

    @staticmethod
    def _snapshot(root: Path) -> Dict[str, bytes]:
        return {str(p.relative_to(root)): p.read_bytes()
                for p in sorted(Path(root).rglob("*")) if p.is_file()}
