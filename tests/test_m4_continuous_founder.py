import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from founder_agent.discovery import scan_sources
from founder_agent.execution import (
    RESPONSE_MARKER,
    append_execution_log,
    execute_bounded_action,
    respond_to_inbound_interest,
)
from founder_agent.operator import merge_discovery_into_scan
from founder_agent.operator_models import opportunity_from_dict
from founder_agent.operator_scoring import OPPORTUNITY_WEIGHTS, rank_opportunities
from founder_agent.runtime_budget import BudgetExceededError, BudgetTracker, RuntimeBudget
from founder_agent.synthesis import (
    GITHUB_MODELS_API_VERSION,
    MAX_SYNTHESIS_PROMPT_CHARS,
    GitHubModelsClient,
    build_synthesis_prompt,
    synthesize_opportunities,
)
from scripts.run_continuous_founder import (
    _select_model,
    _update_manifest,
    _update_model_access_state,
)


ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def make_budget(**overrides):
    values = {
        "source_fetches": 6,
        "model_calls": 1,
        "new_opportunities": 4,
        "channel_candidates": 3,
        "publications": 1,
        "external_messages": 3,
        "repository_writes": 1,
        "spend_usd": 0.0,
        "runtime_minutes": 12,
    }
    values.update(overrides)
    return RuntimeBudget(**values)


def evidence_record():
    return {
        "evidence_id": "ev-live-test-market",
        "title": "Test market",
        "source_url": "https://example.com/market",
        "observed_at": "2026-07-11T12:00:00+00:00",
        "summary": "A test fixture reports a concrete buyer signal.",
        "quality": "test_fixture",
        "signals": {"buyers": 3},
        "caveats": ["Fixture evidence is not a real revenue claim."],
    }


def valid_model_payload():
    return {
        "channel_candidates": [
            {
                "channel_id": "test-market",
                "name": "Test Market",
                "source_url": "https://example.com/market",
                "kinds": ["discovery"],
                "buyer_signal": "Three explicit requests",
                "access_requirements": "Public read only",
                "platform_risk_1_to_10": 3,
            }
        ],
        "opportunities": [
            {
                "slug": "specific-outcome",
                "name": "Specific Outcome",
                "category": "test_service",
                "thesis": "Reachable buyers requested a bounded result.",
                "offer": "Deliver outcome <script>alert(1)</script> within 24 hours.",
                "buyer": "Three named public buyer types",
                "price": {"amount": 99, "currency": "USD", "billing_model": "fixed"},
                "acquisition_channel": "The exact public market from the evidence.",
                "payment_rail": "A configured human checkout after validation.",
                "estimated_cost": 0,
                "expected_outcome": "One verified customer.",
                "evidence_ids": ["ev-live-test-market"],
                "free_substitutes": ["Manual work"],
                "scores": {key: 8 for key in OPPORTUNITY_WEIGHTS},
                "role_fit": {"cash": 9, "asset": 7, "frontier": 6},
                "required_assets": ["Sample"],
                "next_action": {
                    "description": "Publish a bounded validation brief.",
                    "channel_id": "github_pages",
                    "authority_class": "autonomous",
                },
                "validation_72h": ["One qualified public interest signal"],
            }
        ],
        "selected_execution": {
            "opportunity_slug": "specific-outcome",
            "action_type": "publish_validation_brief",
            "reason": "The opportunity has a concrete buyer and executable validation step.",
        },
    }


