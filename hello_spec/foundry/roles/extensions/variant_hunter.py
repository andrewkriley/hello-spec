"""Variant-Hunter (Foundry spec.md §6.2) — pattern replication.

Turns one confirmed finding into leads for its siblings: for each confirmed
true-positive, it surfaces every other place the same weakness class appears —
including out-of-scope or non-security siblings, each labelled with its verdict.

It is read-only over the finding store: it creates no findings, changes no
verdicts, and never touches the target (Constitution X). Variants are leads for a
human, never promoted findings (Constitution II). The report is written
atomically through the sandbox (IX/XI).

Scope note: "same weakness pattern" is approximated by "same weakness class".
A fuller implementation could add an LLM hunt for instances the detector missed;
that is out of scope here.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from ...lifecycle.models import Variant, Verdict
from ...substrate.persistence import atomic_write_json
from ..base import Role


class VariantHunter(Role):
    name = "variant-hunter"

    def hunt(self, store, sandbox, reports_dir: Path, tick: int) -> List[Variant]:
        self.heartbeat()
        reports_dir = Path(reports_dir)
        confirmed = store.with_verdict(Verdict.TRUE_POSITIVE)

        variants: List[Variant] = []
        for tp in confirmed:                       # FR-001
            for other in store.all():
                if other.fingerprint == tp.fingerprint:
                    continue                       # never a variant of itself
                if other.weakness_class != tp.weakness_class:
                    continue
                variants.append(Variant(           # FR-002 / FR-003
                    source_fingerprint=tp.fingerprint,
                    weakness_class=tp.weakness_class,
                    location=f"{other.path}::{other.symbol}",
                    verdict=other.verdict.value if other.verdict else "unknown",
                    fingerprint=other.fingerprint))

        artifact = reports_dir / "variants.json"
        sandbox.check_write(str(artifact))         # Principle IX
        atomic_write_json(artifact, [v.to_dict() for v in variants])  # Principle XI
        self.emit(tick, "variant-hunt",
                  f"{len(variants)} variant lead(s) from "
                  f"{len(confirmed)} confirmed finding(s)")
        return variants
