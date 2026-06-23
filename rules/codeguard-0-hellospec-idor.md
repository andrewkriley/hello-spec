---
description: Enforce object-level authorization to prevent IDOR
languages:
- python
tags:
- web
alwaysApply: false
---

# Authorization — Insecure Direct Object Reference (IDOR)

An object fetched by a client-supplied identifier must be checked against the
caller's authorization before it is returned.

## Secure pattern

- After loading an object by id, verify the current principal owns or may access
  it; otherwise return 403/404.
- Prefer scoping queries to the caller (e.g. `WHERE owner = :current_user`).

```python
# SECURE
payment = db.get(payment_id)
if payment.get("owner") != current_user.id:
    return forbidden()
```

## Detector contract (Foundry §5.4)

- id: codeguard-py-idor
- severity: high
- weakness_class: CWE-639
- matcher: idor_no_authz
