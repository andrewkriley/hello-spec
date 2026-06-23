"""Reporter (Foundry spec.md §5.8 / FR-075-084).

The ONLY role that writes to the issue tracker (FR-044/FR-078). It surfaces
only findings that survived the gates (Constitution II): true-positives that
were confirmed/validated. It assigns severity against the operator's rubric
(§11.9) — the rule's severity was only a hint — produces a per-finding report,
publishes (update-not-recreate, keyed on fingerprint, FR-090), and writes an
evaluation rollup (FR-083).
"""
from __future__ import annotations

from typing import List

from ..integrations.issue_tracker import FilesystemIssueTracker
from ..lifecycle.labels import labels_for
from ..lifecycle.models import Finding, FindingState, Severity, Verdict
from .base import Role

# Operator severity rubric (§11.9): weakness class -> severity.
SEVERITY_RUBRIC = {
    "CWE-89": Severity.CRITICAL,    # SQL injection
    "CWE-78": Severity.CRITICAL,    # OS command injection
    "CWE-639": Severity.HIGH,       # IDOR
    "CWE-798": Severity.HIGH,       # hardcoded credentials
    "CWE-208": Severity.MEDIUM,     # timing-unsafe comparison
    "CWE-22": Severity.HIGH,        # path traversal
    "CWE-1395": Severity.MEDIUM,    # vulnerable dependency
}


class Reporter(Role):
    name = "reporter"

    def report(self, store, tracker: FilesystemIssueTracker, tick: int) -> str:
        self.heartbeat()
        published = 0
        for f in store.with_verdict(Verdict.TRUE_POSITIVE):
            f.severity = SEVERITY_RUBRIC.get(f.weakness_class, Severity.MEDIUM)
            f.labels = labels_for(f)
            tracker.upsert_issue(f.fingerprint, f.title, self._body(f))
            f.state = FindingState.PUBLISHED
            published += 1
        rollup = self._rollup(store, published)
        tracker.upsert_issue("rollup", "Evaluation rollup", rollup)
        self.emit(tick, "publish", f"published {published} issue(s) + rollup")
        return rollup

    def _body(self, f: Finding) -> str:
        legs = "\n".join(
            f"- **{c.leg}**: `{c.file}:{c.symbol}:{c.line}` — {c.note}"
            for c in f.evidence.legs())
        return (
            f"- fingerprint: `{f.fingerprint}`\n"
            f"- weakness: {f.weakness_class}\n"
            f"- severity: {f.severity.value if f.severity else 'n/a'}\n"
            f"- exploited: {f.exploited}\n"
            f"- technique: {f.technique}\n"
            f"- labels: {', '.join(f.labels)}\n\n"
            f"## Description\n{f.description}\n\n"
            f"## Evidence (gate passed)\n{legs}\n")

    def _rollup(self, store, published: int) -> str:
        lines = ["## Findings by verdict"]
        for v in Verdict:
            lines.append(f"- {v.value}: {len(store.with_verdict(v))}")
        lines.append("")
        lines.append(f"## Surfaced (published true-positives): {published}")
        exploited = sum(1 for f in store.surfaced() if f.exploited)
        lines.append(f"## Exploited: {exploited}")
        return "\n".join(lines)
