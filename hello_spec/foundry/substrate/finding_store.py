"""Internal finding store (Foundry spec.md §5.4/§7, Constitution II & VIII).

The store absorbs all detection volume. It is keyed by fingerprint so that:
- re-detections deduplicate (FR-045);
- re-runs reuse prior verdicts and update-not-recreate (FR-090, NFR-002);
- only findings that survive triage are surfaced (Constitution II).

Persisted atomically (Constitution XI) via persistence.atomic_write_json.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from ..lifecycle.models import Finding, FindingState, Verdict
from .persistence import atomic_write_json


class FindingStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self._by_fp: Dict[str, Finding] = {}
        self._path = Path(path) if path else None

    def upsert(self, finding: Finding) -> bool:
        """Insert a candidate, deduplicating by fingerprint. Returns True if
        the finding was new, False if a finding with this fingerprint already
        existed (its prior verdict/reasoning is preserved — FR-045/NFR-002)."""
        fp = finding.fingerprint
        if fp in self._by_fp:
            return False
        self._by_fp[fp] = finding
        return True

    def get(self, fingerprint: str) -> Optional[Finding]:
        return self._by_fp.get(fingerprint)

    def all(self) -> List[Finding]:
        return list(self._by_fp.values())

    def with_verdict(self, verdict: Verdict) -> List[Finding]:
        return [f for f in self._by_fp.values() if f.verdict == verdict]

    def surfaced(self) -> List[Finding]:
        """Constitution II: only true-positives that reached PUBLISHED."""
        return [f for f in self._by_fp.values()
                if f.verdict == Verdict.TRUE_POSITIVE
                and f.state in (FindingState.VALIDATED, FindingState.PUBLISHED)]

    def persist(self) -> None:
        if self._path:
            atomic_write_json(self._path, [f.to_dict() for f in self.all()])
