import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StarterKitAssetsTest(unittest.TestCase):
    def test_product_card_json_files_are_valid(self):
        paths = [
            ROOT / "starter-kit" / "free-sample" / "product-card.sample.json",
            ROOT / "starter-kit" / "paid-bundle" / "product-card-template.json",
            ROOT / "starter-kit" / "paid-bundle" / "example-product-card.json",
        ]
        for path in paths:
            with self.subTest(path=path):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual("agent_readable_product_card", data["schema_name"])
                self.assertEqual("0.1", data["schema_version"])
                self.assertIn("product", data)
                self.assertIn("commercial_terms", data)
                self.assertIn("agent_guidance", data)
                self.assertTrue(data["agent_guidance"]["purchase_requires_human_approval"])

    def test_launch_copy_is_marked_as_draft(self):
        text = (ROOT / "launch-copy" / "public-posts.md").read_text(encoding="utf-8").lower()
        self.assertIn("drafts only", text)
        self.assertIn("do not post without explicit approval", text)

    def test_landing_page_has_no_checkout_or_wallet_action(self):
        text = (ROOT / "site" / "index.html").read_text(encoding="utf-8").lower()
        blocked = ["stripe", "walletconnect", "mint now", "buy now", "href=\"https://"]
        for snippet in blocked:
            self.assertNotIn(snippet, text)
        self.assertIn("no payment is enabled", text)


if __name__ == "__main__":
    unittest.main()
