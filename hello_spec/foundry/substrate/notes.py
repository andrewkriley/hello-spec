"""Shared notes (Foundry spec.md §8.4 / FR-104-104b, Constitution X).

An optional persistent notes document, read at startup. It is size-bounded and
write-locked. Crucially it MUST NOT contain coverage claims or "done"
assertions: agents talk each other out of work by reading a prior agent's
"this area is fully covered" note. Only the operator and the Coverage-Guide's
checklist may speak to coverage (Constitution X: The Operator Outranks Every
Agent).
"""
from __future__ import annotations

import re
import threading
from typing import List

_BANNED = re.compile(r"\b(done|complete|completed|fully covered|saturated|"
                     r"nothing left|finished|exhaustive)\b", re.I)


class NotesRejected(ValueError):
    pass


class SharedNotes:
    def __init__(self, max_bytes: int = 4096) -> None:
        self._lock = threading.Lock()
        self._entries: List[str] = []
        self._max_bytes = max_bytes

    def read(self) -> List[str]:
        with self._lock:
            return list(self._entries)

    def append(self, agent_id: str, note: str) -> None:
        if _BANNED.search(note):
            raise NotesRejected(
                "notes MUST NOT contain coverage/done assertions (FR-104b)")
        with self._lock:
            entry = f"[{agent_id}] {note}"
            size = sum(len(e) for e in self._entries) + len(entry)
            if size > self._max_bytes:
                raise NotesRejected("shared notes size bound exceeded (FR-104b)")
            self._entries.append(entry)
