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


class RemediationStatus(enum.Enum):
    """Status of a candidate remediation (Remediator role, spec §6.4)."""

    VERIFIED = "verified"        # patch re-scanned clean (finding closed, no new)
    UNVERIFIED = "unverified"    # could not demonstrate the fix
    NO_CONTROL = "no-control"    # no mapped secure control for this class


@dataclass
class VerificationResult:
    """Outcome of checking a candidate against an isolated patched copy."""

    finding_closed: bool
    new_findings: int

    @property
    def passed(self) -> bool:
        return self.finding_closed and self.new_findings == 0

    def to_dict(self) -> dict:
        return {"finding_closed": self.finding_closed,
                "new_findings": self.new_findings, "passed": self.passed}


@dataclass
class CandidateRemediation:
    """A proposed, verified-or-not fix for exactly one confirmed finding (§6.4).

    The Remediator never sets `exploited`, never auto-applies the change, and a
    candidate is `verified` only when its VerificationResult passed (Principle I:
    demonstrated, not asserted)."""

    finding_fingerprint: str
    weakness_class: str
    control: str                  # control id, or "none"
    status: RemediationStatus
    change: str = ""
    reason: str = ""
    generated_by: str = "template"   # "template" | "llm"
    verification: Optional[VerificationResult] = None

    def to_dict(self) -> dict:
        return {
            "finding_fingerprint": self.finding_fingerprint,
            "weakness_class": self.weakness_class,
            "control": self.control,
            "status": self.status.value,
            "change": self.change,
            "reason": self.reason,
            "generated_by": self.generated_by,
            "verification": self.verification.to_dict() if self.verification else None,
        }


@dataclass
class Variant:
    """A lead surfaced by the Variant-Hunter (spec §6.2): another place the same
    weakness class as a confirmed finding appears. A lead for human follow-up —
    never a promoted finding (Constitution II/X)."""

    source_fingerprint: str   # the confirmed true-positive this derives from
    weakness_class: str
    location: str             # "path::symbol"
    verdict: str              # the sibling's current verdict
    fingerprint: str          # the sibling's stable identity

    def to_dict(self) -> dict:
        return {
            "source_fingerprint": self.source_fingerprint,
            "weakness_class": self.weakness_class,
            "location": self.location,
            "verdict": self.verdict,
            "fingerprint": self.fingerprint,
        }


@dataclass
class RuleProposal:
    """A CodeGuard rule the Self-Improver authored from a rule-gap (§6.5). A
    proposal for human acceptance, written to a sandbox path — never merged into
    the committed corpus by the system (Constitution X). `verified` is set only
    after a re-scan shows the rule catches the class (Constitution I)."""

    weakness_class: str
    rule_id: str
    filename: str
    matcher: str
    verified: bool = False
    path: str = ""

    def to_dict(self) -> dict:
        return {
            "weakness_class": self.weakness_class,
            "rule_id": self.rule_id,
            "filename": self.filename,
            "matcher": self.matcher,
            "verified": self.verified,
            "path": self.path,
        }


@dataclass
class AttackPath:
    """A chain from a foothold finding to an impact finding (Attack-Mapper, §6.3).
    A lead for a human — built only from already-confirmed findings (Constitution
    II); the mapper invents nothing and changes nothing (Constitution X)."""

    entry_class: str
    entry_location: str
    entry_fingerprint: str
    impact_class: str
    impact_location: str
    impact_fingerprint: str
    narrative: str

    def to_dict(self) -> dict:
        return {
            "entry_class": self.entry_class,
            "entry_location": self.entry_location,
            "entry_fingerprint": self.entry_fingerprint,
            "impact_class": self.impact_class,
            "impact_location": self.impact_location,
            "impact_fingerprint": self.impact_fingerprint,
            "narrative": self.narrative,
        }
