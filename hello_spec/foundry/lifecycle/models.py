"""Core data model for the finding lifecycle (Foundry spec.md §7).

Implements: states (§7.1), verdicts (§7.2), the evidence gate's data shape
(§7.3), the exploited flag (§7.4), fingerprints (§7.5) and the label
taxonomy (§7.6).
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import List, Optional

from .fingerprint import fingerprint


class FindingState(enum.Enum):
    """§7.1 — the states a finding traverses."""

    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"   # verdict assigned
    VALIDATED = "validated"   # exploited reproduction done
    PUBLISHED = "published"   # surfaced to the tracker


class Verdict(enum.Enum):
    """§7.2 / FR-050 — the five verdicts a Triager may assign."""

    TRUE_POSITIVE = "true-positive"
    FALSE_POSITIVE = "false-positive"
    NEEDS_REVIEW = "needs-review"
    NOT_APPLICABLE = "not-applicable"
    CODE_QUALITY = "code-quality"


class Severity(enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Citation:
    """One leg of the evidence gate (§7.3). A pointer into the target's code
    that the gate mechanically resolves against the Indexer."""

    leg: str           # "reachability" | "trust-boundary" | "impact"
    file: str
    symbol: str
    line: int
    note: str

    def resolves(self, index) -> bool:
        """Mechanically verify this citation points at real code.
        Principle I: a claim whose citation does not resolve is demoted."""
        return index.resolves(self.file, self.symbol, self.line)


@dataclass
class EvidenceGate:
    """§7.3 / FR-087-088 — a true-positive MUST carry all three legs, each
    resolving to real code."""

    reachability: Optional[Citation] = None
    trust_boundary: Optional[Citation] = None
    impact: Optional[Citation] = None

    def legs(self) -> List[Citation]:
        return [c for c in (self.reachability, self.trust_boundary, self.impact) if c]

    def is_complete(self) -> bool:
        return all((self.reachability, self.trust_boundary, self.impact))

    def all_resolve(self, index) -> bool:
        return self.is_complete() and all(c.resolves(index) for c in self.legs())

    def failed_legs(self, index) -> List[str]:
        return [c.leg for c in self.legs() if not c.resolves(index)]


@dataclass
class Finding:
    """A vulnerability finding as it moves through the lifecycle."""

    path: str
    symbol: str
    weakness_class: str          # e.g. "CWE-89"; part of the fingerprint
    title: str
    description: str
    technique: str               # FR-043: how it was found, e.g. "rule:codeguard-..."
    state: FindingState = FindingState.CANDIDATE
    verdict: Optional[Verdict] = None
    reasoning: str = ""
    severity: Optional[Severity] = None
    evidence: EvidenceGate = field(default_factory=EvidenceGate)
    exploited: bool = False       # §7.4 — set ONLY by the Validator
    source_system: str = "hello-spec"
    labels: List[str] = field(default_factory=list)

    @property
    def fingerprint(self) -> str:
        """§7.5 / FR-090 — identity is (path, symbol, class); excludes line
        numbers and snippets so it is stable under edit (Principle VIII)."""
        return fingerprint(self.path, self.symbol, self.weakness_class)

    def to_dict(self) -> dict:
        return {
            "fingerprint": self.fingerprint,
            "path": self.path,
            "symbol": self.symbol,
            "weakness_class": self.weakness_class,
            "title": self.title,
            "description": self.description,
            "technique": self.technique,
            "state": self.state.value,
            "verdict": self.verdict.value if self.verdict else None,
            "reasoning": self.reasoning,
            "severity": self.severity.value if self.severity else None,
            "exploited": self.exploited,
            "source_system": self.source_system,
            "labels": self.labels,
            "evidence": {
                leg.leg: {"file": leg.file, "symbol": leg.symbol,
                          "line": leg.line, "note": leg.note}
                for leg in self.evidence.legs()
            },
        }
