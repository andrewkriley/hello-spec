"""Operator dashboard (Foundry spec.md §10 / FR-120, FR-124-125).

Renders, from the substrate, the six widget classes the spec requires:
per-agent state, finding counts by verdict/severity/exploited, coverage state,
budget, yield, queue depth and operator messages. It reads the same substrate
the status query reads (FR-124), and prominently surfaces system degradation
(FR-125).
"""
from __future__ import annotations

from typing import Dict, List

from ..governance.budget import Budget
from ..governance.yield_stop import YieldGovernor
from ..lifecycle.models import Verdict
from ..substrate.finding_store import FindingStore
from ..substrate.work_queue import WorkQueue


def render(store: FindingStore, queue: WorkQueue, budget: Budget,
           governor: YieldGovernor, coverage: Dict, agents: Dict[str, str],
           operator_messages: List, degradations: List[str]) -> str:
    out: List[str] = []
    out.append("=" * 64)
    out.append("  HELLO-SPEC :: Foundry mini-engine — operator dashboard")
    out.append("=" * 64)

    if degradations:   # FR-125: surface degradation prominently, at the top
        out.append("!! SYSTEM DEGRADATION")
        for d in degradations:
            out.append(f"   - {d}")
        out.append("")

    out.append("Agents:")
    for aid, state in agents.items():
        out.append(f"   {aid:<16} {state}")

    out.append("")
    out.append("Findings by verdict:")
    for v in Verdict:
        out.append(f"   {v.value:<16} {len(store.with_verdict(v))}")
    sev: Dict[str, int] = {}
    exploited = 0
    for f in store.all():
        if f.verdict == Verdict.TRUE_POSITIVE:
            if f.severity:
                sev[f.severity.value] = sev.get(f.severity.value, 0) + 1
            if f.exploited:
                exploited += 1
    out.append("   by severity (true-positive): " +
               (", ".join(f"{k}={v}" for k, v in sorted(sev.items())) or "none"))
    out.append(f"   exploited: {exploited}")
    out.append(f"   surfaced (published): {len(store.surfaced())}")

    out.append("")
    out.append("Coverage:")
    out.append(f"   complete: {coverage.get('complete')}   "
               f"items: {coverage.get('done')}/{coverage.get('total')}")

    out.append("")
    out.append("Budget & yield:")
    cap = budget.spend_cap if budget.spend_cap is not None else "unset"
    tcap = budget.time_cap if budget.time_cap is not None else "unset"
    out.append(f"   spend: {budget.spend:.4f} / {cap}    "
               f"runtime: {budget.runtime} / {tcap}    "
               f"tokens: {budget.tokens}    backoff: {budget.backoff_level}")
    out.append(f"   trailing yield: {governor.trailing_yield():.3f} "
               f"(threshold {governor.threshold}, window "
               f"{'full' if governor.window_full() else 'filling'})")

    out.append("")
    out.append(f"Queue depth (open): {queue.open_depth()}")
    out.append("Operator messages:")
    for m in operator_messages:
        out.append(f"   [{m['kind']}] {m['text']}")
    out.append("")
    out.append("Per-role cost rollup:")
    for role, r in sorted(budget.per_role().items()):
        out.append(f"   {role:<14} calls={int(r['calls'])} "
                   f"tokens={int(r['tokens'])} cost={r['cost']:.4f}")
    out.append("=" * 64)
    return "\n".join(out)
