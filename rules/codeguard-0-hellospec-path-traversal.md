---
description: Contain untrusted path components to prevent path traversal
languages:
- python
tags:
- web
alwaysApply: false
---

# File Handling — Path Traversal

Joining an untrusted path component to a base directory can escape that base
(`../../etc/passwd`).

## Secure pattern

- After resolving the candidate with `realpath`, verify it is contained within
  the intended base using `commonpath`, and reject otherwise.

```python
# SECURE
candidate = os.path.realpath(os.path.join(base_path, untrusted_path))
if os.path.commonpath([base_path, candidate]) != base_path:
    raise ValueError("Path traversal attempt")
```

This rule is high-recall: a function that already contains the containment
check above is a correct implementation, and the Triager should reject the
candidate as a false-positive after investigation.

## Detector contract (Foundry §5.4)

- id: codeguard-py-path-traversal
- severity: medium
- weakness_class: CWE-22
- matcher: path_traversal
