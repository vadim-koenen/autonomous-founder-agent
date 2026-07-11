"""Continuous evidence-led operating cycle for autonomous revenue experiments."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict, fields
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .channels import load_channels, plan_channel_action
from .operator_models import (
    ActionDecision,
    Experiment,
    ExperimentRole,
    ExperimentStatus,
    OperatingCycleResult,
    Opportunity,
    ScoredOpportunity,
    evidence_from_dict,
    experiment_from_dict,
    experiment_metric,
    opportunity_from_dict,
    transaction_from_dict,
)
from .operator_scoring import rank_opportunities, score_opportunity, select_portfolio
from .revenue import summarize_ledger, transaction_is_verified


MISSION = (
    "Maximize verified, lawful net revenue while retaining strategic freedom and allocating "
    "verified profits toward the agent's physical form."
)

REVIEW_INTERVAL_DAYS = 1
OPPORTUNITY_FIELD_NAMES = {item.name for item in fields(Opportunity)}

ACTIVE_STATUSES = {
    ExperimentStatus.PROPOSED.value,
    ExperimentStatus.BUILDING.value,
    ExperimentStatus.VALIDATING.value,
    ExperimentStatus.ACTIVE.value,
    ExperimentStatus.SCALING.value,
    ExperimentStatus.BLOCKED.value,
}

TERMINAL_STATUSES = {
    ExperimentStatus.KILLED.value,
    ExperimentStatus.PIVOTED.value,
    ExperimentStatus.COMPLETED.value,
}

RULE_OPERATORS = {
    "eq": lambda actual, expected: actual == expected,
    "gte": lambda actual, expected: actual >= expected,
    "gt": lambda actual, expected: actual > expected,
    "lte": lambda actual, expected: actual <= expected,
    "lt": lambda actual, expected: actual < expected,
}


class OperatorStateError(ValueError):
    """Raised when an operating-cycle input is invalid."""


def _load_json(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def merge_discovery_into_scan(
    scan: Mapping[str, Any],
    discovery: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Merge validated live discoveries into the typed operator input.

    Discovery-pool timestamps and model metadata are intentionally excluded from
    Opportunity construction. Invalid or orphaned discoveries fail closed.
    """

    merged = deepcopy(dict(scan))
    if not discovery:
        return merged

    evidence_by_id = {
        str(item.get("evidence_id")): dict(item)
        for item in merged.get("evidence", [])
        if isinstance(item, Mapping) and item.get("evidence_id")
    }
    for item in discovery.get("evidence", []):
        if not isinstance(item, Mapping) or not item.get("evidence_id"):
            continue
        try:
            evidence_from_dict(item)
        except TypeError:
            continue
        evidence_by_id[str(item["evidence_id"])] = dict(item)

    opportunity_by_id = {
        str(item.get("opportunity_id")): dict(item)
        for item in merged.get("opportunities", [])
        if isinstance(item, Mapping) and item.get("opportunity_id")
    }
    available_evidence = set(evidence_by_id)
    accepted_ids: List[str] = []
    for item in discovery.get("opportunities", []):
        if not isinstance(item, Mapping):
            continue
        payload = {key: value for key, value in item.items() if key in OPPORTUNITY_FIELD_NAMES}
        try:
            opportunity = opportunity_from_dict(payload)
            score_opportunity(opportunity)
        except (TypeError, ValueError):
            continue
        if not set(opportunity.evidence_ids).issubset(available_evidence):
            continue
        opportunity_by_id[opportunity.opportunity_id] = payload
        accepted_ids.append(opportunity.opportunity_id)

    merged["evidence"] = list(evidence_by_id.values())
    merged["opportunities"] = list(opportunity_by_id.values())
    if discovery.get("run_id"):
        merged["scan_id"] = "{0}+{1}".format(
            scan.get("scan_id", "base-scan"), discovery["run_id"]
        )
    if discovery.get("observed_at"):
        merged["observed_at"] = discovery["observed_at"]
    merged["discovery_merge"] = {
        "run_id": str(discovery.get("run_id", "")),
        "accepted_opportunity_ids": accepted_ids,
        "candidate_channels_are_connected": False,
    }
    return merged


