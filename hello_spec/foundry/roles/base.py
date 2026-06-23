"""Base agent role (Foundry spec.md §5).

Every role carries a stable agent id, heartbeats into the LivenessRegistry,
emits to the activity feed and structured session log, and reaches the model
only through the sandboxed LLM adapter. Roles never write to the issue tracker
except the Reporter (FR-044/FR-078).
"""
from __future__ import annotations

from ..llm.adapter import LLMAdapter
from ..observability.activity_feed import ActivityFeed
from ..observability.session_log import SessionLog
from ..substrate.liveness import LivenessRegistry


class Role:
    name = "role"

    def __init__(self, agent_id: str, llm: LLMAdapter, feed: ActivityFeed,
                 log: SessionLog, liveness: LivenessRegistry) -> None:
        self.agent_id = agent_id
        self.llm = llm
        self.feed = feed
        self.log = log
        self.liveness = liveness

    def heartbeat(self) -> None:
        self.liveness.heartbeat(self.agent_id)

    def emit(self, tick: int, kind: str, message: str) -> None:
        self.feed.emit(tick, self.name, kind, message)
        self.log.record(tick=tick, role=self.name, agent=self.agent_id,
                        kind=kind, message=message)
