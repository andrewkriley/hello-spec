"""Detector (Foundry spec.md §5.4 / FR-037-049).

High-volume, low-precision candidate generation via four techniques:
  - FR-037 rule-based sweep (CodeGuard rules applied function-by-function);
  - FR-038 dependency scanning (known-vulnerable pinned dependencies);
  - FR-039 secret scanning (hardcoded credentials at module scope);
  - FR-040 exploratory hunting (free-form, finds what no rule covers).

The Detector writes only to the internal finding store, deduped by fingerprint
(FR-045), never to the issue tracker (FR-044). When exploration finds a class
no rule matched, a rule-gap entry is recorded (FR-042) — the seed's rule-gap
flywheel.

The matchers below are the deterministic, offline stand-in for the spec's
"LLM-evaluated detection rules": in a live deployment each would be a model
call; here they are checkable Python so the demo is reproducible (NFR-004).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from ..detection_rules import DetectionRule, load_rules
from ..lifecycle.models import Finding, FindingState
from ..substrate.finding_store import FindingStore
from .base import Role
from .indexer import CodeIndex, FuncInfo

# ---- matchers (FR-037): FuncInfo -> note string if the rule fires ----------

_SECRET_RE = re.compile(
    r"(sk_live_[A-Za-z0-9]+|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|"
    r"-----BEGIN[ A-Z]*PRIVATE KEY-----|"
    r"(?:password|secret|api_key|token)\s*=\s*['\"][^'\"]{6,}['\"])", re.I)


def _m_sql_string_format(fn: FuncInfo) -> Optional[str]:
    if not fn.reads_request:
        return None
    if re.search(r"\.execute\(\s*f[\"']", fn.source) or \
            re.search(r"\.execute\([^)]*%[^)]*\)", fn.source) or \
            re.search(r"\.execute\([^)]*\+[^)]*\)", fn.source):
        return "user input string-formatted into a SQL query"
    return None


def _m_shell_injection(fn: FuncInfo) -> Optional[str]:
    if fn.reads_request and "shell=True" in fn.source:
        return "request-controlled input passed to a shell with shell=True"
    return None


def _m_idor_no_authz(fn: FuncInfo) -> Optional[str]:
    # A DB/object fetch (db.get / .objects.get) keyed on client input, with no
    # ownership check. request.args.get(...) alone does NOT count as the sink.
    if fn.reads_request and re.search(r"\bdb[\w.]*\.get\(", fn.source) \
            and "current_user" not in fn.source \
            and not re.search(r"\bowner\b", fn.source):
        return "object fetched by client-supplied id with no ownership check"
    return None


def _m_path_traversal(fn: FuncInfo) -> Optional[str]:
    if "os.path.join(" in fn.source and \
            ("untrusted" in fn.source or "path" in fn.name.lower()):
        return "untrusted path component joined to a base path"
    return None


def _m_hardcoded_secret_fn(fn: FuncInfo) -> Optional[str]:
    if _SECRET_RE.search(fn.source):
        return "hardcoded credential in function body"
    return None


MATCHERS: Dict[str, Callable[[FuncInfo], Optional[str]]] = {
    "sql_string_format": _m_sql_string_format,
    "shell_injection": _m_shell_injection,
    "idor_no_authz": _m_idor_no_authz,
    "path_traversal": _m_path_traversal,
    "hardcoded_secret_fn": _m_hardcoded_secret_fn,
}

# Tiny known-vulnerable dependency table (FR-038 stand-in).
KNOWN_BAD_DEPS = {"requests": ("2.19.0", "CVE-2018-18074")}


@dataclass
class RuleGap:
    finding_fingerprint: str
    weakness_class: str
    pattern: str


@dataclass
class DetectionResult:
    candidates: List[Finding] = field(default_factory=list)
    rule_gaps: List[RuleGap] = field(default_factory=list)


class Detector(Role):
    name = "detector"

    def detect(self, index: CodeIndex, target_dir: Path, rules_dir: Path,
               store: FindingStore, tick: int) -> DetectionResult:
        self.heartbeat()
        rules = load_rules(rules_dir)
        result = DetectionResult()

        # FR-037: rule sweep, function-by-function (module-level vars are not
        # functions; module-scope secrets are handled by the secret scanner).
        # Two modes share the same candidate-creation path:
        #   stub  -> deterministic matchers (reproducible; used by tests, NFR-004)
        #   cli/api -> the model evaluates the rules against each function, one
        #              call per function (FR-037 "LLM-evaluated detection rules").
        use_llm = self.llm.backend in ("cli", "api")
        for fn in index.all():
            if fn.is_module_var:
                continue
            hits = (self._llm_sweep(fn, rules) if use_llm
                    else self._deterministic_sweep(fn, rules))
            for rule, note in hits:
                self._add(store, result, Finding(
                    path=fn.file, symbol=fn.name,
                    weakness_class=rule.weakness_class,
                    title=f"{rule.weakness_class} in {fn.name}",
                    description=note, technique=f"rule:{rule.id}"))

        # FR-039: secret scanning at module scope (not inside a function).
        self._secret_scan(target_dir, store, result)
        # FR-038: dependency scanning.
        self._dependency_scan(target_dir, store, result)
        # FR-040: exploratory hunting + FR-042 rule-gap.
        self._explore(index, rules, store, result)

        self.emit(tick, "detect",
                  f"{len(result.candidates)} candidate(s); "
                  f"{len(result.rule_gaps)} rule-gap(s)")
        return result

    def _add(self, store, result, finding) -> None:
        if store.upsert(finding):              # FR-045 dedup by fingerprint
            result.candidates.append(finding)

    # -- rule sweep modes --------------------------------------------------
    def _deterministic_sweep(self, fn, rules):
        """Stub mode: run each rule's checkable matcher. Returns [(rule, note)]."""
        hits = []
        for rule in rules:
            matcher = MATCHERS.get(rule.matcher)
            note = matcher(fn) if matcher else None
            if note:
                hits.append((rule, note))
        return hits

    def _llm_sweep(self, fn, rules):
        """cli/api mode: one model call evaluates ALL candidate rules against this
        function and returns which genuinely apply. Falls back to the
        deterministic matchers on any model/parse error so a flaky call never
        drops a function silently."""
        by_id = {r.id: r for r in rules}
        catalogue = "\n".join(
            f"- {r.id} ({r.weakness_class}): {r.description}" for r in rules)
        prompt = (
            f"Function `{fn.name}` in {fn.file}:\n```python\n{fn.source}\n```\n\n"
            f"Candidate weakness rules:\n{catalogue}\n\n"
            "Decide which rules GENUINELY apply to THIS function (the function "
            "actually exhibits that weakness). Be precise; do not flag a rule "
            "that does not apply. Respond with ONLY a JSON array: "
            '[{"id":"<rule id>","note":"<=12 words why"}]. Empty [] if none.')
        try:
            raw = self.llm.complete(
                self.name,
                "You are a precise security code detector. Output only JSON.",
                prompt)
            data = self._parse_json_array(raw)
            if data is None:
                self.log.discarded(f"llm-detect:{fn.name}", "unparseable response")
                return self._deterministic_sweep(fn, rules)
            hits = []
            for item in data:
                rule = by_id.get(str(item.get("id", "")).strip())
                if rule:
                    hits.append((rule, str(item.get("note", ""))[:120]))
            return hits
        except Exception as exc:               # never crash the fleet on one call
            self.log.discarded(f"llm-detect:{fn.name}", f"error: {exc}")
            return self._deterministic_sweep(fn, rules)

    @staticmethod
    def _parse_json_array(raw: str):
        txt = raw.strip()
        if txt.startswith("```"):
            txt = re.sub(r"^```[a-zA-Z]*\n?", "", txt).rstrip("`").strip()
        try:
            out = json.loads(txt)
        except Exception:
            i, j = txt.find("["), txt.rfind("]")
            if 0 <= i < j:
                try:
                    out = json.loads(txt[i:j + 1])
                except Exception:
                    return None
            else:
                return None
        return out if isinstance(out, list) else None

    def _secret_scan(self, target_dir, store, result) -> None:
        for py in sorted(Path(target_dir).rglob("*.py")):
            rel = str(py.relative_to(target_dir))
            for i, line in enumerate(py.read_text().splitlines(), start=1):
                m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*", line)
                if m and _SECRET_RE.search(line):
                    self._add(store, result, Finding(
                        path=rel, symbol=m.group(1), weakness_class="CWE-798",
                        title=f"Hardcoded credential {m.group(1)}",
                        description=f"module-scope secret at {rel}:{i}",
                        technique="secret-scan"))

    def _dependency_scan(self, target_dir, store, result) -> None:
        req = Path(target_dir) / "requirements.txt"
        if not req.exists():
            return
        for line in req.read_text().splitlines():
            if "==" in line:
                pkg, ver = (p.strip() for p in line.split("==", 1))
                bad = KNOWN_BAD_DEPS.get(pkg)
                if bad and bad[0] == ver:
                    self._add(store, result, Finding(
                        path="requirements.txt", symbol=pkg,
                        weakness_class="CWE-1395",
                        title=f"Vulnerable dependency {pkg}=={ver}",
                        description=f"{pkg}=={ver} affected by {bad[1]}",
                        technique="dependency-scan"))

    def _explore(self, index, rules, store, result) -> None:
        covered = {r.weakness_class for r in rules}
        for fn in index.all():
            src = fn.source.lower()
            looks_like_secret_check = (
                fn.name.startswith(("check", "verify"))
                and "==" in fn.source
                and ("token" in src or "secret" in src)
                and "compare_digest" not in src
                and "hmac" not in src
            )
            if looks_like_secret_check:
                f = Finding(
                    path=fn.file, symbol=fn.name, weakness_class="CWE-208",
                    title=f"Timing-unsafe comparison in {fn.name}",
                    description="secret compared with == (non-constant-time)",
                    technique="exploratory")
                if store.upsert(f):
                    result.candidates.append(f)
                    if "CWE-208" not in covered:        # FR-042 rule-gap
                        result.rule_gaps.append(RuleGap(
                            f.fingerprint, "CWE-208",
                            "constant-time comparison of secrets/tokens"))
