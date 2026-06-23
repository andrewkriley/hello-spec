"""Heartbeat liveness (Foundry spec.md §8.2 / FR-100-101, Constitution III).

An agent is alive iff its heartbeat is recent. Wall-clock runtime is NOT a
liveness signal: a long-running but heartbeating agent is healthy. Work is
reclaimed from an agent ONLY when its heartbeat goes stale.

A logical clock is used instead of wall-clock so the demo is deterministic
(NFR-004) and so tests can advance time explicitly. The heartbeat lane is
modelled as a separate update path that is never blocked by work.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class LivenessRegistry:
    """Tracks the last heartbeat tick per agent."""

    stale_after: int = 3            # ticks; a claim is reclaimable past this
    _now: int = 0
    _last_beat: Dict[str, int] = field(default_factory=dict)

    def tick(self, n: int = 1) -> int:
        self._now += n
        return self._now

    def heartbeat(self, agent_id: str) -> None:
        # The heartbeat has its own lane: it records immediately and is never
        # starved by an agent that is busy doing work.
        self._last_beat[agent_id] = self._now

    def age(self, agent_id: str) -> int:
        if agent_id not in self._last_beat:
            return self.stale_after + 1
        return self._now - self._last_beat[agent_id]

    def is_alive(self, agent_id: str) -> bool:
        return self.age(agent_id) <= self.stale_after
