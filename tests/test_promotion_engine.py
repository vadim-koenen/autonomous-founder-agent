import copy
import csv
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from promotion_engine.apollo import ApolloAccessError, ApolloClient
from promotion_engine.attribution import build_attributed_url
from promotion_engine.config import PromotionConfigError, load_config
from promotion_engine.cli import _private_input, main as promotion_main
from promotion_engine.engine import PromotionEngine
from promotion_engine.store import (
    SUPPRESSION_SCOPE_REASONS,
    PromotionStore,
)


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
            self.config,
            self.store,
            ROOT / "data/revenue_ledger.json",
            grants_path=ROOT / "config/capability_grants.json",
        )

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def activated_engine(self, grant_enabled=True, max_per_cycle=5):
        config = copy.deepcopy(self.config)
        email_config = config["channels"]["apollo_email"]
        email_config["send_enabled"] = True
        email_config["sequence_activation_implemented"] = True
        email_config["activation_gates"] = {
            gate: True for gate in email_config["activation_gates"]
        }
        grants_path = self.root / "activation-grants.json"
        grants_path.write_text(
            json.dumps(
                {
                    "grants": [
                        {
                            "capability_id": "commercial_email_or_dm",
                            "enabled": grant_enabled,
                            "max_per_cycle": max_per_cycle,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return PromotionEngine(
            config,
            self.store,
            ROOT / "data/revenue_ledger.json",
            grants_path=grants_path,
        )

    def record_empty_snapshot(self, scope):
        self.store.import_suppressions(
            [],
            "Synthetic authoritative empty {0} snapshot".format(scope),
            scope,
        )

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
            3,
            self.engine.approve(
                "Vadim Koenen", approve_all=True, channel="apollo_email"
            ),
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

    def test_closeout_draft_uses_a_complete_sentence(self):
        self.store.upsert_prospect(valid_prospect())
        self.engine.qualify()
        self.engine.create_drafts("apollo_email")
        closeout = next(
            draft
            for draft in self.store.review_drafts("krs_visibility_2026_q3")
            if draft["channel"] == "apollo_email" and draft["step_index"] == 3
        )
        self.assertIn(
            "If diagnosing this handoff becomes a priority",
            closeout["body"],
        )
        self.assertNotIn(
            "gaps often hide inside the marketo-to-salesforce handoff becomes",
            closeout["body"],
        )

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

    def test_campaign_qualifies_only_the_active_segment(self):
        self.store.upsert_prospect(valid_prospect())
        self.engine.qualify()
        self.engine.create_drafts("apollo_email")
        drafts = self.store.review_drafts("krs_visibility_2026_q3")
        self.assertEqual({"marketo_repair"}, {draft["segment_id"] for draft in drafts})

    def test_target_technology_is_a_hard_gate(self):
        prospect = valid_prospect()
        prospect["technologies"] = "Salesforce"
        self.store.upsert_prospect(prospect)
        result = self.engine.qualify()
        self.assertEqual(1, result["review_required"])
        self.assertEqual([], self.store.qualified_prospects("krs_visibility_2026_q3"))

    def test_target_role_and_seniority_are_hard_gates(self):
        wrong_role = valid_prospect(email="role@acme.example", company="Role Co")
        wrong_role["title"] = "Director, Product Analytics"
        self.store.upsert_prospect(wrong_role)
        manager = valid_prospect(email="manager@example.net", company="Manager Co")
        manager["title"] = "Marketing Operations Manager"
        manager["seniority"] = "Manager"
        manager["company_domain"] = "example.net"
        manager["source_url"] = "https://example.net/company"
        self.store.upsert_prospect(manager)

        result = self.engine.qualify()
        self.assertEqual(2, result["review_required"])
        self.assertEqual([], self.store.qualified_prospects("krs_visibility_2026_q3"))

    def test_target_company_size_and_industry_are_hard_gates(self):
        too_small = valid_prospect(email="small@acme.example", company="Small Co")
        too_small["company_size"] = "90"
        self.store.upsert_prospect(too_small)
        wrong_industry = valid_prospect(
            email="industry@example.net", company="Industry Co"
        )
        wrong_industry["company_domain"] = "example.net"
        wrong_industry["source_url"] = "https://example.net/company"
        wrong_industry["industry"] = "Consumer Restaurants"
        self.store.upsert_prospect(wrong_industry)

        result = self.engine.qualify()
        self.assertEqual(2, result["review_required"])
        self.assertEqual([], self.store.qualified_prospects("krs_visibility_2026_q3"))

    def test_suppressed_record_cannot_qualify(self):
        record = valid_prospect()
        self.store.upsert_prospect(record)
        self.engine.suppress(
            record["email"], "do_not_contact", "Synthetic DNC fixture"
        )
        result = self.engine.qualify()
        self.assertEqual(1, result["suppressed"])
        self.assertEqual([], self.store.qualified_prospects("krs_visibility_2026_q3"))

    def test_existing_crm_contact_is_a_distinct_suppression_reason(self):
        record = valid_prospect()
        self.store.upsert_prospect(record)
        self.engine.suppress(
            record["email"],
            "existing_crm_contact",
            "Synthetic HubSpot contact fixture",
        )
        result = self.engine.qualify()
        self.assertEqual(1, result["suppressed"])
        self.assertEqual(
            "existing_crm_contact", self.store.suppression_reason(record["email"])
        )

    def test_suppression_after_approval_blocks_export(self):
        record = valid_prospect()
        self.store.upsert_prospect(record)
        self.engine.qualify()
        self.engine.create_drafts("apollo_email")
        self.engine.approve(
            "Vadim Koenen", approve_all=True, channel="apollo_email"
        )
        self.engine.suppress(
            record["email"], "unsubscribed", "Synthetic unsubscribe fixture"
        )
        with self.assertRaisesRegex(ValueError, "no complete"):
            self.engine.export_apollo(self.root / "blocked.csv")

    def test_reimport_invalidates_score_drafts_and_approval(self):
        prospect = valid_prospect()
        self.store.upsert_prospect(prospect)
        self.engine.qualify()
        self.engine.create_drafts("apollo_email")
        self.engine.approve(
            "Vadim Koenen", approve_all=True, channel="apollo_email"
        )

        prospect["country"] = "Canada"
        self.store.upsert_prospect(prospect)
        counts = self.store.aggregate_counts("krs_visibility_2026_q3")
        self.assertEqual({}, counts["qualification"])
        self.assertEqual({}, counts["drafts"])
        with self.assertRaisesRegex(ValueError, "no complete"):
            self.engine.export_apollo(self.root / "blocked-after-reimport.csv")

    def test_changed_campaign_copy_invalidates_prior_approval_at_export(self):
        self.store.upsert_prospect(valid_prospect())
        self.engine.qualify()
        self.engine.create_drafts("apollo_email")
        self.engine.approve(
            "Vadim Koenen", approve_all=True, channel="apollo_email"
        )
        self.engine.segments["marketo_repair"][
            "pain"
        ] = "A changed campaign claim requires a fresh review."

        with self.assertRaisesRegex(ValueError, "no complete"):
            self.engine.export_apollo(self.root / "stale-copy.csv")
        statuses = {
            draft["status"]
            for draft in self.store.review_drafts("krs_visibility_2026_q3")
        }
        self.assertIn("draft", statuses)

    def test_revoked_approver_invalidates_prior_approval_at_export(self):
        self.store.upsert_prospect(valid_prospect())
        self.engine.qualify()
        self.engine.create_drafts("apollo_email")
        self.engine.approve(
            "Vadim Koenen", approve_all=True, channel="apollo_email"
        )
        self.config["policy"]["allowed_approvers"] = ["Replacement Reviewer"]

        with self.assertRaisesRegex(ValueError, "no complete"):
            self.engine.export_apollo(self.root / "revoked-approver.csv")
        statuses = {
            draft["status"]
            for draft in self.store.review_drafts("krs_visibility_2026_q3")
        }
        self.assertEqual({"draft"}, statuses)

    def test_batch_approval_is_channel_scoped_and_approver_allowlisted(self):
        self.store.upsert_prospect(valid_prospect())
        self.engine.qualify()
        self.engine.create_drafts("apollo_email")
        self.engine.create_drafts("linkedin_manual_task")
        with self.assertRaisesRegex(ValueError, "channel is required"):
            self.engine.approve("Vadim Koenen", approve_all=True)
        with self.assertRaisesRegex(ValueError, "allowed_approvers"):
            self.engine.approve(
                "Unverified Reviewer",
                approve_all=True,
                channel="apollo_email",
            )
        self.assertEqual(
            3,
            self.engine.approve(
                "Vadim Koenen", approve_all=True, channel="apollo_email"
            ),
        )
        statuses = {
            (draft["channel"], draft["status"])
            for draft in self.store.review_drafts("krs_visibility_2026_q3")
        }
        self.assertEqual(
            {
                ("apollo_email", "approved"),
                ("linkedin_manual_task", "draft"),
            },
            statuses,
        )

    def test_prospect_approval_covers_only_that_sequence(self):
        first_id = self.store.upsert_prospect(valid_prospect())
        second = valid_prospect("second@example.net", company="Second Co")
        second["company_domain"] = "example.net"
        second["source_url"] = "https://example.net/company"
        self.store.upsert_prospect(second)
        self.engine.qualify()
        self.engine.create_drafts("apollo_email")

        self.assertEqual(
            3,
            self.engine.approve(
                "Vadim Koenen",
                prospect_id=first_id,
                channel="apollo_email",
            ),
        )
        drafts = self.store.review_drafts("krs_visibility_2026_q3")
        approved_prospects = {
            draft["prospect_id"]
            for draft in drafts
            if draft["status"] == "approved"
        }
        self.assertEqual({first_id}, approved_prospects)

    def test_bulk_suppression_import_records_snapshot(self):
        csv_path = self.root / "suppressions.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=["email", "reason", "evidence_reference"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "email": "existing@example.com",
                    "reason": "existing_crm_contact",
                    "evidence_reference": "Synthetic HubSpot export",
                }
            )
        result = self.engine.import_suppressions_csv(
            csv_path,
            "Synthetic HubSpot snapshot",
            "crm_contacts",
        )
        self.assertEqual({"imported": 1, "scope": "crm_contacts"}, result)
        snapshot = self.store.get_metadata("suppression_snapshot:crm_contacts")
        self.assertEqual(1, snapshot["value"]["record_count"])
        self.assertEqual(
            "existing_crm_contact",
            self.store.suppression_reason("existing@example.com"),
        )

    def test_bulk_suppression_import_is_atomic_on_invalid_record(self):
        with self.assertRaisesRegex(ValueError, "unsupported suppression reason"):
            self.store.import_suppressions(
                [
                    {
                        "email": "valid@example.com",
                        "reason": "existing_crm_contact",
                        "evidence_reference": "Synthetic valid record",
                    },
                    {
                        "email": "invalid@example.com",
                        "reason": "not_a_reason",
                        "evidence_reference": "Synthetic invalid record",
                    },
                ],
                "Synthetic snapshot",
                "crm_contacts",
            )
        self.assertIsNone(self.store.suppression_reason("valid@example.com"))
        self.assertIsNone(
            self.store.get_metadata("suppression_snapshot:crm_contacts")
        )

    def test_weaker_snapshot_reason_cannot_downgrade_opt_out(self):
        email = "optout@example.com"
        self.store.suppress(
            email,
            "unsubscribed",
            "Synthetic recipient opt-out",
        )
        self.store.import_suppressions(
            [
                {
                    "email": email,
                    "reason": "existing_crm_contact",
                    "evidence_reference": "Synthetic CRM contact snapshot",
                }
            ],
            "Synthetic HubSpot snapshot",
            "crm_contacts",
        )

        self.assertEqual("unsubscribed", self.store.suppression_reason(email))
        history = self.store.suppression_history(email)
        self.assertEqual(
            ["unsubscribed", "existing_crm_contact"],
            [item["reason"] for item in history],
        )
        self.assertEqual(
            ["manual", "crm_contacts"],
            [item["source_scope"] for item in history],
        )

    def test_activation_preflight_fails_closed(self):
        preflight = self.engine.activation_preflight()
        self.assertFalse(preflight["ready"])
        self.assertIn(
            "suppression_snapshot_missing:crm_contacts",
            preflight["blockers"],
        )
        self.assertIn("engine_sending_disabled", preflight["blockers"])
        self.assertIn(
            "commercial_email_capability_disabled",
            preflight["blockers"],
        )

    def test_partial_suppression_scope_cannot_clear_preflight(self):
        engine = self.activated_engine(grant_enabled=True, max_per_cycle=3)
        self.record_empty_snapshot("crm_contacts")

        partial = engine.activation_preflight()
        self.assertFalse(partial["ready"])
        self.assertIn(
            "suppression_snapshot_missing:apollo_delivery_suppressions",
            partial["blockers"],
        )
        self.assertIn(
            "suppression_snapshot_missing:crm_commercial_relationships",
            partial["blockers"],
        )

        self.record_empty_snapshot("apollo_delivery_suppressions")
        self.record_empty_snapshot("crm_commercial_relationships")
        complete = engine.activation_preflight()
        self.assertTrue(complete["ready"])
        self.assertEqual(3, complete["effective_daily_limit_after_activation"])

    def test_disabled_commercial_email_grant_blocks_otherwise_ready_preflight(self):
        engine = self.activated_engine(grant_enabled=False, max_per_cycle=5)
        for scope in SUPPRESSION_SCOPE_REASONS:
            self.record_empty_snapshot(scope)

        preflight = engine.activation_preflight()
        self.assertFalse(preflight["ready"])
        self.assertIn(
            "commercial_email_capability_disabled",
            preflight["blockers"],
        )

    def test_ambiguous_commercial_email_grants_fail_closed(self):
        engine = self.activated_engine(grant_enabled=True, max_per_cycle=5)
        grant_payload = json.loads(engine.grants_path.read_text(encoding="utf-8"))
        grant_payload["grants"].append(dict(grant_payload["grants"][0]))
        engine.grants_path.write_text(
            json.dumps(grant_payload),
            encoding="utf-8",
        )
        for scope in SUPPRESSION_SCOPE_REASONS:
            self.record_empty_snapshot(scope)

        preflight = engine.activation_preflight()
        self.assertFalse(preflight["ready"])
        self.assertIn(
            "commercial_email_capability_grant_ambiguous",
            preflight["blockers"],
        )

    def test_activation_configuration_requires_exact_boolean_gates(self):
        missing_gate = copy.deepcopy(self.config)
        del missing_gate["channels"]["apollo_email"]["activation_gates"][
            "unsubscribe_verified"
        ]
        invalid_boolean = copy.deepcopy(self.config)
        invalid_boolean["channels"]["apollo_email"]["activation_gates"][
            "unsubscribe_verified"
        ] = "false"
        invalid_send_flag = copy.deepcopy(self.config)
        invalid_send_flag["channels"]["apollo_email"]["send_enabled"] = "false"

        for index, candidate in enumerate(
            (missing_gate, invalid_boolean, invalid_send_flag)
        ):
            with self.subTest(index=index):
                path = self.root / "invalid-config-{0}.json".format(index)
                path.write_text(json.dumps(candidate), encoding="utf-8")
                with self.assertRaises(PromotionConfigError):
                    load_config(path)

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
        self.assertEqual(
            "apollo_delivery_event",
            self.store.suppression_history("ada@acme.example")[0]["source_scope"],
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

    def test_apollo_import_rejects_tracked_repository_input(self):
        with self.assertRaisesRegex(ValueError, "PII-bearing outputs"):
            _private_input(ROOT / "data" / "unsafe-apollo.csv")

    def test_apollo_health_without_key_returns_structured_error(self):
        original = os.environ.pop("APOLLO_API_KEY", None)
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                status = promotion_main(["apollo-health"])
        finally:
            if original is not None:
                os.environ["APOLLO_API_KEY"] = original
        self.assertEqual(2, status)
        payload = json.loads(output.getvalue())
        self.assertFalse(payload["ok"])
        self.assertFalse(payload["credential_present"])

    def test_apollo_paths_are_validated_before_client_or_credit_action(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            private = root / "private"
            private.mkdir()
            filters = private / "filters.json"
            filters.write_text(
                json.dumps({"person_id": "synthetic-person"}),
                encoding="utf-8",
            )
            unsafe_output = root / "outside-private.json"
            safe_output = private / "enriched.json"

            with mock.patch("promotion_engine.cli.PRIVATE_ROOT", private), mock.patch(
                "promotion_engine.cli.ApolloClient"
            ) as client_class, mock.patch.dict(
                os.environ, {"APOLLO_API_KEY": "synthetic-key"}
            ):
                with self.assertRaisesRegex(ValueError, "PII-bearing outputs"):
                    promotion_main(
                        [
                            "apollo-enrich",
                            "--filters-json",
                            str(filters),
                            "--out",
                            str(unsafe_output),
                        ]
                    )
                client_class.assert_not_called()

                client_class.return_value.enrich_person.return_value = {
                    "person": {"id": "synthetic-person"}
                }
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    status = promotion_main(
                        [
                            "apollo-enrich",
                            "--filters-json",
                            str(filters),
                            "--out",
                            str(safe_output),
                        ]
                    )
                self.assertEqual(0, status)
                client_class.return_value.enrich_person.assert_called_once_with(
                    {"person_id": "synthetic-person"}
                )
                self.assertTrue(safe_output.is_file())


if __name__ == "__main__":
    unittest.main()
