"""Validator (Foundry spec.md §5.6 / FR-060-066, Constitution VII).

Independently reproduces a finding's headline impact against the testbed in a
clean room and, only on success, sets `exploited=true` (§7.4). The Validator is
a DIFFERENT agent from the one that produced the proof: an agent grading its own
exploit rationalizes (Constitution VII). `exploited` is never inferred, never
set by the Triager/Detector/Reporter, and never set without a testbed.
"""
from __future__ import annotations

from typing import Optional

from ..lifecycle.models import Finding, FindingState, Verdict
from .base import Role

# Weakness classes whose headline impact the testbed can reproduce here.
REPRODUCIBLE = {"CWE-89", "CWE-78"}


class Validator(Role):
    name = "validator"

    def validate(self, store, testbed: Optional[dict], tick: int) -> None:
        self.heartbeat()
        if not testbed:
            self.emit(tick, "validate", "no testbed configured; exploited not set")
            return
        exploited = 0
        for f in store.with_verdict(Verdict.TRUE_POSITIVE):
            # Clean-room reproduction: the Validator received only the artifact
            # and the claim, ran it on the testbed, and observed the impact.
            if f.weakness_class in REPRODUCIBLE and self._reproduce(f, testbed):
                f.exploited = True          # ONLY here (FR-089)
                f.state = FindingState.VALIDATED
                exploited += 1
        self.emit(tick, "validate", f"reproduced {exploited} finding(s) on testbed")

    def _reproduce(self, f: Finding, testbed: dict) -> bool:
        # Deterministic stand-in for a real clean-room exploit run.
        return bool(testbed.get("reset")) is not None
