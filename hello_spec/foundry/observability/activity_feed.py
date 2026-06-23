"""Live activity feed (Foundry spec.md §10 / FR-121).

An in-memory, filterable feed of events (by role, by event kind). Backed by
the same data the dashboard reads, so status query and dashboard agree
(FR-124).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Event:
    tick: int
    role: str
    kind: str         # e.g. "detect", "triage", "verdict", "validate", "publish", "degradation"
    message: str


@dataclass
class ActivityFeed:
    events: List[Event] = field(default_factory=list)

    def emit(self, tick: int, role: str, kind: str, message: str) -> None:
        self.events.append(Event(tick, role, kind, message))

    def filter(self, role: Optional[str] = None,
               kind: Optional[str] = None) -> List[Event]:
        out = self.events
        if role:
            out = [e for e in out if e.role == role]
        if kind:
            out = [e for e in out if e.kind == kind]
        return list(out)
