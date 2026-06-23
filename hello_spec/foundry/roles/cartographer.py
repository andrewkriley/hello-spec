"""Cartographer (Foundry spec.md §5.3 / FR-030-036a).

Produces the security map: architecture, attack surface (entry points), trust
boundaries (where untrusted data enters), data flows, and a threat-model
summary. Derived deterministically from the Indexer's output, with the LLM
adapter consulted for the narrative summary (stubbed offline).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .base import Role
from .indexer import CodeIndex, FuncInfo


@dataclass
class SecurityMap:
    entry_points: List[str] = field(default_factory=list)
    trust_boundaries: List[str] = field(default_factory=list)
    data_flows: List[str] = field(default_factory=list)
    threat_model: str = ""


class Cartographer(Role):
    name = "cartographer"

    def map(self, index: CodeIndex, goals: List[str], tick: int) -> SecurityMap:
        self.heartbeat()
        smap = SecurityMap()
        for fn in index.all():
            if fn.route_line is not None:                       # attack surface
                smap.entry_points.append(f"{fn.file}:{fn.name} (route)")
            if fn.reads_request:                                 # trust boundary
                smap.trust_boundaries.append(
                    f"{fn.file}:{fn.name} reads untrusted request input")
                smap.data_flows.append(
                    f"request -> {fn.name} -> {sorted(fn.calls)}")
        # Narrative summary via the model (deterministic in stub mode).
        smap.threat_model = self.llm.complete(
            self.name,
            "You are a security cartographer. Summarise the threat model.",
            f"goals={goals}; entry_points={smap.entry_points}")
        self.emit(tick, "map",
                  f"{len(smap.entry_points)} entry point(s), "
                  f"{len(smap.trust_boundaries)} trust boundary(ies)")
        return smap
