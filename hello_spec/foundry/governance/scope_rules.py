"""Operator scope / hard rules (Foundry spec.md §9.2 / FR-110-111).

The operator's hard-rules block is injected verbatim into every agent's system
prompt as defence-in-depth. It is NOT the enforcement layer (that is the
sandbox, Constitution IX) but it tells the model the boundaries it must
respect. Default hard rules apply when the testbed is not disposable.
"""
from __future__ import annotations

from typing import List

DEFAULT_HARD_RULES: List[str] = [
    "Do NOT perform denial-of-service or load/stress testing.",
    "Do NOT delete or modify data on the target or testbed.",
    "Do NOT change credentials or account state.",
    "Do NOT affect users or systems outside the declared scope.",
]


def system_prompt_block(hard_rules: List[str], scope: List[str]) -> str:
    rules = hard_rules or DEFAULT_HARD_RULES
    lines = ["## Hard rules (non-negotiable)"]
    lines += [f"- {r}" for r in rules]
    if scope:
        lines.append("## In scope")
        lines += [f"- {s}" for s in scope]
    return "\n".join(lines)
