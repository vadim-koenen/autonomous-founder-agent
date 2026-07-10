import copy
import json
import unittest
from dataclasses import asdict
from datetime import date
from pathlib import Path

from founder_agent.operator import (
    apply_lifecycle_rules,
    cycle_to_public_state,
    opportunity_to_experiment,
    run_operating_cycle,
)
from founder_agent.operator_models import ExperimentStatus, TransactionRecord, opportunity_from_dict
from founder_agent.operator_scoring import OPPORTUNITY_WEIGHTS, score_opportunity
from founder_agent.revenue import summarize_ledger, summarize_transactions


ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


class M3OperatorTest(unittest.TestCase):
    def setUp(self):
        self.scan = load_json("data/opportunity_scan_2026-07-09.json")
        self.channels = load_json("data/channel_registry.json")
        self.ledger = load_json("data/revenue_ledger.json")

    def test_current_scan_selects_three_roles_and_x402_sprint_loses(self):
        result = run_operating_cycle(
            self.scan,
            self.channels,
            self.ledger,
            previous_state=None,
            as_of=date(2026, 7, 9),
        )

        self.assertEqual({"cash", "asset", "frontier"}, {item.role for item in result.selected_experiments})
        selected_ids = {item.opportunity_id for item in result.selected_experiments}
        self.assertNotIn("opp-x402-sprint", selected_ids)
        self.assertIn("opp-agent-launch-qa", selected_ids)
        self.assertIn("opp-agent-launch-gate", selected_ids)
        self.assertIn("opp-x402-opportunity-pulse", selected_ids)

    def test_category_is_not_hard_coded_and_collectible_can_win(self):
        scan = copy.deepcopy(self.scan)
        for opportunity in scan["opportunities"]:
            opportunity["scores"] = {key: 1 for key in OPPORTUNITY_WEIGHTS}
            opportunity["role_fit"] = {"cash": 1, "asset": 1, "frontier": 1}
            if opportunity["opportunity_id"] == "opp-embodiment-collectible":
                opportunity["scores"] = {key: 10 for key in OPPORTUNITY_WEIGHTS}
                opportunity["role_fit"] = {"cash": 10, "asset": 10, "frontier": 10}

        result = run_operating_cycle(
            scan,
            self.channels,
            self.ledger,
            previous_state=None,
            as_of=date(2026, 7, 9),
        )

        cash = next(item for item in result.selected_experiments if item.role == "cash")
        self.assertEqual("opp-embodiment-collectible", cash.opportunity_id)

    def test_experiment_can_be_killed_and_scaled(self):
        opportunity = opportunity_from_dict(self.scan["opportunities"][0])

        killed = opportunity_to_experiment(
            score_opportunity(opportunity), "cash", date(2026, 7, 9), 1
        )
        killed.actual_contacts = 25
        killed.actual_replies = 0
        self.assertEqual(ExperimentStatus.KILLED.value, apply_lifecycle_rules(killed).current_status)

        scaled = opportunity_to_experiment(
            score_opportunity(opportunity), "cash", date(2026, 7, 9), 2
        )
        scaled.actual_purchases = 3
        scaled.net_revenue = 300
        self.assertEqual(ExperimentStatus.SCALING.value, apply_lifecycle_rules(scaled).current_status)

    def test_due_incumbent_is_reassessed_and_replaced(self):
        first = run_operating_cycle(
            self.scan,
            self.channels,
            self.ledger,
            previous_state=None,
            as_of=date(2026, 7, 9),
        )
        previous = {"current_portfolio": [asdict(item) for item in first.selected_experiments]}
        for item in previous["current_portfolio"]:
            item["current_status"] = "validating"
            item["review_date"] = "2026-07-10"

        rescanned = copy.deepcopy(self.scan)
        for opportunity in rescanned["opportunities"]:
            if opportunity["opportunity_id"] == "opp-x402-opportunity-pulse":
                opportunity["scores"] = {key: 1 for key in OPPORTUNITY_WEIGHTS}
                opportunity["role_fit"]["frontier"] = 1
            if opportunity["opportunity_id"] == "opp-x402-sprint":
                opportunity["role_fit"]["frontier"] = 10

        second = run_operating_cycle(
            rescanned,
            self.channels,
            self.ledger,
            previous_state=previous,
            as_of=date(2026, 7, 13),
        )

        retired_ids = {item.opportunity_id for item in second.killed_or_pivoted}
        frontier = next(item for item in second.selected_experiments if item.role == "frontier")
        self.assertIn("opp-x402-opportunity-pulse", retired_ids)
        self.assertEqual("opp-x402-sprint", frontier.opportunity_id)
        experiment_ids = [item.experiment_id for item in second.selected_experiments]
        self.assertEqual(len(experiment_ids), len(set(experiment_ids)))
        self.assertNotIn(
            frontier.experiment_id,
            {item.experiment_id for item in second.killed_or_pivoted},
        )

    def test_decision_history_survives_a_no_change_cycle(self):
        first = run_operating_cycle(
            self.scan,
            self.channels,
            self.ledger,
            previous_state=None,
            as_of=date(2026, 7, 9),
        )
        first_state = cycle_to_public_state(first, self.scan)
        first_state["current_portfolio"][0]["next_executable_action"] = "stale action"
        second = run_operating_cycle(
            self.scan,
            self.channels,
            self.ledger,
            previous_state=first_state,
            as_of=date(2026, 7, 10),
        )
        second_state = cycle_to_public_state(second, self.scan, previous_state=first_state)

        self.assertEqual(3, len(first_state["decision_history"]))
        self.assertEqual(first_state["decision_history"], second_state["decision_history"])
        current_cash_action = self.scan["opportunities"][0]["next_executable_action"]
        cash = next(item for item in second_state["current_portfolio"] if item["role"] == "cash")
        self.assertEqual(current_cash_action, cash["next_executable_action"])

    def test_public_metrics_and_unverified_records_cannot_increase_revenue(self):
        ledger = {
            "currency": "USD",
            "public_metrics": {"impressions": 100000, "calls": 50000, "replies": 20},
            "transactions": [
                {
                    "transaction_id": "unverified-1",
                    "experiment_id": "m3-test",
                    "occurred_at": "2026-07-09",
                    "status": "completed",
                    "verification_reference": "",
                    "verified_at": "",
                    "currency": "USD",
                    "gross_amount": 9999,
                    "processor_fees": 0,
                    "platform_fees": 0,
                    "refunds": 0,
                    "direct_costs": 0,
                    "notes": "Public interest is not settlement evidence."
                }
            ]
        }

        summary = summarize_ledger(ledger)
        self.assertEqual(0, summary.verified_transactions)
        self.assertEqual(0.0, summary.gross_revenue)
        self.assertEqual(0.0, summary.net_revenue)

    def test_fees_refunds_and_costs_reduce_net_revenue(self):
        transaction = TransactionRecord(
            transaction_id="verified-1",
            experiment_id="m3-test",
            occurred_at="2026-07-09",
            status="completed",
            verification_reference="provider-order-public-safe-1",
            verified_at="2026-07-09T12:00:00Z",
            currency="USD",
            gross_amount=149,
            processor_fees=5,
            platform_fees=2,
            refunds=1,
            direct_costs=10,
        )

        summary = summarize_transactions([transaction])
        self.assertEqual(149.0, summary.gross_revenue)
        self.assertEqual(131.0, summary.net_revenue)
        self.assertEqual(91.7, summary.physical_form_fund)


if __name__ == "__main__":
    unittest.main()
