"""LLM-backed Detector rule sweep (FR-037) — tested without live calls by
injecting a fake adapter, so it stays deterministic and offline.
"""
from pathlib import Path

from conftest import make_role

from hello_spec.foundry.detection_rules import load_rules
from hello_spec.foundry.roles.detector import Detector
from hello_spec.foundry.roles.indexer import Indexer

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "target" / "vulnerable"
RULES = ROOT / "rules"


class _FakeLLM:
    def __init__(self, reply):
        self.backend = "cli"
        self._reply = reply

    def complete(self, role, system, prompt):
        return self._reply


def _sqli_fn(harness):
    index = make_role(Indexer, harness, "ix").build(TARGET, 1)
    return index.get("app.py", "handle_export"), load_rules(RULES)


def test_llm_sweep_maps_model_ids_to_rules(harness):
    det = make_role(Detector, harness, "det")
    det.llm = _FakeLLM('[{"id":"codeguard-py-sql-injection","note":"f-string SQL"}]')
    fn, rules = _sqli_fn(harness)
    hits = det._llm_sweep(fn, rules)
    assert [r.weakness_class for r, _ in hits] == ["CWE-89"]
    assert hits[0][1] == "f-string SQL"


def test_llm_sweep_handles_fenced_json(harness):
    det = make_role(Detector, harness, "det")
    det.llm = _FakeLLM('```json\n[{"id":"codeguard-py-sql-injection","note":"x"}]\n```')
    fn, rules = _sqli_fn(harness)
    assert [r.weakness_class for r, _ in det._llm_sweep(fn, rules)] == ["CWE-89"]


def test_llm_sweep_falls_back_on_garbage(harness):
    # Unparseable model output must fall back to the deterministic matchers,
    # which still catch the SQL injection — never a silent miss.
    det = make_role(Detector, harness, "det")
    det.llm = _FakeLLM("sorry, I can't help with that")
    fn, rules = _sqli_fn(harness)
    assert "CWE-89" in [r.weakness_class for r, _ in det._llm_sweep(fn, rules)]


def test_llm_sweep_empty_array_means_no_hits(harness):
    det = make_role(Detector, harness, "det")
    det.llm = _FakeLLM("[]")
    fn, rules = _sqli_fn(harness)
    assert det._llm_sweep(fn, rules) == []