class M4ContinuousFounderTest(unittest.TestCase):
    def setUp(self):
        self.base_scan = load_json("data/opportunity_scan_2026-07-09.json")
        self.channels = load_json("data/channel_registry.json")
        self.snapshot = {
            "run_id": "discovery-test",
            "observed_at": "2026-07-11T12:00:00+00:00",
            "sources": [],
            "evidence": [evidence_record()],
        }

    def synthesize(self, payload=None):
        tracker = BudgetTracker(make_budget())
        response = json.dumps(payload or valid_model_payload())
        result = synthesize_opportunities(
            self.snapshot,
            self.base_scan,
            self.channels,
            None,
            tracker,
            model="openai/gpt-5",
            model_callable=lambda prompt, model: response,
            observed_at=datetime(2026, 7, 11, 12, tzinfo=timezone.utc),
        )
        return result, tracker

    def test_budget_fails_closed_before_overrun(self):
        tracker = BudgetTracker(make_budget(publications=1))
        tracker.consume("publications")
        with self.assertRaises(BudgetExceededError):
            tracker.consume("publications")
        self.assertEqual(1, tracker.snapshot()["used"]["publications"])
        with self.assertRaises(ValueError):
            BudgetTracker(make_budget()).consume("runtime_minutes", float("nan"))

    def test_source_rotation_respects_fetch_limit(self):
        registry = {
            "sources": [
                {
                    "source_id": "old",
                    "name": "Old",
                    "url": "https://models.github.ai/catalog/models",
                    "adapter": "model_catalog",
                    "priority": 100,
                    "allowed_host": "models.github.ai",
                },
                {
                    "source_id": "new-high",
                    "name": "New high",
                    "url": "https://models.github.ai/catalog/models",
                    "adapter": "model_catalog",
                    "priority": 90,
                    "allowed_host": "models.github.ai",
                },
                {
                    "source_id": "new-low",
                    "name": "New low",
                    "url": "https://models.github.ai/catalog/models",
                    "adapter": "model_catalog",
                    "priority": 80,
                    "allowed_host": "models.github.ai",
                },
            ]
        }
        previous = {
            "sources": [
                {
                    "source_id": "old",
                    "observed_at": "2026-07-10T00:00:00+00:00",
                    "last_attempt_at": "2026-07-10T00:00:00+00:00",
                    "status": "ok",
                    "summary": "prior",
                    "metrics": {},
                    "items": [],
                }
            ]
        }
        tracker = BudgetTracker(make_budget(source_fetches=2))
        result = scan_sources(
            registry,
            previous,
            tracker,
            fetch_json=lambda source, token: [],
            observed_at=datetime(2026, 7, 11, 12, tzinfo=timezone.utc),
        )

        self.assertEqual(["new-high", "new-low"], result["attempted_source_ids"])
        self.assertEqual(2, result["budget"]["used"]["source_fetches"])

    def test_failed_fetch_cannot_become_stale_evidence(self):
        registry = {
            "sources": [
                {
                    "source_id": "failed",
                    "name": "Failed",
                    "url": "https://models.github.ai/catalog/models",
                    "adapter": "model_catalog",
                    "priority": 1,
                    "allowed_host": "models.github.ai",
                }
            ]
        }
        previous = {
            "sources": [
                {
                    "source_id": "failed",
                    "status": "error",
                    "observed_at": "",
                    "fingerprint": "",
                    "summary": "Source fetch failed; no market inference was made.",
                }
            ]
        }

        result = scan_sources(
            registry,
            previous,
            BudgetTracker(make_budget(source_fetches=1)),
            fetch_json=lambda source, token: (_ for _ in ()).throw(RuntimeError("still failed")),
        )

        self.assertEqual("error", result["sources"][0]["status"])
        self.assertEqual([], result["evidence"])

    def test_public_issue_bodies_are_not_persisted_in_discovery(self):
        registry = {
            "sources": [
                {
                    "source_id": "issues",
                    "name": "Issues",
                    "url": "https://api.github.com/search/issues?q=test",
                    "adapter": "github_issues",
                    "priority": 1,
                    "allowed_host": "api.github.com",
                    "signal_type": "explicit_paid_work",
                }
            ]
        }
        payload = {
            "total_count": 1,
            "items": [
                {
                    "title": "Paid implementation request",
                    "body": "Contact private-looking@example.com for /bounty $500",
                    "html_url": "https://github.com/example/project/issues/1",
                    "repository_url": "https://api.github.com/repos/example/project",
                    "labels": [],
                    "comments": 0,
                }
            ],
        }
        result = scan_sources(
            registry,
            None,
            BudgetTracker(make_budget(source_fetches=1)),
            fetch_json=lambda source, token: payload,
        )

        serialized = json.dumps(result)
        self.assertNotIn("private-looking@example.com", serialized)
        self.assertEqual(500, result["sources"][0]["items"][0]["explicit_bounty_usd"])

    def test_model_proposal_requires_live_evidence_and_typed_scores(self):
        result, _ = self.synthesize()

        self.assertEqual("github_models", result["synthesis_mode"])
        self.assertEqual(["opp-discovered-specific-outcome"], result["new_opportunity_ids"])
        self.assertEqual(5.0, result["opportunities"][0]["scores"]["observable_buyer_demand"])
        self.assertGreater(result["opportunities"][0]["role_fit"]["cash"], 1)
        self.assertIn("score_adjustments", result["opportunities"][0])
        merged = merge_discovery_into_scan(self.base_scan, result)
        discovered = next(
            item for item in merged["opportunities"]
            if item["opportunity_id"] == "opp-discovered-specific-outcome"
        )
        self.assertNotIn("discovered_at", discovered)
        self.assertNotIn("score_adjustments", discovered)
        opportunity_from_dict(discovered)

        invalid = valid_model_payload()
        invalid["opportunities"][0]["evidence_ids"] = ["ev-model-invented"]
        rejected, _ = self.synthesize(invalid)
        self.assertEqual([], rejected["new_opportunity_ids"])
        self.assertEqual("monitor_signal", rejected["selected_execution"]["action_type"])

        malformed, _ = self.synthesize(
            {"opportunities": "not-a-list", "channel_candidates": ["not-an-object"], "selected_execution": []}
        )
        self.assertEqual([], malformed["new_opportunity_ids"])
        self.assertEqual([], malformed["new_channel_ids"])
        self.assertEqual("monitor_signal", malformed["selected_execution"]["action_type"])

        non_finite = valid_model_payload()
        non_finite["opportunities"][0]["scores"]["gross_margin"] = float("nan")
        rejected_non_finite, _ = self.synthesize(non_finite)
        self.assertEqual([], rejected_non_finite["new_opportunity_ids"])

        duplicate_channel = valid_model_payload()
        duplicate_channel["channel_candidates"][0]["channel_id"] = "github-pages"
        duplicate_channel_result, _ = self.synthesize(duplicate_channel)
        self.assertEqual([], duplicate_channel_result["new_channel_ids"])

    def test_model_prompt_is_compact_enough_for_free_github_models(self):
        prompt = build_synthesis_prompt(
            load_json("data/discovery_snapshot.json"),
            self.base_scan,
            self.channels,
            BudgetTracker(make_budget()),
            load_json("data/discovered_opportunities.json"),
        )

        self.assertLessEqual(len(prompt), MAX_SYNTHESIS_PROMPT_CHARS)
        self.assertIn("ev-live-github_open_bounties", prompt)
        self.assertIn("existing_opportunity_ids", prompt)
        self.assertNotIn("body_excerpt", prompt)

    def test_model_client_uses_current_version_without_persisting_token(self):
        response = io.BytesIO(b'{"choices":[{"message":{"content":"{}"}}]}')
        with patch("founder_agent.synthesis.urlopen", return_value=response) as urlopen_mock:
            completion = GitHubModelsClient("runtime-only-token").complete(
                "bounded prompt", "openai/gpt-5"
            )

        request = urlopen_mock.call_args.args[0]
        headers = dict(request.header_items())
        request_body = json.loads(request.data.decode("utf-8"))
        self.assertEqual("{}", completion)
        self.assertEqual(GITHUB_MODELS_API_VERSION, headers["X-github-api-version"])
        self.assertEqual("openai/gpt-5", request_body["model"])
        self.assertNotIn("runtime-only-token", request.data.decode("utf-8"))

    def test_publication_is_one_bounded_escaped_asset(self):
        synthesis, tracker = self.synthesize()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = execute_bounded_action(
                root,
                synthesis,
                self.snapshot,
                self.channels,
                tracker,
                eligible_opportunity_ids=["opp-discovered-specific-outcome"],
                observed_at=datetime(2026, 7, 11, 12, tzinfo=timezone.utc),
            )
            page = (root / "site" / "opportunities" / "latest.html").read_text(encoding="utf-8")
            self.assertEqual("published", record["status"])
            self.assertIn("&lt;script&gt;", page)
            self.assertNotIn("<script>alert(1)</script>", page)
            self.assertEqual(1, tracker.snapshot()["used"]["publications"])
            self.assertEqual(0, record["external_effects"]["messages"])
            self.assertEqual(0.0, record["external_effects"]["spend_usd"])

            prior = append_execution_log({}, record)
            duplicate = execute_bounded_action(
                root,
                synthesis,
                self.snapshot,
                self.channels,
                tracker,
                eligible_opportunity_ids=["opp-discovered-specific-outcome"],
                previous_log=prior,
                observed_at=datetime(2026, 7, 11, 18, tzinfo=timezone.utc),
            )
            self.assertEqual("skipped_duplicate", duplicate["status"])
            self.assertEqual(1, tracker.snapshot()["used"]["publications"])

    def test_inbound_replies_require_grant_token_and_stop_at_three(self):
        capabilities = load_json("config/capability_grants.json")
        posted = []

        def transport(method, url, payload, token):
            self.assertEqual("runtime-only-token", token)
            self.assertTrue(url.startswith("https://api.github.com/repos/vadim-koenen/autonomous-founder-agent/"))
            if method == "GET" and "issues?state=" in url:
                return [{"number": number} for number in range(1, 6)]
            if method == "GET":
                return []
            posted.append(payload["body"])
            return {"id": len(posted)}

        tracker = BudgetTracker(make_budget(external_messages=3))
        record = respond_to_inbound_interest(
            capabilities,
            tracker,
            github_token="runtime-only-token",
            transport=transport,
            observed_at=datetime(2026, 7, 11, 12, tzinfo=timezone.utc),
        )

        self.assertEqual("executed", record["status"])
        self.assertEqual(3, record["external_effects"]["messages"])
        self.assertEqual(3, len(posted))
        self.assertTrue(all(RESPONSE_MARKER in body for body in posted))
        self.assertNotIn("runtime-only-token", json.dumps(record))

        no_token = respond_to_inbound_interest(
            capabilities,
            BudgetTracker(make_budget()),
            github_token=None,
            transport=transport,
        )
        self.assertEqual("not_configured", no_token["status"])

    def test_roblox_is_eligible_but_not_artificially_promoted(self):
        extension = load_json("data/platform_opportunity_extensions.json")
        merged = merge_discovery_into_scan(self.base_scan, extension)
        ranked = rank_opportunities(
            opportunity_from_dict(item) for item in merged["opportunities"]
        )
        ranks = {
            item.opportunity.opportunity_id: index
            for index, item in enumerate(ranked, start=1)
        }

        self.assertIn("opp-roblox-launch-lens-plugin", ranks)
        self.assertIn("opp-roblox-embodiment-factory", ranks)
        self.assertGreater(ranks["opp-roblox-launch-lens-plugin"], ranks["opp-agent-launch-qa"])
        self.assertGreater(ranks["opp-roblox-embodiment-factory"], ranks["opp-roblox-launch-lens-plugin"])

    def test_preflight_product_updates_existing_cash_and_frontier_experiments(self):
        platform = load_json("data/platform_opportunity_extensions.json")
        products = load_json("data/product_opportunity_extensions.json")
        merged = merge_discovery_into_scan(self.base_scan, platform)
        merged = merge_discovery_into_scan(merged, products)
        by_id = {item["opportunity_id"]: item for item in merged["opportunities"]}

        self.assertEqual(
            "MCP / Agent Preflight Full Audit",
            by_id["opp-agent-launch-qa"]["name"],
        )
        self.assertEqual(
            "MCP / Agent Preflight Metered API",
            by_id["opp-x402-opportunity-pulse"]["name"],
        )
        opportunity_from_dict(by_id["opp-agent-launch-qa"])
        opportunity_from_dict(by_id["opp-x402-opportunity-pulse"])

    def test_manifest_refresh_preserves_active_human_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "site").mkdir()
            (root / "AGENT_MANIFEST.json").write_text(
                json.dumps(
                    {
                        "schema_name": "autonomous_founder_agent_manifest",
                        "revenue": {},
                        "payment_policy": {},
                    }
                ),
                encoding="utf-8",
            )
            (root / "site" / "checkout-config.json").write_text(
                json.dumps(
                    {
                        "status": "active",
                        "experiment_id": "opp-agent-launch-qa",
                        "provider": "stripe",
                        "checkout_url": "https://buy.stripe.com/example",
                        "configured_by_human": True,
                    }
                ),
                encoding="utf-8",
            )
            state = {
                "as_of": "2026-07-12",
                "ranked_opportunities": [
                    {"opportunity_id": "opp-agent-launch-qa", "name": "Full Audit"}
                ],
                "current_portfolio": [
                    {
                        "role": "cash",
                        "opportunity_id": "opp-agent-launch-qa",
                        "current_status": "validating",
                    }
                ],
                "revenue": {
                    "verified_transactions": 0,
                    "gross_revenue": 0,
                    "net_revenue": 0,
                    "physical_form_fund": 0,
                },
                "owner_funds_spent": 0,
            }

            _update_manifest(
                root,
                state,
                {"run_id": "test-run"},
                {"model": "test-model", "synthesis_mode": "test"},
            )
            manifest = json.loads((root / "AGENT_MANIFEST.json").read_text(encoding="utf-8"))

            self.assertEqual(["stripe_payment_link"], manifest["payment_policy"]["active_rails"])
            self.assertTrue(manifest["safety"]["human_checkout_connected"])
            self.assertEqual(
                "active_public_checkout",
                manifest["current_portfolio"][0]["payment_status"],
            )

    def test_workflow_runs_six_hour_model_cycle_and_direct_pages_deploy(self):
        workflow = (ROOT / ".github" / "workflows" / "revenue-operator.yml").read_text(encoding="utf-8")

        self.assertIn('cron: "17 */6 * * *"', workflow)
        self.assertIn("models: read", workflow)
        self.assertIn("issues: write", workflow)
        self.assertIn("scripts/run_continuous_founder.py", workflow)
        self.assertIn("actions/deploy-pages@v4", workflow)
        self.assertIn("if [ -d site/opportunities ]; then", workflow)
        self.assertNotIn("secrets.", workflow)

    def test_model_preference_uses_only_catalog_available_id(self):
        config = load_json("config/operator_budget.json")
        snapshot = {
            "sources": [
                {
                    "source_id": "github_models_catalog",
                    "status": "ok",
                    "items": [{"id": "openai/gpt-5"}],
                }
            ]
        }
        self.assertEqual("openai/gpt-5", _select_model(snapshot, config))
        snapshot["sources"][0]["items"].insert(0, {"id": "openai/gpt-5.5"})
        self.assertEqual("openai/gpt-5.5", _select_model(snapshot, config))

    def test_unavailable_preferred_model_uses_temporary_fallback(self):
        config = load_json("config/operator_budget.json")
        snapshot = {
            "sources": [
                {
                    "source_id": "github_models_catalog",
                    "status": "ok",
                    "items": [
                        {"id": "openai/gpt-5"},
                        {"id": "openai/gpt-4.1"},
                    ],
                }
            ]
        }
        now = datetime(2026, 7, 11, 12, tzinfo=timezone.utc)
        access = _update_model_access_state(
            {},
            {
                "model": "openai/gpt-5",
                "model_error": "GitHub Models request failed with HTTP 400: Unavailable model: gpt-5",
                "synthesis_mode": "deterministic_fallback",
            },
            now,
        )

        self.assertEqual("openai/gpt-4.1", _select_model(snapshot, config, access, now))
        self.assertEqual(
            "openai/gpt-5",
            _select_model(snapshot, config, access, datetime(2026, 7, 19, tzinfo=timezone.utc)),
        )
        self.assertNotIn("runtime-only-token", json.dumps(access))

    def test_unconnected_high_impact_capabilities_remain_explicit(self):
        capabilities = load_json("config/capability_grants.json")
        by_id = {item["capability_id"]: item for item in capabilities["grants"]}

        self.assertTrue(by_id["github_pages_publication"]["enabled"])
        self.assertTrue(by_id["github_issue_inbound_reply"]["enabled"])
        self.assertFalse(by_id["commercial_email_or_dm"]["enabled"])
        self.assertFalse(by_id["owner_funded_spend"]["enabled"])
        self.assertFalse(by_id["wallet_receive_or_spend"]["enabled"])
        self.assertFalse(by_id["nft_mint"]["enabled"])


if __name__ == "__main__":
    unittest.main()