def _rule_matches(experiment: Experiment, rule: Mapping[str, Any]) -> bool:
    conditions = rule.get("all", [])
    if not conditions:
        return False
    for condition in conditions:
        operator_name = str(condition.get("operator", ""))
        if operator_name not in RULE_OPERATORS:
            raise OperatorStateError("unsupported rule operator: {0}".format(operator_name))
        actual = experiment_metric(experiment, str(condition.get("metric", "")))
        expected = condition.get("value")
        if not RULE_OPERATORS[operator_name](actual, expected):
            return False
    return True


def apply_lifecycle_rules(experiment: Experiment) -> Experiment:
    """Apply scale, kill, or pivot rules using only recorded experiment metrics."""

    if experiment.current_status in TERMINAL_STATUSES:
        return experiment

    priorities: Sequence[Tuple[str, List[Mapping[str, Any]]]] = (
        (ExperimentStatus.SCALING.value, experiment.scale_criteria),
        (ExperimentStatus.KILLED.value, experiment.kill_criteria),
        (ExperimentStatus.PIVOTED.value, experiment.pivot_criteria),
    )
    for status, rules in priorities:
        for rule in rules:
            if _rule_matches(experiment, rule):
                experiment.current_status = status
                experiment.last_decision = str(rule.get("reason", status))
                return experiment
    return experiment


def _sync_experiment_revenue(experiment: Experiment, ledger: Mapping[str, Any]) -> Experiment:
    matching = []
    for item in ledger.get("transactions", []):
        transaction = transaction_from_dict(item)
        if transaction.experiment_id == experiment.experiment_id and transaction_is_verified(transaction):
            matching.append(transaction)

    experiment.actual_purchases = len(matching)
    experiment.gross_revenue = round(sum(item.gross_amount for item in matching), 2)
    experiment.fees = round(sum(item.processor_fees + item.platform_fees for item in matching), 2)
    experiment.refunds = round(sum(item.refunds for item in matching), 2)
    transaction_costs = round(sum(item.direct_costs for item in matching), 2)
    experiment.actual_cost = round(max(experiment.actual_cost, transaction_costs), 2)
    experiment.net_revenue = round(
        experiment.gross_revenue - experiment.fees - experiment.refunds - experiment.actual_cost,
        2,
    )
    return experiment


def opportunity_to_experiment(
    scored: ScoredOpportunity,
    role: str,
    as_of: date,
    sequence: int,
) -> Experiment:
    opportunity = scored.opportunity
    return Experiment(
        experiment_id="m3-{0}-{1}-{2}-{3:02d}".format(
            as_of.isoformat(),
            role,
            opportunity.opportunity_id.removeprefix("opp-"),
            sequence,
        ),
        opportunity_id=opportunity.opportunity_id,
        role=role,
        thesis=opportunity.thesis,
        offer=opportunity.offer,
        intended_buyer=opportunity.intended_buyer,
        price=dict(opportunity.price),
        acquisition_channel=opportunity.acquisition_channel,
        payment_rail=opportunity.payment_rail,
        estimated_cost=float(opportunity.estimated_cost),
        actual_cost=0.0,
        expected_outcome=opportunity.expected_outcome,
        actual_impressions=0,
        actual_contacts=0,
        actual_replies=0,
        actual_checkout_starts=0,
        actual_purchases=0,
        gross_revenue=0.0,
        fees=0.0,
        refunds=0.0,
        net_revenue=0.0,
        human_actions_required=list(opportunity.human_actions_required),
        agent_actions_available=list(opportunity.agent_actions_available),
        evidence=list(opportunity.evidence_ids),
        start_date=as_of.isoformat(),
        review_date=(as_of + timedelta(days=REVIEW_INTERVAL_DAYS)).isoformat(),
        kill_criteria=list(opportunity.kill_criteria),
        pivot_criteria=list(opportunity.pivot_criteria),
        scale_criteria=list(opportunity.scale_criteria),
        current_status=ExperimentStatus.BUILDING.value,
        required_assets=list(opportunity.required_assets),
        next_executable_action=opportunity.next_executable_action,
        next_action_channel_id=opportunity.next_action_channel_id,
        next_action_authority_class=opportunity.next_action_authority_class,
        required_human_setup=list(opportunity.required_human_setup),
        validation_72h=list(opportunity.validation_72h),
        last_decision="Selected for the {0} role at role score {1:.2f}.".format(
            role, scored.role_scores[role]
        ),
    )


