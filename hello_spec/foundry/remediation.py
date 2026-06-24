"""Remediation core for the Remediator role (Foundry spec.md §6.4).

Holds the CWE -> secure-control map, the patch application helper, and the
isolated-copy verifier. The verifier is the linchpin (Constitution I/VII): a
candidate is only ever called `verified` after the patch is applied to a throwaway
copy and the real Detector re-confirms the finding's fingerprint is gone and no
new finding appeared — demonstrated, never asserted.

The control "templates" here are the project's own secure twin
(`target/secure/`), which is the documented end-state per class and is already
proven clean by `make scan-secure` (research decision D3).
"""
from __future__ import annotations

import difflib
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Set, Tuple

from .lifecycle.models import Finding, VerificationResult
from .roles.indexer import CodeIndex, Indexer
from .substrate.finding_store import FindingStore

# CWE -> human control id. Classes absent here have no mapped control.
CONTROL_MAP = {
    "CWE-89": "parameterized-query",
    "CWE-78": "argv-no-shell",
    "CWE-639": "ownership-check",
    "CWE-798": "env-secret",
}


def control_for(weakness_class: str) -> Optional[str]:
    return CONTROL_MAP.get(weakness_class)


def secure_symbol_source(secure_index: CodeIndex, rel_path: str,
                         symbol: str) -> Optional[str]:
    """The secure implementation of `symbol` at the same relative path, used as
    the control template. Returns None when the secure twin has no counterpart."""
    fn = secure_index.get(rel_path, symbol)
    return fn.source if fn else None


def apply_control(vuln_text: str, vuln_index: CodeIndex, finding: Finding,
                  secure_source: str) -> Tuple[str, str]:
    """Replace the finding's symbol span in `vuln_text` with `secure_source`.
    Returns (patched_text, unified_diff). The decorator line (if any) sits above
    the def line and is preserved."""
    fn = vuln_index.get(finding.path, finding.symbol)
    if not fn:
        return vuln_text, ""
    lines = vuln_text.splitlines()
    patched = lines[:fn.lineno - 1] + secure_source.splitlines() + lines[fn.end_lineno:]
    patched_text = "\n".join(patched) + ("\n" if vuln_text.endswith("\n") else "")
    diff = "\n".join(difflib.unified_diff(
        lines[fn.lineno - 1:fn.end_lineno], secure_source.splitlines(),
        fromfile=f"a/{finding.path}", tofile=f"b/{finding.path}", lineterm=""))
    return patched_text, diff


def verify_candidate(finding: Finding, target_dir: Path, rel_path: str,
                     patched_text: str, rules_dir: Path, sandbox, reports_dir: Path,
                     baseline_fingerprints: Set[str], deps) -> VerificationResult:
    """Write the patched copy to a sandbox-writable temp dir, re-run detection,
    and report whether the finding closed and whether anything new appeared.

    `deps` is (llm, feed, log, liveness) — the Role infrastructure the throwaway
    Indexer/Detector need. Detection is deterministic (matchers), so the verdict
    is reproducible regardless of LLM backend (NFR-004)."""
    from .roles.detector import Detector  # local import to avoid a cycle

    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(dir=str(reports_dir), prefix="verify-"))
    try:
        sandbox.check_write(str(tmp))                 # Principle IX: enforced
        dst = tmp / "target"
        shutil.copytree(target_dir, dst)
        patched_file = dst / rel_path
        patched_file.write_text(patched_text, encoding="utf-8")

        index = Indexer("rem-indexer", *deps).build(dst, 0)
        store = FindingStore()
        result = Detector("rem-detector", *deps).detect(
            index, dst, rules_dir, store, 0)
        new_fps = {c.fingerprint for c in result.candidates}
        return VerificationResult(
            finding_closed=finding.fingerprint not in new_fps,
            new_findings=len(new_fps - baseline_fingerprints))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
