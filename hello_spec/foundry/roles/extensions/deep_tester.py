"""Deep-Tester (Foundry spec.md §6.1) — input-generation testing.

Generates a corpus of inputs and EXECUTES a runnable target entry point
(`parse_record` in `<target>/parser.py`) on each, reporting de-duplicated
crashes (one per exception type) with a representative input. This finds
robustness / improper-input-validation defects (CWE-20 / CWE-248) that static
rules can't see, because it runs the code.

Execution isolation (Constitution IX): the corpus runs in a SEPARATE process
with a timeout — target code never executes in the engine process. Here that is
a subprocess; a production deployment would containerize it (same posture as the
in-process Sandbox). The role never modifies the target; it writes its report
atomically through the sandbox (XI).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import List

from ...lifecycle.models import DeepTestFinding
from ...substrate.persistence import atomic_write_json
from ..base import Role

ENTRY_FUNCTION = "parse_record"

# A small, fixed corpus — valid plus systematic malformations. Fixed (not random)
# so crashes are deterministic and reproducible (NFR-004).
CORPUS = ["id=1", "id=42", "", "id=", "id=abc", "nope", "a=b=c", "x" * 64]

# The child-process fuzz runner: imports the target by path, runs the corpus
# through the entry function, and prints de-duplicated crashes as JSON. Target
# code executes HERE, in the child, never in the engine process.
_RUNNER = """
import importlib.util, json, sys
CORPUS = {corpus!r}
spec = importlib.util.spec_from_file_location("dt_target", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
fn = getattr(mod, {func!r}, None)
seen, out = set(), []
if fn is not None:
    for s in CORPUS:
        try:
            fn(s)
        except Exception as exc:
            ct = type(exc).__name__
            if ct not in seen:
                seen.add(ct)
                out.append({{"crash_type": ct, "sample_input": s}})
print(json.dumps(out))
"""


class DeepTester(Role):
    name = "deep-tester"

    def fuzz(self, target_dir: Path, sandbox, reports_dir: Path,
             tick: int) -> List[DeepTestFinding]:
        self.heartbeat()
        target_dir, reports_dir = Path(target_dir), Path(reports_dir)
        parser = target_dir / "parser.py"

        findings: List[DeepTestFinding] = []
        if parser.exists():                            # FR-006
            findings = self._run_corpus(parser)

        artifact = reports_dir / "deep-test.json"
        sandbox.check_write(str(artifact))             # Principle IX
        atomic_write_json(artifact, [f.to_dict() for f in findings])  # Principle XI
        self.emit(tick, "deep-test",
                  f"{len(findings)} distinct crash(es) from {len(CORPUS)} inputs")
        return findings

    def _run_corpus(self, parser: Path) -> List[DeepTestFinding]:
        runner = _RUNNER.format(corpus=CORPUS, func=ENTRY_FUNCTION)
        entry = f"{parser.name}::{ENTRY_FUNCTION}"
        try:
            # Isolated execution: argv form, shell=False, bounded by a timeout.
            proc = subprocess.run(
                [sys.executable, "-c", runner, str(parser)],
                capture_output=True, text=True, timeout=15)
        except subprocess.TimeoutExpired:              # FR-004 — a hang is bounded
            return [DeepTestFinding(entry_point=entry, crash_type="Timeout",
                                    sample_input="(corpus hung)")]
        try:
            crashes = json.loads(proc.stdout or "[]")
        except json.JSONDecodeError:
            self.log.discarded(f"deep-test:{entry}", "unparseable runner output")
            return []
        return [DeepTestFinding(entry_point=entry, crash_type=c["crash_type"],
                                sample_input=c["sample_input"]) for c in crashes]