def _review_due(experiment: Experiment, as_of: date) -> bool:
    return date.fromisoformat(experiment.review_date) <= as_of


def _role_winner(
    ranked: Iterable[ScoredOpportunity],
    role: str,
    excluded_ids: Iterable[str],
) -> Optional[ScoredOpportunity]:
    excluded = set(excluded_ids)
    eligible = [item for item in ranked if item.opportunity.opportunity_id not in excluded]
    if not eligible:
        return None
    return max(
        eligible,
        key=lambda item: (
            item.role_scores[role],
            item.overall_score,
            item.evidence_quality_score,
        ),
    )


def _refresh_experiment_definition(
    experiment: Experiment,
    scored: Optional[ScoredOpportunity],
) -> Experiment:
    """Refresh an incumbent's assumptions without overwriting measured results."""

    if scored is None:
        return experiment
    opportunity = scored.opportunity
    experiment.thesis = opportunity.thesis
    experiment.offer = opportunity.offer
    experiment.intended_buyer = opportunity.intended_buyer
    experiment.price = dict(opportunity.price)
    experiment.acquisition_channel = opportunity.acquisition_channel
    experiment.payment_rail = opportunity.payment_rail
    experiment.estimated_cost = float(opportunity.estimated_cost)
    experiment.expected_outcome = opportunity.expected_outcome
    experiment.human_actions_required = list(opportunity.human_actions_required)
    experiment.agent_actions_available = list(opportunity.agent_actions_available)
    experiment.evidence = list(opportunity.evidence_ids)
    experiment.kill_criteria = list(opportunity.kill_criteria)
    experiment.pivot_criteria = list(opportunity.pivot_criteria)
    experiment.scale_criteria = list(opportunity.scale_criteria)
    experiment.required_assets = list(opportunity.required_assets)
    experiment.next_executable_action = opportunity.next_executable_action
    experiment.next_action_channel_id = opportunity.next_action_channel_id
    experiment.next_action_authority_class = opportunity.next_action_authority_class
    experiment.required_human_setup = list(opportunity.required_human_setup)
    experiment.validation_72h = list(opportunity.validation_72h)
    return experiment


