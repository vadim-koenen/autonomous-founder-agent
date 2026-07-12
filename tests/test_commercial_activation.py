import json
import unittest
from datetime import date
from pathlib import Path

from founder_agent.revenue import summarize_ledger
from scripts.refresh_commercial_funnel import build_funnel


ROOT = Path(__file__).resolve().parents[1]


class CommercialActivationTest(unittest.TestCase):
    def test_public_interest_is_measured_but_never_counted_as_revenue(self):
        issues = [
            {
                "number": 1,
                "title": "[Interest] Agent Launch QA Sprint",
                "body": "I need an Agent Launch QA Sprint.",
                "state": "open",
                "labels": [{"name": "revenue-experiment"}],
            },
            {
                "number": 2,
                "title": "Unrelated issue",
                "state": "open",
                "labels": [],
            },
        ]

        funnel = build_funnel(issues, as_of=date(2026, 7, 10))
        ledger = json.loads((ROOT / "data" / "revenue_ledger.json").read_text(encoding="utf-8"))
        revenue = summarize_ledger(ledger)

        self.assertEqual(1, funnel["metrics"]["public_interest_issues"])
        self.assertEqual(1, funnel["metrics"]["qa_sprint_interest_issues"])
        self.assertEqual("none", funnel["revenue_effect"])
        self.assertEqual(0.0, revenue.gross_revenue)
        self.assertEqual(0.0, revenue.net_revenue)

    def test_sales_page_uses_human_configured_public_checkout(self):
        checkout = json.loads((ROOT / "site" / "checkout-config.json").read_text(encoding="utf-8"))
        page = (ROOT / "site" / "qa-sprint.html").read_text(encoding="utf-8")

        self.assertEqual("active", checkout["status"])
        self.assertEqual("stripe", checkout["provider"])
        self.assertTrue(checkout["configured_by_human"])
        self.assertEqual(
            "https://buy.stripe.com/fZu00j2vSgJge0P08N3cc00",
            checkout["checkout_url"],
        )
        self.assertIn("Buy the full audit — $149", page)
        self.assertIn('target="_blank" rel="noopener"', page)
        self.assertIn("preflight.html", page)
        self.assertIn("SAMPLE_REPORT.md", page)
        self.assertIn("vadimkoenen@gmail.com", page)
        self.assertIn("Refunds: full refund if the audit isn't delivered within the agreed scope.", page)
        self.assertIn("checkout-config.json", page)
        self.assertNotIn("sk_live_", page)
        self.assertNotIn("private_key", page.lower())

    def test_funnel_output_contains_no_issue_body_or_buyer_identity(self):
        funnel = build_funnel(
            [
                {
                    "number": 7,
                    "title": "[Interest] Agent Launch QA Sprint",
                    "body": "secret@example.com",
                    "user": {"login": "buyer-name"},
                    "state": "closed",
                    "labels": [{"name": "revenue-experiment"}],
                }
            ],
            as_of=date(2026, 7, 10),
        )

        serialized = json.dumps(funnel)
        self.assertNotIn("secret@example.com", serialized)
        self.assertNotIn("buyer-name", serialized)


if __name__ == "__main__":
    unittest.main()
