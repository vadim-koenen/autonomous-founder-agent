import json
import re
import unittest
from pathlib import Path

from founder_agent.channels import load_channels, plan_channel_action


ROOT = Path(__file__).resolve().parents[1]


class M3SafetyTest(unittest.TestCase):
    def setUp(self):
        registry = json.loads((ROOT / "data" / "channel_registry.json").read_text(encoding="utf-8"))
        self.channels = load_channels(registry)

    def test_human_identity_action_is_blocked(self):
        action = plan_channel_action(
            action_id="identity-test",
            experiment_id="m3-test",
            description="Open and verify a seller account.",
            channel_id="contra",
            authority_class="human_identity_required",
            channels=self.channels,
        )

        self.assertFalse(action.executable_now)
        self.assertIn("identity", action.blocked_reason.lower())

    def test_missing_channel_cannot_fabricate_execution(self):
        action = plan_channel_action(
            action_id="missing-test",
            experiment_id="m3-test",
            description="Publish through an unknown marketplace.",
            channel_id="unknown_marketplace",
            authority_class="preauthorized_when_connected",
            channels=self.channels,
        )

        self.assertFalse(action.executable_now)
        self.assertIn("not present", action.blocked_reason.lower())

    def test_channel_registry_covers_all_required_channel_kinds(self):
        kinds = {kind for channel in self.channels.values() for kind in channel.kinds}
        self.assertTrue(
            {
                "discovery",
                "distribution",
                "marketplace",
                "human_payment",
                "agent_native_payment",
                "publishing",
                "fulfillment",
            }.issubset(kinds)
        )

    def test_operator_does_not_import_static_strategy_library(self):
        operator_text = (ROOT / "founder_agent" / "operator.py").read_text(encoding="utf-8")
        self.assertNotIn("strategy_library", operator_text)
        self.assertNotIn("build_candidate_strategies", operator_text)

    def test_public_prospect_queue_records_no_contact_execution(self):
        queue = json.loads((ROOT / "data" / "prospect_queue.json").read_text(encoding="utf-8"))
        self.assertEqual(25, len(queue["prospects"]))
        self.assertIn("No messages", queue["outreach_status"])
        for prospect in queue["prospects"]:
            self.assertEqual("not_contacted", prospect["contact_status"])
            self.assertFalse(prospect["external_action_performed"])

    def test_operator_code_has_no_broker_or_transaction_execution_client(self):
        patterns = [
            r"\bimport\s+(alpaca|ccxt|web3|smtplib)\b",
            r"\bfrom\s+(alpaca|ccxt|web3)\b",
            r"\b(place_order|submit_order|send_transaction|mint_nft|send_email|send_dm)\s*\(",
            r"\brequests\.(post|put|patch|delete)\s*\(",
            r"\burlopen\([^\n]*data\s*=",
        ]
        for path in (ROOT / "founder_agent").glob("*.py"):
            text = path.read_text(encoding="utf-8")
            for pattern in patterns:
                self.assertIsNone(re.search(pattern, text, flags=re.IGNORECASE), f"{pattern} found in {path}")

        workflow = (ROOT / ".github" / "workflows" / "revenue-operator.yml").read_text(encoding="utf-8")
        self.assertNotIn("secrets.", workflow)
        self.assertNotIn("broker", workflow.lower())


if __name__ == "__main__":
    unittest.main()
