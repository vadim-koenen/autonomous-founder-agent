import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class M2ActivationTest(unittest.TestCase):
    def test_agent_manifest_is_machine_readable_and_checkout_pending(self):
        manifest = json.loads((ROOT / "AGENT_MANIFEST.json").read_text(encoding="utf-8"))

        self.assertEqual("autonomous_founder_agent_manifest", manifest["schema_name"])
        self.assertEqual("checkout_pending", manifest["current_experiment"]["status"])
        self.assertEqual("", manifest["commerce_channels"]["human_checkout"]["checkout_url"])
        self.assertEqual("pending_human_checkout_url", manifest["commerce_channels"]["human_checkout"]["status"])
        self.assertTrue(manifest["safety"]["no_private_keys"])
        self.assertTrue(manifest["safety"]["no_wallet_transactions"])
        self.assertTrue(manifest["safety"]["no_nft_minting"])
        self.assertTrue(manifest["safety"]["no_email_dm_or_ad_sending"])
        self.assertTrue(manifest["safety"]["no_broker_or_trading_api"])

    def test_checkout_config_requires_human_public_url(self):
        config = json.loads((ROOT / "site" / "checkout-config.json").read_text(encoding="utf-8"))

        self.assertEqual("pending", config["status"])
        self.assertEqual("", config["provider"])
        self.assertEqual("", config["checkout_url"])
        self.assertFalse(config["configured_by_human"])
        self.assertEqual(19, config["price"]["amount"])

    def test_site_buy_button_is_pending_without_checkout_url(self):
        html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")

        self.assertIn("id=\"buyButton\"", html)
        self.assertIn("Checkout pending", html)
        self.assertIn("checkout-config.json", html)
        self.assertIn("This agent is trying to earn its own physical form", html)
        self.assertNotIn("stripe.com/pay", html)
        self.assertNotIn("lemonsqueezy.com/checkout", html)

    def test_revenue_ledger_starts_at_zero(self):
        ledger = (ROOT / "docs" / "REVENUE_LEDGER.md").read_text(encoding="utf-8")

        self.assertIn("| Gross revenue | $0.00 |", ledger)
        self.assertIn("| Net revenue | $0.00 |", ledger)
        self.assertIn("pending-checkout", ledger)

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
            if path.suffix.lower() not in {".py", ".md", ".json", ".html", ".toml", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in secret_patterns + execution_patterns:
                self.assertIsNone(re.search(pattern, text, flags=re.IGNORECASE), f"{pattern} found in {path}")


if __name__ == "__main__":
    unittest.main()
