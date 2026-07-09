import unittest
from datetime import date
from pathlib import Path

from founder_agent.m1 import run_m1_decision_system
from founder_agent.models import ExternalActionRequest, LaunchActionType
from founder_agent.safety import ExternalActionBlocked, assert_m1_can_only_plan


class SafetyBoundaryTest(unittest.TestCase):
    def test_m1_blocks_external_action_execution(self):
        action = ExternalActionRequest(
            action_type=LaunchActionType.POST_PUBLICLY,
            description="Post launch copy.",
            approval_required=True,
            performed=False,
        )
        with self.assertRaises(ExternalActionBlocked):
            assert_m1_can_only_plan(action)

    def test_generated_run_marks_no_external_actions_performed(self):
        run = run_m1_decision_system(as_of=date(2026, 7, 9))
        all_actions = list(run.launch_plan.external_actions_required)
        for scored in run.scored_candidates:
            all_actions.extend(scored.strategy.external_actions_required)

        self.assertTrue(all_actions)
        for action in all_actions:
            self.assertTrue(action.approval_required)
            self.assertFalse(action.performed)

    def test_package_does_not_import_external_execution_clients(self):
        root = Path(__file__).resolve().parents[1] / "founder_agent"
        banned_snippets = [
            "import requests",
            "import httpx",
            "import smtplib",
            "from web3",
            "import web3",
            "stripe.",
            "place_order",
            "submit_order",
        ]
        for path in root.glob("*.py"):
            text = path.read_text(encoding="utf-8").lower()
            for snippet in banned_snippets:
                self.assertNotIn(snippet, text, f"{snippet} found in {path}")


if __name__ == "__main__":
    unittest.main()
