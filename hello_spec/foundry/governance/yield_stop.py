"""Yield auto-stop (Foundry spec.md §9.4 / FR-115-117, Constitution VI).

The fleet halts itself only when ALL of the following hold:
  - trailing yield (severity-weighted confirmed findings per spend unit) is
    below threshold;
  - the Coverage-Guide has signalled coverage-complete;
  - the minimum runtime has elapsed;
  - the trailing window is full.

Constitution VI (Coverage Before Yield): low yield alone is NOT sufficient. An
evaluation that stops because the first dry spell looked unproductive has not
done the job it was given.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict

from ..lifecycle.models import Finding, Severity, Verdict

# Seed authors' recommended geometric weighting (~3.15x per tier) and a 2x
# multiplier for exploited findings.
SEVERITY_WEIGHTS: Dict[Severity, float] = {
    Severity.INFO: 0.0,
    Severity.LOW: 1.0,
    Severity.MEDIUM: 3.15,
    Severity.HIGH: 9.9,
    Severity.CRITICAL: 31.2,
}
EXPLOITED_MULTIPLIER = 2.0


def finding_weight(f: Finding) -> float:
    if f.verdict != Verdict.TRUE_POSITIVE or not f.severity:
        return 0.0
    w = SEVERITY_WEIGHTS.get(f.severity, 0.0)
    return w * (EXPLOITED_MULTIPLIER if f.exploited else 1.0)


@dataclass
class YieldGovernor:
    threshold: float = 0.5            # weighted findings per spend unit
    window: int = 5                   # trailing samples
    min_runtime: int = 1             # logical ticks before auto-stop allowed
    _samples: Deque[float] = field(default_factory=deque)

    def sample(self, weighted_findings: float, spend_delta: float) -> None:
        ratio = weighted_findings / spend_delta if spend_delta > 0 else 0.0
        self._samples.append(ratio)
        while len(self._samples) > self.window:
            self._samples.popleft()

    def trailing_yield(self) -> float:
        if not self._samples:
            return 0.0
        return sum(self._samples) / len(self._samples)

    def window_full(self) -> bool:
        return len(self._samples) >= self.window

    def should_stop(self, coverage_complete: bool, runtime: int) -> bool:
        return (
            self.window_full()
            and self.trailing_yield() < self.threshold
            and coverage_complete                 # Constitution VI
            and runtime >= self.min_runtime
        )
