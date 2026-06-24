"""Attack-Mapper (Foundry spec.md §6.3) — chain findings into attack paths.

Reads confirmed true-positives, labels each by attack role (foothold vs impact)
from its weakness class, and links each foothold to each distinct impact as an
attack path with a plain-language narrative — turning a list of separate bugs
into an attack story (e.g. a hardcoded credential → remote code execution).

Read-only over the finding store: invents no findings, changes no verdicts, never
touches the target (Constitution X). Paths are leads, not promoted findings
(Constitution II); the report is written atomically through the sandbox (IX/XI).

Scope note: attack-role classification is approximated by weakness class. A
fuller implementation would use the security map's trust boundaries and data flows.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from ...lifecycle.models import AttackPath, Verdict
from ...substrate.persistence import atomic_write_json
from ..base import Role

# Weakness class -> role in an attack chain.
FOOTHOLD = {
    "CWE-798": "exposes a credential an attacker can use to authenticate",
    "CWE-208": "lets an attacker forge or brute-force an auth token",
}
IMPACT = {
    "CWE-78": "remote code execution on the host",
    "CWE-89": "exfiltration of arbitrary database records",
    "CWE-639": "access to other users' objects",
    "CWE-22": "reading arbitrary files",
}


class AttackMapper(Role):
    name = "attack-mapper"

    def map_attacks(self, store, sandbox, reports_dir: Path,
                    tick: int) -> List[AttackPath]:
        self.heartbeat()
        reports_dir = Path(reports_dir)
        confirmed = store.with_verdict(Verdict.TRUE_POSITIVE)
        footholds = [f for f in confirmed if f.weakness_class in FOOTHOLD]
        impacts = [f for f in confirmed if f.weakness_class in IMPACT]

        paths: List[AttackPath] = []
        for entry in footholds:                        # FR-001/FR-002
            for impact in impacts:
                if entry.fingerprint == impact.fingerprint:
                    continue                           # never chain to self
                paths.append(AttackPath(
                    entry_class=entry.weakness_class,
                    entry_location=f"{entry.path}::{entry.symbol}",
                    entry_fingerprint=entry.fingerprint,
                    impact_class=impact.weakness_class,
                    impact_location=f"{impact.path}::{impact.symbol}",
                    impact_fingerprint=impact.fingerprint,
                    narrative=(
                        f"{entry.weakness_class} at {entry.path}::{entry.symbol} "
                        f"{FOOTHOLD[entry.weakness_class]}, then reach "
                        f"{impact.weakness_class} at {impact.path}::{impact.symbol} "
                        f"for {IMPACT[impact.weakness_class]}.")))

        artifact = reports_dir / "attack-paths.json"
        sandbox.check_write(str(artifact))             # Principle IX
        atomic_write_json(artifact, [p.to_dict() for p in paths])  # Principle XI
        self.emit(tick, "attack-map",
                  f"{len(paths)} attack path(s) from {len(footholds)} foothold(s) "
                  f"× {len(impacts)} impact(s)")
        return paths
