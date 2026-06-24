# CodeGuard security review — hello-spec engine

**Date**: 2026-06-24
**Scope**: `hello_spec/**` (the Python engine, 40 modules) + `scripts/build_rules.sh`.
**Excluded** (intentional fixtures, read for context only): `target/vulnerable/**`
(deliberately insecure teaching data) and `target/secure/**`.
**Rules applied**: CodeGuard always-apply rules (hardcoded-credentials, crypto,
digital-certificates) + context rules (input-validation/injection, file-handling,
logging, privacy, supply-chain) + the Python language rules + this repo's `rules/`.
**Method**: CodeGuard `security-review` methodology (see
[`docs/METHODOLOGY.md`](METHODOLOGY.md) — this is the **Gate B** review of the
implementation, run as a worked example over the existing engine).

## Summary

The engine consistently applies secure-by-default patterns: subprocess uses the
argv form with `shell=False`, YAML is parsed with `yaml.safe_load`, secrets come
only from environment variables (and config-load actively *rejects* inline
secrets), filesystem writes and network egress are forced through a Sandbox
chokepoint, and shared artifacts use atomic temp-file + `os.replace` writes. No
`eval`/`exec`/`pickle`/unsafe `yaml.load`/`os.system`/`shell=True`/string-built
SQL exists in product code; no real hardcoded secrets, weak security crypto, or
certificate handling.

**Counts**: Critical 0 · High 0 · Medium 0 · Low 0 · Info 0.

## Findings

**None.** The reviewed code follows the applicable CodeGuard controls. Evidence:

| Control (CodeGuard) | Observed secure pattern | Location |
|---|---|---|
| Command injection (CWE-78) | argv list, `shell=False`, exe via `shutil.which` | `llm/adapter.py:75,79-82` |
| Hardcoded credentials (CWE-798) | key from `os.environ`; config rejects inline secrets | `llm/adapter.py:96`, `config.py:77-86` |
| Unsafe deserialization | `yaml.safe_load`; no pickle/eval/exec | `config.py:64` |
| Path traversal / boundary (CWE-22) | `resolve()` + containment checks; writes/egress via sandbox | `governance/sandbox.py`, `remediation.py:78`, `integrations/issue_tracker.py:25` |
| Atomic/secure writes | mkstemp (0600) + fsync + `os.replace`, cleanup in `finally` | `substrate/persistence.py:16-28` |
| Temp handling | `mkdtemp` (0700) + `rmtree` in `finally` | `remediation.py:76` |
| Crypto | only `hashlib.sha256` for deterministic IDs (not a security control) | `llm/adapter.py:66` |
| Logging / privacy | structured turn/token metadata; no secrets logged | `observability/session_log.py` |

## Notes & non-issues

- **In-process Sandbox is a documented teaching simplification** (`sandbox.py:1-12`):
  it maps to container network policy + read-only mounts in a real deployment.
  It is an in-process chokepoint, not a kernel boundary — but every engine
  egress/write path *does* route through it, which is the intended design.
- **`cli` backend passes the full prompt (possibly derived from scanned target
  content) as an argv element** — intentional and safe under `shell=False`; the
  prompt is data, not a command boundary.
- **Detector regexes containing `sk_live_`, `AKIA`, `password=…`**
  (`roles/detector.py:35-37`) are the scanner's *detection patterns*, not secrets.
- **`scripts/build_rules.sh`** uses `set -euo pipefail`, quoted variables, and a
  `trap cleanup EXIT`; no untrusted input is interpolated into commands.

## Verdict

**CLEAN** — no changes required. The secure-coding controls the project teaches
are the ones it follows in its own engine.
