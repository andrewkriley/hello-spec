"""Structured session logs (Foundry spec.md §10 / FR-122-123, NFR-007).

Append-only structured records (turns, tool calls, tool results, token usage)
to durable storage. The full provenance chain (detection -> triage ->
validation -> report) is reconstructable from these records (NFR-007:
Auditability). NFR-008: discarded work is logged visibly, never silently
dropped.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from ..substrate.persistence import atomic_write_text


@dataclass
class SessionLog:
    path: Optional[Path] = None
    records: List[dict] = field(default_factory=list)

    def record(self, **fields) -> None:
        self.records.append(dict(fields))

    def discarded(self, what: str, why: str) -> None:
        # NFR-008: no silent data loss.
        self.records.append({"event": "discarded", "what": what, "why": why})

    def persist(self) -> None:
        if self.path:
            atomic_write_text(
                Path(self.path),
                "\n".join(json.dumps(r, sort_keys=True) for r in self.records))
