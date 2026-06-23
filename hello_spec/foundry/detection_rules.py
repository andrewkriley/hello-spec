"""Detection-rule loader (Foundry spec.md §5.4 FR-037/FR-041).

Loads the CodeGuard-format rules from the rule corpus. Each rule keeps its
native CodeGuard frontmatter (description / languages / tags / alwaysApply) so
the real CodeGuard tooling validates and converts it unchanged, and adds a
`## Detector contract` section carrying the fields Foundry's Detector needs
(id, severity, weakness_class, matcher). The corpus is versioned independently
of the Detector code (FR-041): rules are data, matchers are code.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class DetectionRule:
    id: str
    description: str
    languages: List[str]
    tags: List[str]
    always_apply: bool
    severity: str
    weakness_class: str
    matcher: str
    path: str = ""
    contract: dict = field(default_factory=dict)


def _parse_frontmatter(text: str):
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    fm = yaml.safe_load(text[3:end]) or {}
    return fm, text[end + 4:]


_CONTRACT_RE = re.compile(r"##\s+Detector contract.*?\n(.*?)(?:\n##\s|\Z)", re.S)
_KV_RE = re.compile(r"^\s*-\s*([a-z_]+):\s*(.+?)\s*$", re.M)


def _parse_contract(body: str) -> dict:
    m = _CONTRACT_RE.search(body)
    if not m:
        return {}
    return {k: v for k, v in _KV_RE.findall(m.group(1))}


def load_rules(rules_dir: Path) -> List[DetectionRule]:
    rules: List[DetectionRule] = []
    for md in sorted(Path(rules_dir).glob("codeguard-*.md")):
        text = md.read_text(encoding="utf-8")
        fm, body = _parse_frontmatter(text)
        contract = _parse_contract(body)
        if not contract.get("matcher"):
            # A rule with no Detector contract (e.g. a pure guidance/always-on
            # rule) is still valid CodeGuard; it just contributes no matcher.
            continue
        rules.append(DetectionRule(
            id=contract.get("id", md.stem),
            description=fm.get("description", ""),
            languages=fm.get("languages") or [],
            tags=fm.get("tags") or [],
            always_apply=bool(fm.get("alwaysApply", False)),
            severity=contract.get("severity", "medium"),
            weakness_class=contract.get("weakness_class", "CWE-0"),
            matcher=contract["matcher"],
            path=str(md),
            contract=contract,
        ))
    return rules
