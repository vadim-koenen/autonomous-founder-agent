import unittest
from datetime import date

from founder_agent.m1 import run_m1_decision_system
from founder_agent.models import StrategyCategory
from founder_agent.scoring import RUBRIC_BY_KEY
from founder_agent.strategy_library import build_candidate_strategies


class M1DecisionSystemTest(unittest.TestCase):
    def test_generates_at_least_30_strategies(self):
        strategies = build_candidate_strategies()
        self.assertGreaterEqual(len(strategies), 30)

    def test_required_strategy_categories_are_present(self):
        categories = {strategy.category for strategy in build_candidate_strategies()}
        self.assertIn(StrategyCategory.DIGITAL_COLLECTIBLE, categories)
        self.assertIn(StrategyCategory.AGENT_TO_AGENT, categories)
        self.assertIn(StrategyCategory.DIGITAL_PRODUCT, categories)
        self.assertIn(StrategyCategory.ATTENTION, categories)
        self.assertIn(StrategyCategory.MARKETPLACE, categories)

    def test_all_strategies_have_complete_scores(self):
        expected = set(RUBRIC_BY_KEY)
        for strategy in build_candidate_strategies():
            self.assertEqual(expected, set(strategy.dimension_scores), strategy.strategy_id)
            for value in strategy.dimension_scores.values():
                self.assertIsInstance(value, int)
                self.assertGreaterEqual(value, 1)
                self.assertLessEqual(value, 10)

    def test_no_strategy_is_bound_to_user_business(self):
        for strategy in build_candidate_strategies():
            self.assertTrue(strategy.not_user_business_bound, strategy.strategy_id)
            text = " ".join(
                [
                    strategy.name,
                    strategy.thesis,
                    strategy.target_buyer,
                    strategy.first_offer,
                    strategy.score_notes,
                ]
            ).lower()
            self.assertNotIn("krs", text)

    def test_run_selects_top_3_and_primary(self):
        run = run_m1_decision_system(as_of=date(2026, 7, 9))
        self.assertGreaterEqual(run.candidate_count, 30)
        self.assertEqual(3, len(run.top_3))
        self.assertEqual(run.top_3[0], run.primary_experiment)
        self.assertEqual("afa-001", run.primary_experiment.strategy.strategy_id)


if __name__ == "__main__":
    unittest.main()
