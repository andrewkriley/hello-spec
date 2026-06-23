"""Evaluation configuration (Foundry spec.md §12 / FR-126-129).

A single configuration document defines one evaluation. It carries every
section the spec requires: target, testbed, goals, rules, detection, fleet,
sandbox, budget, integrations. Secrets are NOT stored here (FR-127); they are
read from a separate env file. Configuration failures are named specifically
(FR-129).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

REQUIRED_SECTIONS = ["target", "goals", "rules", "fleet", "sandbox", "budget",
                     "integrations"]


class ConfigError(ValueError):
    pass


@dataclass
class EvalConfig:
    raw: Dict
    base_dir: Path

    @property
    def target(self) -> Dict:
        return self.raw["target"]

    @property
    def testbed(self) -> Optional[Dict]:
        tb = self.raw.get("testbed")
        return None if (tb in (None, "none", {})) else tb

    @property
    def goals(self) -> List[str]:
        return self.raw["goals"].get("attack_goals", [])

    @property
    def scope_exclude(self) -> List[str]:
        return self.target.get("exclude", [])

    @property
    def hard_rules(self) -> List[str]:
        return self.raw.get("rules", {}).get("hard_rules", [])

    @property
    def rules_dir(self) -> Path:
        return (self.base_dir / self.raw["detection"]["corpus"]).resolve()

    def section(self, name: str) -> Dict:
        return self.raw.get(name, {})


def load_config(path: Path) -> EvalConfig:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"config file not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"config is not valid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("config root must be a mapping")
    missing = [s for s in REQUIRED_SECTIONS if s not in raw]
    if missing:
        raise ConfigError(f"config missing required section(s): {missing}")
    # FR-127: secrets must not live in the config document.
    _reject_inline_secrets(raw)
    return EvalConfig(raw=raw, base_dir=path.parent)


def _reject_inline_secrets(raw: Dict) -> None:
    integrations = raw.get("integrations", {})
    for surface, binding in integrations.items():
        if isinstance(binding, dict):
            for k, v in binding.items():
                if isinstance(v, str) and k.lower() in ("api_key", "token",
                                                        "password", "secret"):
                    raise ConfigError(
                        f"inline secret in integrations.{surface}.{k} "
                        f"(FR-127: use a secret reference, not a literal)")
