"""Budget tracking (Foundry spec.md §9.3 / FR-112-114, Constitution V).

Tracks cumulative LLM spend (currency) and per-call token accounting, plus a
logical wall-clock. Caps default unset; a pre-flight warning fires if both are
unset. The provider is the rate arbiter (Constitution V): there is no internal
pre-throttle here below the provider's real limit — only accounting and an
adaptive fleet-wide backoff signal when the provider pushes back.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CallRecord:
    role: str
    tokens_in: int
    tokens_out: int
    cost: float


@dataclass
class Budget:
    spend_cap: Optional[float] = None        # currency; None = unset
    time_cap: Optional[int] = None           # logical ticks; None = unset
    cost_per_1k_in: float = 0.003
    cost_per_1k_out: float = 0.015
    calls: List[CallRecord] = field(default_factory=list)
    _ticks: int = 0
    # Constitution V: shared, fleet-wide adaptive backoff (not per-agent)
    backoff_level: int = 0

    def preflight_warning(self) -> Optional[str]:
        if self.spend_cap is None and self.time_cap is None:
            return ("WARNING: neither spend_cap nor time_cap is set; this run "
                    "has no budget ceiling (FR-114).")
        return None

    def record_call(self, role: str, tokens_in: int, tokens_out: int,
                    cost: Optional[float] = None) -> None:
        if cost is None:   # estimate when the provider does not report cost
            cost = (tokens_in / 1000) * self.cost_per_1k_in \
                 + (tokens_out / 1000) * self.cost_per_1k_out
        self.calls.append(CallRecord(role, tokens_in, tokens_out, cost))

    def note_rate_limit(self) -> None:
        """Provider pushed back -> raise shared backoff. Adaptive, fleet-wide."""
        self.backoff_level += 1

    def note_success(self) -> None:
        if self.backoff_level > 0:
            self.backoff_level -= 1

    def tick(self, n: int = 1) -> None:
        self._ticks += n

    @property
    def spend(self) -> float:
        return sum(c.cost for c in self.calls)

    @property
    def tokens(self) -> int:
        return sum(c.tokens_in + c.tokens_out for c in self.calls)

    @property
    def runtime(self) -> int:
        return self._ticks

    def per_role(self) -> Dict[str, Dict[str, float]]:
        roll: Dict[str, Dict[str, float]] = {}
        for c in self.calls:
            r = roll.setdefault(c.role, {"calls": 0, "tokens": 0, "cost": 0.0})
            r["calls"] += 1
            r["tokens"] += c.tokens_in + c.tokens_out
            r["cost"] += c.cost
        return roll

    def exceeded(self) -> bool:
        if self.spend_cap is not None and self.spend >= self.spend_cap:
            return True
        if self.time_cap is not None and self.runtime >= self.time_cap:
            return True
        return False
