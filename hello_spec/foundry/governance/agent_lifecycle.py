"""Agent session lifecycle limits (Foundry spec.md §9.5 / FR-118-119a).

A soft session limit steers an agent to wrap up and release its claims; a hard
limit terminates it and spawns a fresh instance. Limits are measured in
turns/tokens/ticks. Crucially (Constitution III), the hard limit does NOT
re-queue work that is still held — session rotation is a cost control, not a
liveness misfire. The agent releases or hands off its claims first.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SessionLimits:
    soft_turns: int = 6
    hard_turns: int = 10

    def status(self, turns: int) -> str:
        if turns >= self.hard_turns:
            return "rotate"      # terminate + spawn fresh (after claims released)
        if turns >= self.soft_turns:
            return "wrap-up"     # steer agent to finish and release claims
        return "ok"
