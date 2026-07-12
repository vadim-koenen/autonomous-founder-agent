import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class M2ActivationTest(unittest.TestCase):
    def test_manifest_is_machine_readable_and_has_only_human_checkout_active(self):
        manifest = json.loads((ROOT / "AGENT_MANIFEST.json").read_text(encoding="utf-8"))
        state = json.loads((ROOT / "data" / "operator_state.json").read_text(encoding="utf-8"))

        self.assertEqual("autonomous_founder_agent_manifest", manifest["schema_name"])
        self.assertEqual("0.4", manifest["schema_version"])
        self.assertEqual("continuous_discovery_and_bounded_execution_active", manifest["operator"]["status"])
        self.assertEqual(3, len(manifest["current_portfolio"]))
        self.assertEqual(["stripe_payment_link"], manifest["payment_policy"]["active_rails"])
        self.assertTrue(manifest["safety"]["human_checkout_connected"])
        self.assertTrue(manifest["safety"]["no_private_keys"])
        self.assertFalse(manifest["safety"]["wallet_capability_connected"])
        self.assertFalse(manifest["safety"]["nft_mint_capability_connected"])
        self.assertTrue(manifest["safety"]["external_execution_requires_capability_grant"])
        self.assertTrue(manifest["safety"]["no_broker_or_trading_api"])
        self.assertTrue(manifest["safety"]["no_strategy_category_lock"])
        self.assertEqual(
            {item["opportunity_id"] for item in state["current_portfolio"]},
            {item["opportunity_id"] for item in manifest["current_portfolio"]},
        )
        self.assertEqual(state["revenue"]["gross_revenue"], manifest["revenue"]["gross_revenue"])
        self.assertEqual(state["revenue"]["net_revenue"], manifest["revenue"]["net_revenue"])

    def test_checkout_config_is_scoped_and_human_configured(self):
        config = json.loads((ROOT / "site" / "checkout-config.json").read_text(encoding="utf-8"))

        self.assertEqual("active", config["status"])
        self.assertEqual("opp-agent-launch-qa", config["experiment_id"])
        self.assertEqual("stripe", config["provider"])
        self.assertTrue(config["checkout_url"].startswith("https://buy.stripe.com/"))
        self.assertTrue(config["configured_by_human"])
        self.assertNotIn("price", config)

    def test_dashboard_uses_operator_state_and_has_no_generic_buy_button(self):
        html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")

        self.assertIn("Autonomous Revenue Operator", html)
        self.assertIn("This agent is trying to earn its own physical form", html)
        self.assertIn("../data/operator_state.json", html)
        self.assertIn("Recently Killed Or Pivoted", html)
        self.assertNotIn('id="buyButton"', html)
        self.assertNotIn("stripe.com/pay", html)
        self.assertNotIn("lemonsqueezy.com/checkout", html)

    def test_revenue_ledger_starts_at_zero(self):
        ledger = json.loads((ROOT / "data" / "revenue_ledger.json").read_text(encoding="utf-8"))
        public_ledger = (ROOT / "docs" / "REVENUE_LEDGER.md").read_text(encoding="utf-8")

        self.assertEqual([], ledger["transactions"])
        self.assertIn("| Gross revenue | $0.00 |", public_ledger)
        self.assertIn("| Net revenue | $0.00 |", public_ledger)

    def test_no_secret_or_execution_material_is_committed(self):
        secret_patterns = [
            r"sk_live_[A-Za-z0-9]+",
            r"sk_test_[A-Za-z0-9]+",
            r"whsec_[A-Za-z0-9]+",
            r"xprv[1-9A-HJ-NP-Za-km-z]+",
            r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----",
            r"\bseed phrase\b\s*[:=]",
            r"\bmnemonic\b\s*[:=]",
        ]
        execution_patterns = [
            r"\bweb3\.eth\.send_transaction\b",
            r"\bmint_nft\s*\(",
            r"\bsend_email\s*\(",
            r"\bsend_dm\s*\(",
            r"\bpost_to_(linkedin|twitter|x|instagram)\s*\(",
            r"\bcreate_ad\s*\(",
            r"\bplace_order\s*\(",
            r"\bsubmit_order\s*\(",
        ]
        ignored_parts = {".git", "__pycache__", ".pytest_cache"}

        for path in ROOT.rglob("*"):
            if not path.is_file() or any(part in ignored_parts for part in path.parts):
                continue
            if path.suffix.lower() not in {
                ".py", ".md", ".json", ".html", ".toml", ".txt", ".yml", ".yaml", ".js", ".css"
            }:
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in secret_patterns + execution_patterns:
                self.assertIsNone(re.search(pattern, text, flags=re.IGNORECASE), f"{pattern} found in {path}")


if __name__ == "__main__":
    unittest.main()
