"""Atomic persistence (Foundry spec.md §8.6 / FR-106a, Constitution XI).

Every shared artifact is written completely to a temp file and then atomically
swapped into place via os.replace(). No reader ever observes a partially
written or deleted-but-not-yet-rewritten state. We never delete-then-write.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)   # atomic on POSIX/NTFS
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def atomic_write_json(path: Path, obj: Any) -> None:
    atomic_write_text(Path(path), json.dumps(obj, indent=2, sort_keys=True))
