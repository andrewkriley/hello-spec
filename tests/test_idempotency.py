"""NFR-002 (Idempotency) + FR-045 (dedup by fingerprint).

Re-running detection over unchanged input produces zero new findings: the
finding store deduplicates by fingerprint.
"""
from pathlib import Path

from conftest import make_role

from hello_spec.foundry.roles.detector import Detector
from hello_spec.foundry.roles.indexer import Indexer
from hello_spec.foundry.substrate.finding_store import FindingStore

TARGET = Path(__file__).resolve().parents[1] / "target" / "vulnerable"
RULES = Path(__file__).resolve().parents[1] / "rules"


def test_second_detection_pass_adds_nothing(harness):
    indexer = make_role(Indexer, harness, "indexer-1")
    detector = make_role(Detector, harness, "detector-1")
    index = indexer.build(TARGET, tick=1)
    store = FindingStore()

    first = detector.detect(index, TARGET, RULES, store, tick=1)
    assert first.candidates, "first pass should find candidates"

    second = detector.detect(index, TARGET, RULES, store, tick=2)
    assert second.candidates == [], "re-run must add zero new findings (NFR-002)"
