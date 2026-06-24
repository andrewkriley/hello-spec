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


from .variant_hunter import VariantHunter   # §6.2 — fully implemented extension role


from .attack_mapper import AttackMapper   # §6.3 — fully implemented extension role


from .remediator import Remediator   # §6.4 — fully implemented extension role


from .self_improver import SelfImprover   # §6.5 — authors + verifies real rules
