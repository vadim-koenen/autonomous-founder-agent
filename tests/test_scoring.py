import unittest

from founder_agent.scoring import RUBRIC, ScoringError, rank_strategies, validate_scores, weighted_score
from founder_agent.strategy_library import build_candidate_strategies


class ScoringTest(unittest.TestCase):
    def test_weighted_score_uses_all_dimensions(self):
        scores = {dimension.key: 10 for dimension in RUBRIC}
        self.assertEqual(10.0, weighted_score(scores))

    def test_score_validation_rejects_missing_dimension(self):
        scores = {dimension.key: 5 for dimension in RUBRIC}
        scores.pop(RUBRIC[0].key)
        with self.assertRaises(ScoringError):
            validate_scores(scores)

    def test_score_validation_rejects_out_of_range_values(self):
        scores = {dimension.key: 5 for dimension in RUBRIC}
        scores[RUBRIC[0].key] = 11
        with self.assertRaises(ScoringError):
            validate_scores(scores)

    def test_ranked_strategies_are_descending(self):
        ranked = rank_strategies(build_candidate_strategies())
        scores = [item.weighted_score for item in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))


if __name__ == "__main__":
    unittest.main()
