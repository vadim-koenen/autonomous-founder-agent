"""Evidence-weighted opportunity scoring for M3 operating cycles."""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping

from .operator_models import ExperimentRole, Opportunity, ScoredOpportunity


OPPORTUNITY_WEIGHTS: Dict[str, float] = {
    "observable_buyer_demand": 1.5,
    "reachable_buyers": 1.4,
    "time_to_first_verified_dollar": 1.5,
    "startup_cost_efficiency": 1.2,
    "expected_net_revenue": 1.2,
    "agent_execution_fit": 1.3,
    "distribution_access": 1.2,
    "competition_resilience": 0.8,
    "free_substitute_resilience": 0.9,
    "differentiation": 1.0,
    "gross_margin": 0.8,
    "repeatability": 0.8,
    "scalability": 0.7,
    "legal_platform_feasibility": 0.9,
    "low_human_dependency": 0.8,
    "opportunity_cost_efficiency": 0.8,
    "evidence_quality": 1.4,
}


class OperatorScoringError(ValueError):
    """Raised when an externally supplied opportunity cannot be scored."""


def validate_opportunity_scores(scores: Mapping[str, float]) -> None:
    expected = set(OPPORTUNITY_WEIGHTS)
    actual = set(scores)
    missing = expected - actual
    extra = actual - expected
    if missing or extra:
        raise OperatorScoringError(
            "score keys mismatch: missing={0} extra={1}".format(sorted(missing), sorted(extra))
        )
    invalid = {
        key: value
        for key, value in scores.items()
        if not isinstance(value, (int, float)) or value < 1 or value > 10
    }
    if invalid:
        raise OperatorScoringError("scores must be numbers from 1 to 10: {0}".format(invalid))


def validate_role_fit(role_fit: Mapping[str, float]) -> None:
    expected = {role.value for role in ExperimentRole}
    actual = set(role_fit)
    if expected != actual:
        raise OperatorScoringError(
            "role fit keys mismatch: missing={0} extra={1}".format(
                sorted(expected - actual), sorted(actual - expected)
            )
        )
    invalid = {
        key: value
        for key, value in role_fit.items()
        if not isinstance(value, (int, float)) or value < 1 or value > 10
    }
    if invalid:
        raise OperatorScoringError("role fit values must be numbers from 1 to 10: {0}".format(invalid))


def opportunity_score(scores: Mapping[str, float]) -> float:
    validate_opportunity_scores(scores)
    weighted_total = sum(scores[key] * OPPORTUNITY_WEIGHTS[key] for key in OPPORTUNITY_WEIGHTS)
    total_weight = sum(OPPORTUNITY_WEIGHTS.values())
    return round(weighted_total / total_weight, 2)


def score_opportunity(opportunity: Opportunity) -> ScoredOpportunity:
    validate_opportunity_scores(opportunity.scores)
    validate_role_fit(opportunity.role_fit)
    overall = opportunity_score(opportunity.scores)
    role_scores = {
        role.value: round((overall * 0.75) + (float(opportunity.role_fit[role.value]) * 0.25), 2)
        for role in ExperimentRole
    }
    return ScoredOpportunity(
        opportunity=opportunity,
        overall_score=overall,
        role_scores=role_scores,
        evidence_quality_score=float(opportunity.scores["evidence_quality"]),
    )


def rank_opportunities(opportunities: Iterable[Opportunity]) -> List[ScoredOpportunity]:
    scored = [score_opportunity(opportunity) for opportunity in opportunities]
    return sorted(
        scored,
        key=lambda item: (
            item.overall_score,
            item.evidence_quality_score,
            item.opportunity.scores["observable_buyer_demand"],
            item.opportunity.scores["time_to_first_verified_dollar"],
        ),
        reverse=True,
    )


def select_portfolio(
    opportunities: Iterable[Opportunity],
    occupied_roles: Iterable[str] = (),
    excluded_opportunity_ids: Iterable[str] = (),
) -> List[ScoredOpportunity]:
    """Select one evidence-ranked candidate for each unoccupied portfolio role."""

    occupied = set(occupied_roles)
    excluded = set(excluded_opportunity_ids)
    scored = [item for item in rank_opportunities(opportunities) if item.opportunity.opportunity_id not in excluded]
    selected: List[ScoredOpportunity] = []
    used_ids = set(excluded)

    for role in ExperimentRole:
        if role.value in occupied:
            continue
        eligible = [item for item in scored if item.opportunity.opportunity_id not in used_ids]
        if not eligible:
            break
        winner = max(
            eligible,
            key=lambda item: (
                item.role_scores[role.value],
                item.overall_score,
                item.evidence_quality_score,
            ),
        )
        selected.append(winner)
        used_ids.add(winner.opportunity.opportunity_id)

    return selected
