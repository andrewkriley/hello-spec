"""Issue tracker binding (Foundry spec.md §11.1).

A concrete binding of the abstract "issue tracker" integration surface to the
local filesystem: findings are "published" as markdown issues under a reports
directory. Writes go through the Sandbox (Constitution IX), and updates are
keyed on fingerprint so a re-run updates rather than recreates (FR-090).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from ..governance.sandbox import Sandbox
from ..substrate.persistence import atomic_write_text


class FilesystemIssueTracker:
    def __init__(self, reports_dir: Path, sandbox: Sandbox) -> None:
        self.reports_dir = Path(reports_dir)
        self.sandbox = sandbox
        self._issues: Dict[str, Path] = {}

    def upsert_issue(self, fingerprint: str, title: str, body: str) -> Path:
        path = self.reports_dir / f"issue-{fingerprint}.md"
        self.sandbox.check_write(str(path))     # enforced, not advisory
        atomic_write_text(path, f"# {title}\n\n{body}\n")
        self._issues[fingerprint] = path
        return path

    def count(self) -> int:
        return len(self._issues)
