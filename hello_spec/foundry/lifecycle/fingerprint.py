"""Finding fingerprint (Foundry spec.md §7.5 / FR-090, Constitution VIII).

Identity is structural: (normalized path, symbol, vulnerability class).
Line numbers and code snippets are deliberately excluded so the fingerprint
survives edits to a function body and changes only when the function is
moved, renamed, or reclassified.
"""
from __future__ import annotations

import hashlib
import posixpath


def normalize_path(path: str) -> str:
    """Normalize separators and redundant components so the same logical file
    fingerprints identically regardless of how it was referenced."""
    p = path.replace("\\", "/").strip()
    while p.startswith("./"):
        p = p[2:]
    return posixpath.normpath(p)


def fingerprint(path: str, symbol: str, weakness_class: str) -> str:
    key = "|".join((normalize_path(path), symbol.strip(), weakness_class.strip().upper()))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
