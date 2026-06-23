"""Shared test fixtures."""
import sys
from pathlib import Path

import pytest

# Ensure the repo root (containing the hello_spec package) is importable.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hello_spec.foundry.governance.budget import Budget          # noqa: E402
from hello_spec.foundry.governance.sandbox import Sandbox        # noqa: E402
from hello_spec.foundry.llm.adapter import LLMAdapter            # noqa: E402
from hello_spec.foundry.observability.activity_feed import ActivityFeed  # noqa: E402
from hello_spec.foundry.observability.session_log import SessionLog      # noqa: E402
from hello_spec.foundry.substrate.liveness import LivenessRegistry       # noqa: E402


@pytest.fixture
def harness():
    """Minimal role harness (sandboxed stub LLM, feed, log, liveness)."""
    sandbox = Sandbox(["localhost"], writable_paths=[], readonly_paths=[])
    budget = Budget()
    llm = LLMAdapter("stub", sandbox, budget)
    return {
        "llm": llm, "feed": ActivityFeed(), "log": SessionLog(),
        "liveness": LivenessRegistry(stale_after=2), "sandbox": sandbox,
        "budget": budget,
    }


def make_role(cls, harness, agent_id="a-1"):
    return cls(agent_id, harness["llm"], harness["feed"], harness["log"],
               harness["liveness"])
