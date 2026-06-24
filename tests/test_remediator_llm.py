"""Remediator LLM patch generation (cli/api) — tested without live calls via a
fake adapter. The model proposes the fix; the re-scan still decides (Constitution I).
"""
from pathlib import Path

from conftest import make_role

from hello_spec.foundry.governance.sandbox import Sandbox
from hello_spec.foundry.lifecycle.models import RemediationStatus, Verdict
from hello_spec.foundry.roles.detector import Detector
from hello_spec.foundry.roles.extensions import Remediator
from hello_spec.foundry.roles.indexer import Indexer
from hello_spec.foundry.substrate.finding_store import FindingStore

ROOT = Path(__file__).resolve().parents[1]
VULN = ROOT / "target" / "vulnerable"
SECURE = ROOT / "target" / "secure"
RULES = ROOT / "rules"


class _FakeLLM:
    def __init__(self, code):
        self.backend = "cli"
        self._code = code

    def complete(self, role, system, prompt):
        return self._code


def _setup(harness):
    index = make_role(Indexer, harness, "ix").build(VULN, 1)
    secure_index = make_role(Indexer, harness, "ixs").build(SECURE, 1)
    store = FindingStore()
    make_role(Detector, harness, "det").detect(index, VULN, RULES, store, 1)
    sqli = next(f for f in store.all()
                if f.weakness_class == "CWE-89" and f.symbol == "handle_export")
    sqli.verdict = Verdict.TRUE_POSITIVE
    baseline = {f.fingerprint for f in store.all()}
    return index, secure_index, sqli, baseline


def _remediate(harness, tmp_path, fake_code):
    index, secure_index, sqli, baseline = _setup(harness)
    rem = make_role(Remediator, harness, "rem")
    rem.llm = _FakeLLM(fake_code)
    sandbox = Sandbox(["localhost"], writable_paths=[str(tmp_path)], readonly_paths=[])
    deps = (rem.llm, harness["feed"], harness["log"], harness["liveness"])
    return rem._remediate_one(sqli, index, VULN, secure_index, RULES, sandbox,
                              tmp_path, baseline, deps)


def test_llm_generated_patch_is_verified(harness, tmp_path):
    # A competent "model": returns the secure rewrite of handle_export.
    secure_code = make_role(Indexer, harness, "ixc").build(SECURE, 1) \
        .get("app.py", "handle_export").source
    cand = _remediate(harness, tmp_path, secure_code)
    assert cand.generated_by == "llm"
    assert cand.status == RemediationStatus.VERIFIED


def test_unparseable_llm_patch_falls_back_to_template(harness, tmp_path):
    # Garbage from the model -> the LLM attempt is dropped, the secure-twin
    # template takes over, and the result still verifies.
    cand = _remediate(harness, tmp_path, "this is not valid python !!!")
    assert cand.generated_by == "template"
    assert cand.status == RemediationStatus.VERIFIED
