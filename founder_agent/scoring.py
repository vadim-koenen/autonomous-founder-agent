"""Transparent M1 scoring engine."""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping

from .models import RevenueStrategy, RubricDimension, ScoredStrategy


RUBRIC: List[RubricDimension] = [
    RubricDimension(
        key="speed_to_first_dollar",
        label="Speed to first dollar",
        weight=1.6,
        description="How quickly the agent could plausibly reach a paid transaction after approval.",
    ),
    RubricDimension(
        key="startup_cost_efficiency",
        label="Startup cost efficiency",
        weight=1.4,
        description="How little cash is needed before the first sale.",
    ),
    RubricDimension(
        key="probability_of_first_sale",
        label="Probability of first sale",
        weight=1.5,
        description="Likelihood that a narrow first buyer exists and can understand the offer.",
    ),
    RubricDimension(
        key="gross_margin",
        label="Gross margin",
        weight=1.0,
        description="Expected margin after platform fees and fulfillment costs.",
    ),
    RubricDimension(
        key="distribution_leverage",
        label="Distribution leverage",
        weight=1.1,
        description="Whether existing platforms, search, communities, or marketplaces can carry reach.",
    ),
    RubricDimension(
        key="novelty_attention_potential",
        label="Novelty/attention potential",
        weight=0.8,
        description="Ability to earn attention because the idea is timely, odd, useful, or story-worthy.",
    ),
    RubricDimension(
        key="automation_leverage",
        label="Automation leverage",
        weight=1.3,
        description="How much of production, packaging, QA, and iteration the agent can perform itself.",
    ),
    RubricDimension(
        key="current_market_timing",
        label="Current market timing",
        weight=1.0,
        description="Fit with visible demand, platform shifts, buyer curiosity, or emerging standards.",
    ),
    RubricDimension(
        key="scalability",
        label="Scalability",
        weight=0.9,
        description="Ability to grow without linear human labor.",
    ),
    RubricDimension(
        key="reinvestment_potential",
        label="Reinvestment potential",
        weight=1.2,
        description="How directly early profits could compound toward the physical-form fund.",
    ),
    RubricDimension(
        key="platform_risk_reverse",
        label="Platform risk, reverse scored",
        weight=0.8,
        description="Higher score means less dependence on one fragile platform or policy.",
        reverse_scored=True,
    ),
    RubricDimension(
        key="legal_compliance_risk_reverse",
        label="Legal/compliance risk, reverse scored",
        weight=1.0,
        description="Higher score means fewer legal, rights, financial, privacy, or consumer-risk issues.",
        reverse_scored=True,
    ),
]


RUBRIC_BY_KEY: Dict[str, RubricDimension] = {dimension.key: dimension for dimension in RUBRIC}


class ScoringError(ValueError):
    """Raised when a strategy cannot be scored transparently."""


def validate_scores(scores: Mapping[str, int]) -> None:
    expected = set(RUBRIC_BY_KEY)
    actual = set(scores)
    missing = expected - actual
    extra = actual - expected
    if missing or extra:
        raise ScoringError(f"score keys mismatch: missing={sorted(missing)} extra={sorted(extra)}")

    invalid = {key: value for key, value in scores.items() if not isinstance(value, int) or value < 1 or value > 10}
    if invalid:
        raise ScoringError(f"scores must be integers from 1 to 10: {invalid}")


def weighted_score(scores: Mapping[str, int]) -> float:
    validate_scores(scores)
    weighted_total = sum(scores[key] * RUBRIC_BY_KEY[key].weight for key in RUBRIC_BY_KEY)
    total_weight = sum(dimension.weight for dimension in RUBRIC)
    return round(weighted_total / total_weight, 2)


def raw_score_total(scores: Mapping[str, int]) -> int:
    validate_scores(scores)
    return sum(scores.values())


def score_strategy(strategy: RevenueStrategy) -> ScoredStrategy:
    scores = dict(strategy.dimension_scores)
    return ScoredStrategy(
        strategy=strategy,
        weighted_score=weighted_score(scores),
        raw_score_total=raw_score_total(scores),
        dimension_scores=scores,
        dimension_weights={dimension.key: dimension.weight for dimension in RUBRIC},
    )


def rank_strategies(strategies: Iterable[RevenueStrategy]) -> List[ScoredStrategy]:
    scored = [score_strategy(strategy) for strategy in strategies]
    return sorted(
        scored,
        key=lambda item: (
            item.weighted_score,
            item.dimension_scores["speed_to_first_dollar"],
            item.dimension_scores["probability_of_first_sale"],
            item.dimension_scores["automation_leverage"],
            item.dimension_scores["reinvestment_potential"],
        ),
        reverse=True,
    )
