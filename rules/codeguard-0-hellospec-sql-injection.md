---
description: Prevent SQL injection by never building queries from untrusted input
languages:
- python
tags:
- web
alwaysApply: false
---

# Input Validation — SQL Injection

User-controlled input must never be string-formatted into a SQL statement.

## Secure pattern

- Use parameterized queries / prepared statements: pass values as bind
  parameters, never via f-strings, `%`, `.format()`, or concatenation.
- Validate and constrain input types at the trust boundary.

```python
# SECURE
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

## Detector contract (Foundry §5.4)

- id: codeguard-py-sql-injection
- severity: high
- weakness_class: CWE-89
- matcher: sql_string_format