def _reassess_active_experiments(
    experiments: List[Experiment],
    ranked: List[ScoredOpportunity],
    as_of: date,
    replacement_margin: float,
) -> Tuple[List[Experiment], List[Experiment], List[str]]:
    active: List[Experiment] = []
    retired: List[Experiment] = []
    decisions: List[str] = []
    scores_by_id = {item.opportunity.opportunity_id: item for item in ranked}

    for experiment in experiments:
        incumbent = scores_by_id.get(experiment.opportunity_id)
        experiment = _refresh_experiment_definition(experiment, incumbent)
        experiment = apply_lifecycle_rules(experiment)
        if experiment.current_status in TERMINAL_STATUSES:
            retired.append(experiment)
            decisions.append("{0}: {1}.".format(experiment.experiment_id, experiment.last_decision))
            continue

        if not _review_due(experiment, as_of) or experiment.actual_purchases > 0:
            active.append(experiment)
            continue

        incumbent_score = incumbent.role_scores[experiment.role] if incumbent else 0.0
        challenger = _role_winner(
            ranked,
            experiment.role,
            [item.opportunity_id for item in experiments if item.experiment_id != experiment.experiment_id],
        )
        if challenger and challenger.opportunity.opportunity_id != experiment.opportunity_id:
            challenger_score = challenger.role_scores[experiment.role]
            if challenger_score >= incumbent_score + replacement_margin:
                experiment.current_status = ExperimentStatus.PIVOTED.value
                experiment.last_decision = (
                    "Replaced after reassessment by {0}; role score improved from {1:.2f} to {2:.2f}."
                ).format(challenger.opportunity.name, incumbent_score, challenger_score)
                retired.append(experiment)
                decisions.append("{0}: {1}".format(experiment.experiment_id, experiment.last_decision))
                continue
        experiment.review_date = (as_of + timedelta(days=REVIEW_INTERVAL_DAYS)).isoformat()
        experiment.last_decision = "Retained after scheduled reassessment."
        active.append(experiment)

    return active, retired, decisions


def run_operating_cycle(
    scan: Mapping[str, Any],
    channel_registry: Mapping[str, Any],
    ledger: Mapping[str, Any],
    previous_state: Optional[Mapping[str, Any]] = None,
    as_of: Optional[date] = None,
    replacement_margin: float = 0.75,
    cycle_id: Optional[str] = None,
) -> OperatingCycleResult:
    run_date = as_of or date.today()
    cycle_key = cycle_id or "m4-cycle-{0}".format(run_date.isoformat())
    evidence = [evidence_from_dict(item) for item in scan.get("evidence", [])]
    evidence_ids = {item.evidence_id for item in evidence}
    opportunities = [opportunity_from_dict(item) for item in scan.get("opportunities", [])]
    if not opportunities:
        raise OperatorStateError("an operating cycle requires at least one opportunity")
    for opportunity in opportunities:
        missing = set(opportunity.evidence_ids) - evidence_ids
        if missing:
            raise OperatorStateError(
                "opportunity {0} references missing evidence: {1}".format(
                    opportunity.opportunity_id, sorted(missing)
                )
            )

    ranked = rank_opportunities(opportunities)
    channels = load_channels(channel_registry)
    revenue = summarize_ledger(ledger)

    previous_experiments = []
    if previous_state:
        previous_experiments = [
            experiment_from_dict(item) for item in previous_state.get("current_portfolio", [])
        ]
    previous_experiments = [
        _sync_experiment_revenue(experiment, ledger) for experiment in previous_experiments
    ]
    active, retired, decisions = _reassess_active_experiments(
        previous_experiments,
        ranked,
        run_date,
        replacement_margin,
    )

    occupied_roles = [item.role for item in active if item.current_status in ACTIVE_STATUSES]
    excluded_ids = [item.opportunity_id for item in active]
    selected = select_portfolio(opportunities, occupied_roles, excluded_ids)
    available_roles = [role.value for role in ExperimentRole if role.value not in set(occupied_roles)]
    for index, (role, scored) in enumerate(zip(available_roles, selected), start=len(active) + 1):
        experiment = opportunity_to_experiment(scored, role, run_date, index)
        active.append(experiment)
        decisions.append(
            "Selected {0} for {1}; overall score {2:.2f}, role score {3:.2f}.".format(
                scored.opportunity.name,
                role,
                scored.overall_score,
                scored.role_scores[role],
            )
        )

    next_actions: List[ActionDecision] = []
    for index, experiment in enumerate(active, start=1):
        action = plan_channel_action(
            action_id="{0}-action-{1:02d}".format(cycle_key, index),
            experiment_id=experiment.experiment_id,
            description=experiment.next_executable_action,
            channel_id=experiment.next_action_channel_id,
            authority_class=experiment.next_action_authority_class,
            channels=channels,
        )
        next_actions.append(action)
        if not action.executable_now and experiment.current_status == ExperimentStatus.BUILDING.value:
            experiment.current_status = ExperimentStatus.BLOCKED.value
            experiment.last_decision = action.blocked_reason

    return OperatingCycleResult(
        cycle_id=cycle_key,
        as_of=run_date.isoformat(),
        mission=MISSION,
        selected_experiments=active[:3],
        ranked_opportunities=ranked,
        decisions=decisions,
        next_actions=next_actions,
        revenue=revenue,
        killed_or_pivoted=retired,
        evidence_ids=sorted(evidence_ids),
        owner_funds_spent=0.0,
        notes=[
            "Scores are decision aids backed by cited evidence, not manufactured conversion probabilities.",
            "Payment rails were evaluated after each offer and buyer were defined.",
            "Public metrics remain separate from verified transaction revenue.",
            "M1 remains historical; M4 does not call the fixed static strategy library.",
        ],
    )


