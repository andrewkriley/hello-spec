"""Orchestrator (Foundry spec.md §5.1 / FR-001-019).

The operator's interface and the fleet's lifecycle controller. It spawns the
roles, drives the evaluation, services operator messages (FR-006-009), answers
status queries (FR-013), applies operator overrides (FR-016/NFR-009), and
hot-reloads budget/rules/fleet at runtime (FR-128). Operator instructions
outrank every agent (Constitution X).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from ..lifecycle.models import Finding, Verdict
from .base import Role


@dataclass
class OperatorMessage:
    kind: str          # blocker | request | feedback | info
    text: str


class Orchestrator(Role):
    name = "orchestrator"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.messages: List[OperatorMessage] = []
        self._seen: set = set()
        self.overrides: List[str] = []

    # FR-006-009: async, one-way, deduplicated operator messages.
    def post_message(self, kind: str, text: str) -> None:
        key = (kind, text)
        if key in self._seen:
            return                 # dedup (FR-009)
        self._seen.add(key)
        self.messages.append(OperatorMessage(kind, text))

    def messages_as_dicts(self) -> List[Dict]:
        return [{"kind": m.kind, "text": m.text} for m in self.messages]

    # FR-016 / NFR-009: operator override of an automated decision, recorded.
    def override_verdict(self, store, fingerprint: str, verdict: Verdict,
                         note: str, tick: int) -> None:
        f = store.get(fingerprint)
        if not f:
            return
        prev = f.verdict
        f.verdict = verdict
        f.reasoning = f"[operator override] {note} (was {prev.value if prev else None})"
        self.overrides.append(f"{fingerprint}: {prev} -> {verdict.value}")
        self.emit(tick, "override",
                  f"operator set {fingerprint[:8]} to {verdict.value}")

    # FR-013: status query answers from the substrate (agrees with dashboard).
    def status(self, store) -> Dict:
        return {
            "total_findings": len(store.all()),
            "true_positives": len(store.with_verdict(Verdict.TRUE_POSITIVE)),
            "surfaced": len(store.surfaced()),
            "overrides": len(self.overrides),
        }
