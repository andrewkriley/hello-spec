"""Sandbox (Foundry spec.md §9.1 / FR-107-109, Constitution IX).

Network egress is constrained to an allowlist and filesystem writes to
designated paths. The boundary is enforced HERE, at the infrastructure
boundary the agent calls through (the LLM adapter and the report writer),
never by a prompt. An agent that reads adversarial target content and is
talked into reaching a forbidden host still cannot: the call is refused
before it leaves.

In a real deployment this maps to container network policy + read-only mounts
(§11.6). Here it is a chokepoint every outbound action must pass through.
"""
from __future__ import annotations

from pathlib import Path
from typing import List


class SandboxViolation(RuntimeError):
    pass


class Sandbox:
    def __init__(self, egress_allowlist: List[str], writable_paths: List[str],
                 readonly_paths: List[str]) -> None:
        self.egress_allowlist = list(egress_allowlist)
        self.writable_paths = [Path(p).resolve() for p in writable_paths]
        self.readonly_paths = [Path(p).resolve() for p in readonly_paths]

    def check_egress(self, host: str) -> None:
        if host not in self.egress_allowlist:
            raise SandboxViolation(
                f"egress to '{host}' blocked; allowlist={self.egress_allowlist}")

    def check_write(self, path: str) -> None:
        target = Path(path).resolve()
        for ro in self.readonly_paths:
            if _is_within(target, ro):
                raise SandboxViolation(f"write to read-only path '{path}' blocked")
        if self.writable_paths and not any(_is_within(target, w)
                                           for w in self.writable_paths):
            raise SandboxViolation(
                f"write to '{path}' blocked; not under a writable path")


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False
