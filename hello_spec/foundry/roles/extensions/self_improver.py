"""Self-Improver (Foundry spec.md §6.5) — close the detection→prevention flywheel.

For each rule-gap the Detector recorded (a weakness class exploration found but no
rule caught), the Self-Improver authors a real CodeGuard rule and verifies it
catches the class on a fresh sweep. Proposals are written to a sandbox path for
human acceptance; the committed `rules/` corpus is never modified by the system
(Constitution X). A proposal is `verified` only after the re-scan demonstrates it
works (Constitution I).
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from ...lifecycle.models import RuleProposal
from ...rule_authoring import author_rule, template_for, verify_rule
from ...substrate.persistence import atomic_write_json, atomic_write_text
from ..base import Role


class SelfImprover(Role):
    name = "self-improver"

    def improve(self, rule_gaps, target_dir: Path, rules_dir: Path, index,
                sandbox, proposals_dir: Path, tick: int) -> List[RuleProposal]:
        self.heartbeat()
        target_dir, rules_dir, proposals_dir = map(
            Path, (target_dir, rules_dir, proposals_dir))
        deps = (self.llm, self.feed, self.log, self.liveness)

        proposals: List[RuleProposal] = []
        for gap in rule_gaps:
            authored = author_rule(gap.weakness_class)
            if not authored:
                self.log.discarded(f"rule-gap:{gap.weakness_class}",
                                   "no authoring template for this class")
                continue
            filename, markdown = authored
            path = proposals_dir / filename
            sandbox.check_write(str(path))            # Principle IX
            atomic_write_text(path, markdown)         # Principle XI

            verified = verify_rule(gap.finding_fingerprint, filename, markdown,
                                   target_dir, rules_dir, index, sandbox,
                                   proposals_dir, deps)
            t = template_for(gap.weakness_class)
            proposals.append(RuleProposal(
                weakness_class=gap.weakness_class, rule_id=t["rule_id"],
                filename=filename, matcher=t["matcher"], verified=verified,
                path=str(path)))

        index_path = proposals_dir / "proposals.json"
        if proposals:
            sandbox.check_write(str(index_path))
            atomic_write_json(index_path, [p.to_dict() for p in proposals])
        self.emit(tick, "self-improve",
                  f"authored {len(proposals)} rule(s); "
                  f"{sum(p.verified for p in proposals)} verified")
        return proposals
