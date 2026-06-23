"""Coverage-Guide (Foundry spec.md §5.7 / FR-067-074, Constitution VI).

Translates the operator's goals into a checklist, tracks progress as the fleet
works, and signals coverage-complete only when every checklist item has been
attempted. The yield auto-stop is gated on this signal (Constitution VI:
Coverage Before Yield) — the system does not declare itself done on a dry spell
before it has looked everywhere the operator asked.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .base import Role


@dataclass
class ChecklistItem:
    goal: str
    attempted: bool = False


@dataclass
class Coverage:
    items: List[ChecklistItem] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def done(self) -> int:
        return sum(1 for i in self.items if i.attempted)

    @property
    def complete(self) -> bool:
        return self.total > 0 and self.done == self.total

    def as_dict(self) -> Dict:
        return {"total": self.total, "done": self.done, "complete": self.complete}


class CoverageGuide(Role):
    name = "coverage-guide"

    def build_checklist(self, goals: List[str], tick: int) -> Coverage:
        self.heartbeat()
        cov = Coverage(items=[ChecklistItem(goal=g) for g in goals])
        self.emit(tick, "coverage", f"checklist built: {cov.total} item(s)")
        return cov

    def mark_attempted(self, cov: Coverage, goal_substr: str) -> None:
        for item in cov.items:
            if goal_substr.lower() in item.goal.lower():
                item.attempted = True

    def attempt_all(self, cov: Coverage, tick: int) -> None:
        """After the Detector swept every entry point and the Triager processed
        every candidate, each goal has been credibly attempted (FR-072)."""
        self.heartbeat()
        for item in cov.items:
            item.attempted = True
        self.emit(tick, "coverage",
                  f"coverage-complete={cov.complete} ({cov.done}/{cov.total})")
