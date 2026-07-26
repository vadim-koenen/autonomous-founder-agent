import csv
import json
import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from promotion_engine.apollo import ApolloAccessError, ApolloClient
from promotion_engine.attribution import build_attributed_url
from promotion_engine.config import load_config
from promotion_engine.engine import PromotionEngine
from promotion_engine.store import PromotionStore


ROOT = Path(__file__).resolve().parents[1]


def valid_prospect(email="ada@acme.example", company="Acme", evidence=None):
    return {
        "first_name": "Ada",
        "last_name": "Buyer",
        "email": email,
        "email_status": "verified",
        "title": "Director, Marketing Operations",
        "seniority": "Director",
        "company": company,
        "company_domain": email.split("@", 1)[1],
        "company_size": "800",
        "country": "United States",
        "industry": "B2B SaaS",
        "technologies": "Marketo; Salesforce",
        "source_url": "https://{0}/company".format(email.split("@", 1)[1]),
        "evidence_note": evidence
        or "The public careers page lists Marketo and Salesforce operations ownership.",
        "apollo_person_id": "apollo-person-example",
    }


class PromotionEngineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = PromotionStore(self.root / "promotion.sqlite3")
        self.config = load_config(ROOT / "config/promotion_engine.json")
        self.engine = PromotionEngine(
            self.config, self.store, ROOT / "data/revenue_ledger.json"
        )

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_config_is_secret_free_and_sending_is_disabled(self):
        serialized = json.dumps(self.config).lower()
        self.assertNotIn("apollo_api_key", serialized)
        self.assertFalse(self.config["channels"]["apollo_email"]["send_enabled"])
        self.assertFalse(
            self.config["channels"]["apollo_email"]["sequence_activation_implemented"]
        )

    def test_import_qualify_draft_approve_export_never_marks_sent(self):
        csv_path = self.root / "apollo.csv"
        row = valid_prospect()
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)

        self.assertEqual(
            {"imported": 1, "rejected": 0}, self.engine.import_apollo_csv(csv_path)
        )
        self.assertEqual(1, self.engine.qualify()["qualified"])
        draft_result = self.engine.create_drafts("apollo_email")
        self.assertEqual(3, draft_result["drafts_considered"])
        self.assertEqual(
            3, self.engine.approve("Vadim Koenen", approve_all=True)
        )

        export_path = self.root / "approved.csv"
        result = self.engine.export_apollo(export_path)
        self.assertEqual(3, result["records"])
        self.assertEqual(0, result["sent"])
        self.assertEqual(
            {"exported": 3},
            self.store.aggregate_counts("krs_visibility_2026_q3")["drafts"],
        )
        with export_path.open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([1, 2, 3], [int(item["step_index"]) for item in rows])
        self.assertTrue(all("utm_campaign=krs_visibility_2026_q3" in row["body"] for row in rows))

    def test_review_queue_contains_evidence_and_draft_ids(self):
        self.store.upsert_prospect(valid_prospect())
        self.engine.qualify()
        self.engine.create_drafts("linkedin_manual_task")
        output = self.root / "review.csv"
        result = self.engine.export_review_queue(output)
        self.assertEqual(1, result["records"])
        with output.open(encoding="utf-8") as handle:
            row = next(csv.DictReader(handle))
        self.assertTrue(row["draft_id"])
        self.assertEqual("linkedin_manual_task", row["channel"])
        self.assertIn("public careers page", row["evidence_note"])

    def test_policy_blocks_free_email_unknown_jurisdiction_and_missing_evidence(self):
        prospect = valid_prospect(email="buyer@gmail.com", evidence="short")
        prospect["country"] = "Canada"
        prospect["source_url"] = "http://example.com"
        self.store.upsert_prospect(prospect)

        result = self.engine.qualify()
        self.assertEqual(1, result["review_required"])
        self.assertEqual([], self.store.qualified_prospects("krs_visibility_2026_q3"))

    def test_one_person_per_company_cap(self):
        first = valid_prospect("ada@acme.example")
        second = valid_prospect("grace@acme.example")
        second["first_name"] = "Grace"
        self.store.upsert_prospect(first)
        self.store.upsert_prospect(second)

        result = self.engine.qualify()
        self.assertEqual(1, result["qualified"])
        self.assertEqual(1, result["review_required"])

    def test_suppressed_record_cannot_qualify(self):
        record = valid_prospect()
        self.store.upsert_prospect(record)
        self.engine.suppress(
            record["email"], "do_not_contact", "Synthetic DNC fixture"
        )
        result = self.engine.qualify()
        self.assertEqual(1, result["suppressed"])
        self.assertEqual([], self.store.qualified_prospects("krs_visibility_2026_q3"))

    def test_suppression_after_approval_blocks_export(self):
        record = valid_prospect()
        self.store.upsert_prospect(record)
        self.engine.qualify()
        self.engine.create_drafts("apollo_email")
        self.engine.approve("Vadim Koenen", approve_all=True)
        self.engine.suppress(
            record["email"], "unsubscribed", "Synthetic unsubscribe fixture"
        )
        with self.assertRaisesRegex(ValueError, "no complete"):
            self.engine.export_apollo(self.root / "blocked.csv")

    def test_attribution_contains_no_personal_identifier(self):
        url = build_attributed_url(
            "https://vadimkoenen.com",
            "/marketo-consultant/",
            "apollo",
            "email",
            "krs_visibility_2026_q3",
            "marketo_step_1",
            "marketo_repair",
        )
        query = parse_qs(urlsplit(url).query)
        self.assertEqual(["apollo"], query["utm_source"])
        self.assertNotIn("@", url)
        self.assertNotIn("apollo-person-example", url)

    def test_report_uses_revenue_ledger_only(self):
        self.store.upsert_prospect(valid_prospect())
        self.engine.qualify()
        report = self.engine.report()
        self.assertEqual(0, report["verified_revenue"]["transactions"])
        self.assertEqual(0.0, report["verified_revenue"]["gross_usd"])
        self.assertIn("Only ledger-verified", report["interpretation"])

    def test_unsubscribe_event_creates_suppression(self):
        prospect_id = self.store.upsert_prospect(valid_prospect())
        self.engine.record_event(
            prospect_id,
            "unsubscribed",
            "apollo_email",
            "Synthetic Apollo activity fixture",
            "2026-07-26T15:00:00Z",
        )
        self.assertEqual(
            "unsubscribed", self.store.suppression_reason("ada@acme.example")
        )


class ApolloBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.grants_path = Path(self.temp.name) / "grants.json"
        self.grants_path.write_text(
            json.dumps(
                {
                    "grants": [
                        {"capability_id": "apollo_read_and_enrich", "enabled": False},
                        {"capability_id": "apollo_contact_sync", "enabled": False},
                        {
                            "capability_id": "apollo_sequence_enrollment",
                            "enabled": False,
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_search_and_write_are_blocked_before_network(self):
        client = ApolloClient(api_key="synthetic-key", grants_path=self.grants_path)
        with self.assertRaisesRegex(
            ApolloAccessError, "apollo_read_and_enrich capability is disabled"
        ):
            client.search_people({"page": 1})
        with self.assertRaisesRegex(
            ApolloAccessError, "apollo_contact_sync capability is disabled"
        ):
            client.create_contact({"email": "ada@acme.example"})

    def test_sequence_activation_is_not_implemented(self):
        client = ApolloClient(api_key="synthetic-key", grants_path=self.grants_path)
        self.assertFalse(hasattr(client, "activate_sequence"))

    def test_enabled_writes_still_dedupe_and_enroll_paused(self):
        self.grants_path.write_text(
            json.dumps(
                {
                    "grants": [
                        {"capability_id": "apollo_contact_sync", "enabled": True},
                        {
                            "capability_id": "apollo_sequence_enrollment",
                            "enabled": True,
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        client = ApolloClient(api_key="synthetic-key", grants_path=self.grants_path)
        calls = []

        def fake_request(method, path, payload=None):
            calls.append((method, path, payload))
            return {"ok": True}

        client._request = fake_request
        original_write = os.environ.get("APOLLO_WRITE_ENABLED")
        original_enrollment = os.environ.get("APOLLO_SEQUENCE_ENROLLMENT_ENABLED")
        os.environ["APOLLO_WRITE_ENABLED"] = "true"
        os.environ["APOLLO_SEQUENCE_ENROLLMENT_ENABLED"] = "true"
        try:
            client.create_contact({"email": "ada@acme.example"})
            client.add_contact_to_sequence_paused(
                "sequence-example", "contact-example", "mailbox-example"
            )
        finally:
            if original_write is None:
                os.environ.pop("APOLLO_WRITE_ENABLED", None)
            else:
                os.environ["APOLLO_WRITE_ENABLED"] = original_write
            if original_enrollment is None:
                os.environ.pop("APOLLO_SEQUENCE_ENROLLMENT_ENABLED", None)
            else:
                os.environ["APOLLO_SEQUENCE_ENROLLMENT_ENABLED"] = original_enrollment

        self.assertIn("run_dedupe=true", calls[0][1])
        self.assertEqual("paused", calls[1][2]["contact_status"])

    def test_api_key_is_required(self):
        original = os.environ.pop("APOLLO_API_KEY", None)
        try:
            with self.assertRaisesRegex(ApolloAccessError, "not configured"):
                ApolloClient(api_key="", grants_path=self.grants_path)
        finally:
            if original is not None:
                os.environ["APOLLO_API_KEY"] = original


class PromotionRepositoryBoundaryTest(unittest.TestCase):
    def test_private_promotion_data_is_gitignored(self):
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".promotion-private/", gitignore)

    def test_public_promotion_data_directory_warns_against_pii(self):
        text = (ROOT / "data/promotion/README.md").read_text(encoding="utf-8")
        self.assertIn("Never copy", text)
        self.assertIn("revenue_ledger.json", text)


if __name__ == "__main__":
    unittest.main()
