"""Engine — wires the substrate, governance, roles and observability into one
evaluation run (Foundry spec.md §4 overview; orchestration per §5.1).

This is the deterministic, end-to-end "hello world": it indexes a target,
maps it, sweeps it with CodeGuard rules, triages through the evidence gate,
validates against a testbed, tracks coverage, and reports — honouring every
constitutional principle along the way. Run it with:

    python -m hello_spec.foundry.engine --config config/evaluation.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .config import EvalConfig, load_config
from .governance.budget import Budget
from .governance.sandbox import Sandbox
from .governance.scope_rules import system_prompt_block
from .governance.yield_stop import YieldGovernor, finding_weight
from .llm.adapter import LLMAdapter, resolve_backend
from .observability import dashboard
from .observability.activity_feed import ActivityFeed
from .observability.session_log import SessionLog
from .roles.cartographer import Cartographer
from .roles.coverage_guide import CoverageGuide
from .roles.detector import Detector
from .roles.extensions import (AttackMapper, DeepTester, Remediator,
                               SelfImprover, VariantHunter)
from .roles.indexer import Indexer
from .roles.orchestrator import Orchestrator
from .roles.reporter import Reporter
from .roles.triager import Triager
from .roles.validator import Validator
from .integrations.issue_tracker import FilesystemIssueTracker
from .substrate.finding_store import FindingStore
from .substrate.liveness import LivenessRegistry
from .substrate.notes import SharedNotes
from .substrate.work_queue import Task, WorkQueue


def run_evaluation(config_path: Path, backend: Optional[str] = None,
                   target_override: Optional[str] = None) -> Dict:
    cfg = load_config(config_path)
    return _run(cfg, backend, target_override)


def _run(cfg: EvalConfig, backend: Optional[str], target_override: Optional[str]) -> Dict:
    base = cfg.base_dir
    out_dir = (base / cfg.section("integrations").get("artifacts_dir", "build/run")).resolve()
    reports_dir = (base / cfg.section("integrations").get("reports_dir", "build/reports")).resolve()

    # -- governance: sandbox + budget (§9) --------------------------------
    sb_cfg = cfg.section("sandbox")
    sandbox = Sandbox(
        egress_allowlist=sb_cfg.get("egress_allowlist", ["localhost"]),
        writable_paths=[str(out_dir), str(reports_dir)],
        readonly_paths=[str((base / cfg.target["root"]).resolve())])
    b_cfg = cfg.section("budget")
    budget = Budget(spend_cap=b_cfg.get("spend_cap"), time_cap=b_cfg.get("time_cap"))
    governor = YieldGovernor(
        threshold=b_cfg.get("yield_threshold", 0.5),
        window=b_cfg.get("yield_window", 5),
        min_runtime=b_cfg.get("min_runtime", 1))

    degradations: List[str] = []
    warn = budget.preflight_warning()
    if warn:
        degradations.append(warn)

    # -- llm adapter with the backend toggle (§11.2) ----------------------
    chosen = resolve_backend(backend or cfg.section("integrations")
                             .get("llm", {}).get("backend"))
    model = cfg.section("integrations").get("llm", {}).get("model", "claude-opus-4-8")
    llm = LLMAdapter(chosen, sandbox, budget, model=model)

    # -- substrate (§8) ----------------------------------------------------
    liveness = LivenessRegistry(stale_after=2)
    queue = WorkQueue(liveness)
    store = FindingStore(path=out_dir / "findings.json")
    notes = SharedNotes()
    feed = ActivityFeed()
    log = SessionLog(path=out_dir / "session.log.jsonl")

    def role(cls, suffix):
        return cls(f"{suffix}-1", llm, feed, log, liveness)

    orch = role(Orchestrator, "orch")
    indexer = role(Indexer, "indexer")
    carto = role(Cartographer, "carto")
    detector = role(Detector, "detector")
    triager = role(Triager, "triager")
    validator = role(Validator, "validator")
    coverage_guide = role(CoverageGuide, "coverage")
    reporter = role(Reporter, "reporter")
    self_improver = role(SelfImprover, "improver")

    # Hard-rules block injected into every agent's system prompt (§9.2).
    hard_block = system_prompt_block(cfg.hard_rules, cfg.goals)
    log.record(event="system-prompt-hard-rules", block=hard_block)
    orch.post_message("info", f"backend={chosen}; goals={len(cfg.goals)}")

    # -- evaluation pipeline ----------------------------------------------
    target_root = Path(target_override) if target_override \
        else (base / cfg.target["root"]).resolve()

    tick = liveness.tick()
    for r in (orch, indexer, carto, detector, triager, validator,
              coverage_guide, reporter):
        r.heartbeat()

    index = indexer.build(target_root, tick)
    indexer.persist(index, out_dir / "index.json")
    if not index.files:
        degradations.append("index is empty: target has no indexable files")

    smap = carto.map(index, cfg.goals, tick)
    cov = coverage_guide.build_checklist(cfg.goals, tick)

    # Demonstrate the work queue: one task per pipeline phase, atomically
    # claimed and completed (§8.1).
    for i, phase in enumerate(["detect", "triage", "validate", "report"]):
        queue.add(Task(id=phase, title=phase, description=f"phase {phase}",
                       priority=i))
    claimed = queue.claim(detector.agent_id)

    rules_dir = cfg.rules_dir
    if not rules_dir.exists() or not list(rules_dir.glob("codeguard-*.md")):
        degradations.append(f"detection corpus missing at {rules_dir}")
    det = detector.detect(index, target_root, rules_dir, store, tick)
    if claimed:
        queue.complete(claimed.id)
    notes.append(detector.agent_id,
                 f"swept {len(index.all())} symbols across {len(index.files)} files")

    tick = liveness.tick()
    for r in (triager, validator, reporter):
        r.heartbeat()
    triager.triage(store, index, target_root, cfg.scope_exclude, tick)
    validator.validate(store, cfg.testbed, tick)

    # Coverage-complete only after every goal has been credibly attempted (§5.7).
    coverage_guide.attempt_all(cov, tick)

    # Yield sample for the auto-stop governor (§9.4).
    weighted = sum(finding_weight(f) for f in store.all())
    governor.sample(weighted, max(budget.spend, 1e-6))
    budget.tick()
    auto_stop = governor.should_stop(cov.complete, budget.runtime)

    rollup = reporter.report(store, FilesystemIssueTracker(reports_dir, sandbox), tick)
    # §6.5 Self-Improver: author + verify a real CodeGuard rule per rule-gap
    # (the detection→prevention flywheel). Proposals are written for human
    # acceptance; the committed rules/ corpus is never modified.
    proposals = self_improver.improve(
        det.rule_gaps, target_root, rules_dir, index, sandbox,
        reports_dir / "proposals", tick)

    # §6.4 Remediator (opt-in extension): propose + verify candidate fixes.
    remediations = []
    rem_cfg = cfg.section("fleet").get("remediator", {})
    if rem_cfg.get("enabled"):
        remediator = role(Remediator, "remediator")
        secure_dir = (base / rem_cfg.get("reference_dir", "../target/secure")).resolve()
        remediations = remediator.remediate(store, index, target_root, rules_dir,
                                            sandbox, reports_dir, secure_dir, tick)

    # §6.2 Variant-Hunter (opt-in extension): leads for siblings of confirmed bugs.
    variants = []
    if cfg.section("fleet").get("variant_hunter", {}).get("enabled"):
        variant_hunter = role(VariantHunter, "variant-hunter")
        variants = variant_hunter.hunt(store, sandbox, reports_dir, tick)

    # §6.3 Attack-Mapper (opt-in extension): chain findings into attack paths.
    attack_paths = []
    if cfg.section("fleet").get("attack_mapper", {}).get("enabled"):
        attack_mapper = role(AttackMapper, "attack-mapper")
        attack_paths = attack_mapper.map_attacks(store, sandbox, reports_dir, tick)

    # §6.1 Deep-Tester (opt-in extension): fuzz a runnable entry point.
    deep_test = []
    if cfg.section("fleet").get("deep_tester", {}).get("enabled"):
        deep_tester = role(DeepTester, "deep-tester")
        deep_test = deep_tester.fuzz(target_root, sandbox, reports_dir, tick)

    store.persist()
    log.record(event="status", **orch.status(store))
    log.persist()

    agents = {r.agent_id: ("alive" if liveness.is_alive(r.agent_id) else "stale")
              for r in (orch, indexer, carto, detector, triager, validator,
                        coverage_guide, reporter, self_improver)}

    board = dashboard.render(store, queue, budget, governor, cov.as_dict(),
                             agents, orch.messages_as_dicts(), degradations)

    return {
        "config": str(config_path_of(cfg)),
        "backend": chosen,
        "dashboard": board,
        "rollup": rollup,
        "findings": [f.to_dict() for f in store.all()],
        "surfaced": [f.fingerprint for f in store.surfaced()],
        "rule_gaps": [g.weakness_class for g in det.rule_gaps],
        "rule_proposals": [p.to_dict() for p in proposals],
        "remediations": [c.to_dict() for c in remediations],
        "variants": [v.to_dict() for v in variants],
        "attack_paths": [p.to_dict() for p in attack_paths],
        "deep_test": [d.to_dict() for d in deep_test],
        "coverage_complete": cov.complete,
        "auto_stop": auto_stop,
        "security_map": {
            "entry_points": smap.entry_points,
            "trust_boundaries": smap.trust_boundaries},
        "status": orch.status(store),
        "degradations": degradations,
    }


def config_path_of(cfg: EvalConfig) -> Path:
    return cfg.base_dir


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="hello-spec Foundry mini-engine")
    parser.add_argument("--config", default="config/evaluation.yaml")
    parser.add_argument("--backend", default=None,
                        choices=[None, "stub", "cli", "api"])
    parser.add_argument("--target", default=None,
                        help="override the target root (e.g. point at target/secure)")
    args = parser.parse_args(argv)
    result = run_evaluation(Path(args.config), args.backend, args.target)
    print(result["dashboard"])
    print("\n--- evaluation rollup ---")
    print(result["rollup"])
    if result["rule_proposals"]:
        print("\n--- self-improver: authored CodeGuard rules (rule-gap flywheel) ---")
        for p in result["rule_proposals"]:
            tag = "verified" if p["verified"] else "unverified"
            print(f"  [{tag:<10}] {p['weakness_class']} -> {p['filename']} "
                  f"(matcher: {p['matcher']})")
    if result.get("remediations"):
        print("\n--- remediator candidate fixes (proposed, not applied) ---")
        for c in result["remediations"]:
            tail = c["control"] if c["status"] != "no-control" else c["reason"]
            print(f"  [{c['status']:<11}] {c['weakness_class']:<8} {tail}")
    if result.get("variants"):
        print("\n--- variant-hunter leads (same pattern found elsewhere) ---")
        for v in result["variants"]:
            print(f"  {v['weakness_class']:<8} also at {v['location']} "
                  f"[{v['verdict']}]")
    if result.get("attack_paths"):
        print("\n--- attack-mapper chains (foothold → impact) ---")
        for p in result["attack_paths"]:
            print(f"  {p['entry_class']} ({p['entry_location']}) → "
                  f"{p['impact_class']} ({p['impact_location']})")
    if result.get("deep_test"):
        print("\n--- deep-tester crashes (found by running the code) ---")
        for d in result["deep_test"]:
            print(f"  {d['crash_type']:<12} in {d['entry_point']} "
                  f"on input {d['sample_input']!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
