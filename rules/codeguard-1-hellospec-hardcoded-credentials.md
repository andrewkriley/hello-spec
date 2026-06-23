---
description: No Hardcoded Credentials
languages: []
tags:
- secrets
alwaysApply: true
---

# No Hardcoded Credentials

NEVER store secrets, passwords, API keys, tokens, or other credentials directly
in source code. Treat the codebase as public and untrusted: any credential that
appears in source is compromised.

## Secure pattern

- Read secrets from the environment or a secrets manager at runtime.
- Keep secret *references* (not literals) in configuration.
- Add high-entropy and known-prefix patterns (`sk_live_`, `AKIA…`, `ghp_…`,
  `-----BEGIN … PRIVATE KEY-----`) to pre-commit and CI secret scanning.

## Detector contract (Foundry §5.4)

- id: codeguard-py-hardcoded-credential
- severity: high
- weakness_class: CWE-798
- matcher: hardcoded_secret_fn
