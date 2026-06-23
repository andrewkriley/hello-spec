"""Work queue (Foundry spec.md §8.1 / FR-094-099, Constitution IV).

Provides:
- ordered tasks with stable id, title, description, priority, state;
- atomic claim (two agents claiming concurrently get different units);
- liveness-tied release (a dead holder's claim is reclaimed automatically);
- auto-block after N consecutive failures;
- runtime writability by operator and agents.

A claim dies with its holder: there is no unit an agent can hold past its own
death (Constitution IV: Claims Are Atomic And Mortal).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from .liveness import LivenessRegistry


class TaskState(Enum):
    OPEN = "open"
    CLAIMED = "claimed"
    BLOCKED = "blocked"
    CLOSED = "closed"


@dataclass
class Task:
    id: str
    title: str
    description: str
    priority: int = 100        # lower = more urgent
    state: TaskState = TaskState.OPEN
    holder: Optional[str] = None
    failures: int = 0


class WorkQueue:
    def __init__(self, liveness: LivenessRegistry, block_after: int = 3) -> None:
        self._lock = threading.Lock()      # makes claim atomic (FR-096)
        self._tasks: Dict[str, Task] = {}
        self._order: List[str] = []
        self._liveness = liveness
        self._block_after = block_after

    # -- runtime writability (FR-099) -------------------------------------
    def add(self, task: Task) -> None:
        with self._lock:
            if task.id not in self._tasks:
                self._order.append(task.id)
            self._tasks[task.id] = task

    def all(self) -> List[Task]:
        with self._lock:
            return [self._tasks[i] for i in self._order]

    def open_depth(self) -> int:
        return sum(1 for t in self.all() if t.state == TaskState.OPEN)

    # -- atomic claim (FR-096) --------------------------------------------
    def claim(self, agent_id: str) -> Optional[Task]:
        with self._lock:
            self._reclaim_stale_locked()
            for tid in sorted(self._order, key=lambda i: self._tasks[i].priority):
                t = self._tasks[tid]
                if t.state == TaskState.OPEN:
                    t.state = TaskState.CLAIMED
                    t.holder = agent_id
                    return t
            return None

    # -- liveness-tied release (FR-097, Constitution IV) ------------------
    def _reclaim_stale_locked(self) -> None:
        for t in self._tasks.values():
            if t.state == TaskState.CLAIMED and t.holder \
                    and not self._liveness.is_alive(t.holder):
                t.state = TaskState.OPEN
                t.holder = None

    def reclaim_stale(self) -> None:
        with self._lock:
            self._reclaim_stale_locked()

    def complete(self, task_id: str) -> None:
        with self._lock:
            self._tasks[task_id].state = TaskState.CLOSED
            self._tasks[task_id].holder = None

    # -- auto-block after N failures (FR-098) -----------------------------
    def fail(self, task_id: str) -> None:
        with self._lock:
            t = self._tasks[task_id]
            t.failures += 1
            if t.failures >= self._block_after:
                t.state = TaskState.BLOCKED
                t.holder = None
            else:
                t.state = TaskState.OPEN
                t.holder = None
