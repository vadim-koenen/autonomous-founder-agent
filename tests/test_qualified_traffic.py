import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class QualifiedTrafficTest(unittest.TestCase):
    def test_distribution_grant_is_narrow_and_rate_limited(self):
        grants = json.loads(
            (ROOT / "config" / "capability_grants.json").read_text(encoding="utf-8")
        )["grants"]
        grant = next(
            item
            for item in grants
            if item["capability_id"] == "github_qualified_contribution_pr"
        )

        self.assertTrue(grant["enabled"])
        self.assertEqual(1, grant["max_per_cycle"])
        self.assertEqual("github_contribution_prs", grant["channel_id"])
        self.assertIn("explicitly invite", grant["scope"])
        self.assertIn("never use unsolicited issues", grant["scope"])
        self.assertIn("bulk promotion", grant["scope"])

    def test_distribution_channel_forbids_promotional_issue_spam(self):
        registry = json.loads(
            (ROOT / "data" / "channel_registry.json").read_text(encoding="utf-8")
        )["channels"]
        channel = next(
            item for item in registry if item["channel_id"] == "github_contribution_prs"
        )

        self.assertTrue(channel["agent_has_access"])
        self.assertEqual("connected_qualified_only", channel["current_status"])
        restrictions = " ".join(channel["platform_restrictions"])
        self.assertIn("no unsolicited promotional issues or comments", restrictions)
        self.assertIn("no bulk or misleading submissions", restrictions)

    def test_funnel_uses_free_value_before_checkout_and_keeps_risky_actions_off(self):
        engine = json.loads(
            (ROOT / "data" / "qualified_traffic_engine.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(149, engine["primary_offer"]["price_usd"])
        stages = [item["stage"] for item in engine["funnel"]]
        self.assertLess(stages.index("value_event"), stages.index("conversion"))
        self.assertEqual(
            "data/revenue_ledger.json",
            engine["measurement"]["revenue_source_of_truth"],
        )
        self.assertTrue(all(value is False for value in engine["safety"].values()))

    def test_preflight_supports_shareable_reports_and_attributed_checkout(self):
        page = (ROOT / "site" / "preflight.html").read_text(encoding="utf-8")

        self.assertIn('searchParams.set("repo"', page)
        self.assertIn("window.history.replaceState", page)
        self.assertIn('id="shareButton"', page)
        self.assertIn('data-checkout-link', page)
        self.assertIn('searchParams.set("utm_source"', page)
        self.assertIn("https://buy.stripe.com/fZu00j2vSgJge0P08N3cc00", page)
        self.assertIn('target="_blank" rel="noopener"', page)


if __name__ == "__main__":
    unittest.main()
