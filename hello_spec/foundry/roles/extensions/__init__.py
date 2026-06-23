"""Extension roles (Foundry spec.md §6).

These are the optional roles the spec says to build only after the core eight
work. They are included here as minimal, documented stubs so the full role
taxonomy is represented; the Self-Improver does real (small) work by turning
rule-gap entries into proposed new rules — the rule-gap flywheel (§6.5).

  - DeepTester (§6.1):  input-generation testing (fuzzing, property-based).
  - VariantHunter (§6.2): replicate a confirmed pattern across the codebase.
  - AttackMapper (§6.3): privilege graphs; chain findings into attack paths.
  - Remediator (§6.4): candidate patch generation + verification.
  - SelfImprover (§6.5): analyse logs/rule-gaps; propose config/prompt/rule tuning.
"""
from __future__ import annotations

from typing import List

from ..base import Role


class DeepTester(Role):
    name = "deep-tester"


class VariantHunter(Role):
    name = "variant-hunter"

    def hunt(self, store, weakness_class: str) -> List[str]:
        """Replicate a confirmed pattern: list other findings of the same class."""
        return [f.symbol for f in store.all() if f.weakness_class == weakness_class]


class AttackMapper(Role):
    name = "attack-mapper"


class Remediator(Role):
    name = "remediator"


class SelfImprover(Role):
    name = "self-improver"

    def propose_rules(self, rule_gaps, tick: int) -> List[str]:
        """§6.5 — turn each rule-gap entry into a proposed new detection rule.
        This is the flywheel: exploratory lessons become reusable rules."""
        self.heartbeat()
        proposals = [
            f"propose rule for {g.weakness_class}: {g.pattern}" for g in rule_gaps]
        self.emit(tick, "self-improve", f"proposed {len(proposals)} new rule(s)")
        return proposals
