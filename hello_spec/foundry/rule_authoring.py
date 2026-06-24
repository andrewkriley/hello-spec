"""Rule authoring + verification for the rule-gap flywheel (Foundry §6.5).

Turns a recorded rule-gap into a real CodeGuard-format rule (valid frontmatter +
a Detector contract that references an existing matcher), then VERIFIES it by
adding it to a throwaway corpus and re-running the sweep — confirming the gap's
finding is now caught by a `rule:` technique (Foundry's "the next sweep catches
that whole class on the first pass").

The committed `rules/` corpus is never touched: the operator accepts a proposal
by copying it in (Constitution X). An accepted rule then validates under the real
CodeGuard tooling (`make build-rules`).
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Optional, Tuple

# Per weakness-class authoring templates. Each names a matcher that already
# exists in the Detector's MATCHERS registry, valid CodeGuard frontmatter
# (tags ∈ KNOWN_TAGS, real language), and a Detector contract.
RULE_TEMPLATES = {
    "CWE-208": {
        "rule_id": "codeguard-py-timing-comparison",
        "filename": "codeguard-0-hellospec-timing-comparison.md",
        "severity": "medium",
        "matcher": "timing_unsafe_compare",
        "tags": ["secrets"],
        "languages": ["python"],
        "description": "Use constant-time comparison for secrets and tokens",
        "title": "Constant-Time Comparison",
        "body": (
            "Comparing a secret or token with `==` leaks information through "
            "timing and is exploitable (CWE-208).\n\n"
            "## Secure pattern\n\n"
            "- Use a constant-time comparison such as `hmac.compare_digest`.\n\n"
            "```python\n# SECURE\nreturn hmac.compare_digest(provided, expected)\n```\n"),
    },
}


def template_for(weakness_class: str) -> Optional[dict]:
    return RULE_TEMPLATES.get(weakness_class)


def author_rule(weakness_class: str) -> Optional[Tuple[str, str]]:
    """Return (filename, markdown) for a gap's class, or None if no template."""
    t = template_for(weakness_class)
    if not t:
        return None
    md = (
        "---\n"
        f"description: {t['description']}\n"
        "languages:\n" + "".join(f"- {lang}\n" for lang in t["languages"]) +
        "tags:\n" + "".join(f"- {tag}\n" for tag in t["tags"]) +
        "alwaysApply: false\n"
        "---\n\n"
        f"# {t['title']}\n\n"
        f"{t['body']}\n"
        "## Detector contract (Foundry §5.4)\n\n"
        f"- id: {t['rule_id']}\n"
        f"- severity: {t['severity']}\n"
        f"- weakness_class: {weakness_class}\n"
        f"- matcher: {t['matcher']}\n")
    return t["filename"], md


def verify_rule(gap_fingerprint: str, filename: str, markdown: str,
                target_dir: Path, rules_dir: Path, index, sandbox,
                work_dir: Path, deps) -> bool:
    """Add the proposed rule to a temp copy of the corpus, re-run detection over
    the target, and return whether the gap's finding is now caught by a rule."""
    from .roles.detector import Detector            # local import avoids a cycle
    from .substrate.finding_store import FindingStore

    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(dir=str(work_dir), prefix="corpus-"))
    try:
        sandbox.check_write(str(tmp))                # Principle IX
        corpus = tmp / "rules"
        shutil.copytree(rules_dir, corpus)
        (corpus / filename).write_text(markdown, encoding="utf-8")

        store = FindingStore()
        result = Detector("si-detector", *deps).detect(
            index, target_dir, corpus, store, 0)
        return any(c.fingerprint == gap_fingerprint and c.technique.startswith("rule:")
                   for c in result.candidates)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