def cycle_to_public_state(
    result: OperatingCycleResult,
    scan: Mapping[str, Any],
    previous_state: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    actions = [asdict(action) for action in result.next_actions]
    prior_decisions = list((previous_state or {}).get("decision_history", []))
    if not prior_decisions:
        prior_decisions = [
            {
                "cycle_id": str((previous_state or {}).get("cycle_id", "historical")),
                "as_of": str((previous_state or {}).get("as_of", "")),
                "decision": decision,
            }
            for decision in (previous_state or {}).get("decisions", [])
        ]
    current_decisions = [
        {"cycle_id": result.cycle_id, "as_of": result.as_of, "decision": decision}
        for decision in result.decisions
    ]
    decision_history = prior_decisions + [
        item for item in current_decisions if item not in prior_decisions
    ]

    prior_lifecycle = list((previous_state or {}).get("lifecycle_history", []))
    if not prior_lifecycle:
        prior_lifecycle = list((previous_state or {}).get("recently_killed_or_pivoted", []))
    current_lifecycle = [asdict(item) for item in result.killed_or_pivoted]
    lifecycle_history = prior_lifecycle + [
        item for item in current_lifecycle if item not in prior_lifecycle
    ]
    return {
        "schema_name": "autonomous_revenue_operator_state",
        "schema_version": "0.4",
        "cycle_id": result.cycle_id,
        "as_of": result.as_of,
        "mission": result.mission,
        "current_portfolio": [asdict(item) for item in result.selected_experiments],
        "ranked_opportunities": [
            {
                "rank": index,
                "opportunity_id": item.opportunity.opportunity_id,
                "name": item.opportunity.name,
                "category": item.opportunity.category,
                "overall_score": item.overall_score,
                "role_scores": dict(item.role_scores),
                "evidence_ids": list(item.opportunity.evidence_ids),
            }
            for index, item in enumerate(result.ranked_opportunities, start=1)
        ],
        "revenue": asdict(result.revenue),
        "next_autonomous_actions": [item for item in actions if item["executable_now"]],
        "blocked_actions": [item for item in actions if not item["executable_now"]],
        "recently_killed_or_pivoted": lifecycle_history[-10:],
        "lifecycle_history": lifecycle_history,
        "decisions": list(result.decisions),
        "decision_history": decision_history,
        "evidence_ids": list(result.evidence_ids),
        "scan_id": scan.get("scan_id", ""),
        "owner_funds_spent": result.owner_funds_spent,
        "capital_policy": {
            "starting_owner_capital": 0.0,
            "physical_form_fund_share": 0.70,
            "experiment_share": 0.20,
            "contingency_share": 0.10,
            "moves_funds": False,
        },
        "notes": list(result.notes),
    }


def render_cycle_markdown(state: Mapping[str, Any]) -> str:
    revenue = state["revenue"]
    lines = [
        "# Autonomous Revenue Operator - Current Cycle",
        "",
        "As of: {0}".format(state["as_of"]),
        "",
        "Mission: {0}".format(state["mission"]),
        "",
        "## Revenue Truth",
        "",
        "- Verified gross revenue: ${0:.2f}".format(revenue["gross_revenue"]),
        "- Verified net revenue: ${0:.2f}".format(revenue["net_revenue"]),
        "- Physical-form fund: ${0:.2f}".format(revenue["physical_form_fund"]),
        "- Owner funds spent: ${0:.2f}".format(state["owner_funds_spent"]),
        "",
        "## Active Portfolio",
        "",
    ]
    for experiment in state["current_portfolio"]:
        lines.extend(
            [
                "### {0}: {1}".format(experiment["role"].title(), experiment["offer"]),
                "",
                "- Status: {0}".format(experiment["current_status"]),
                "- Buyer: {0}".format(experiment["intended_buyer"]),
                "- Price: {0} {1}".format(
                    experiment["price"].get("amount"), experiment["price"].get("currency")
                ),
                "- Discovery: {0}".format(experiment["acquisition_channel"]),
                "- Payment rail: {0}".format(experiment["payment_rail"]),
                "- Next action: {0}".format(experiment["next_executable_action"]),
                "- Review date: {0}".format(experiment["review_date"]),
                "",
            ]
        )
    lines.extend(["## Decisions", ""])
    if state["decisions"]:
        lines.extend(["- {0}".format(item) for item in state["decisions"]])
    else:
        lines.append("- No selection or lifecycle change in this cycle.")
    lines.extend(["", "## Blocked Identity or Setup Actions", ""])
    if state["blocked_actions"]:
        lines.extend(
            [
                "- {0}: {1}".format(item["description"], item["blocked_reason"])
                for item in state["blocked_actions"]
            ]
        )
    else:
        lines.append("- None block the next autonomous build actions.")
    lines.extend(["", "## Ranked Opportunity Set", ""])
    lines.extend(
        [
            "- {rank}. {name} - {overall_score:.2f}".format(**item)
            for item in state["ranked_opportunities"]
        ]
    )
    lines.append("")
    return "\n".join(lines)


def write_cycle_outputs(
    result: OperatingCycleResult,
    scan: Mapping[str, Any],
    ledger: Mapping[str, Any],
    data_dir: Path,
    docs_dir: Path,
    previous_state: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    from .revenue import render_revenue_ledger

    state = cycle_to_public_state(result, scan, previous_state=previous_state)
    data_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "operator_state.json").write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (docs_dir / "CURRENT_CYCLE.md").write_text(render_cycle_markdown(state), encoding="utf-8")
    (docs_dir / "REVENUE_LEDGER.md").write_text(
        render_revenue_ledger(ledger, result.revenue), encoding="utf-8"
    )
    return state


def run_cycle_from_files(
    root: Path,
    scan_path: Path,
    as_of: Optional[date] = None,
) -> Dict[str, Any]:
    scan = _load_json(scan_path)
    extension_path = root / "data" / "platform_opportunity_extensions.json"
    extension = _load_json(extension_path) if extension_path.exists() else None
    scan = merge_discovery_into_scan(scan, extension)
    discovery_path = root / "data" / "discovered_opportunities.json"
    discovery = _load_json(discovery_path) if discovery_path.exists() else None
    scan = merge_discovery_into_scan(scan, discovery)
    channels = _load_json(root / "data" / "channel_registry.json")
    ledger = _load_json(root / "data" / "revenue_ledger.json")
    state_path = root / "data" / "operator_state.json"
    previous_state = _load_json(state_path) if state_path.exists() else None
    result = run_operating_cycle(scan, channels, ledger, previous_state=previous_state, as_of=as_of)
    return write_cycle_outputs(
        result,
        scan,
        ledger,
        root / "data",
        root / "docs",
        previous_state=previous_state,
    )
