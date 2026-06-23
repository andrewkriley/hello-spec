---
description: Prevent OS command injection from untrusted input
languages:
- python
tags:
- web
alwaysApply: false
---

# OS Command Injection

Request-controlled input must never reach a shell.

## Secure pattern

- Use the argv (list) form of `subprocess` with `shell=False`.
- Prefer a library API over shelling out; if a shell is unavoidable, use a
  strict allowlist and never interpolate untrusted data.

```python
# SECURE
subprocess.run(["/bin/echo", cmd], shell=False)
```

## Detector contract (Foundry §5.4)

- id: codeguard-py-shell-injection
- severity: high
- weakness_class: CWE-78
- matcher: shell_injection
