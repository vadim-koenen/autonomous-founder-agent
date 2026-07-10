"""Data models for the continuous Autonomous Revenue Operator."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional


class AuthorityClass(str, Enum):
    AUTONOMOUS = "autonomous"
    PREAUTHORIZED_WHEN_CONNECTED = "preauthorized_when_connected"
    HUMAN_IDENTITY_REQUIRED = "human_identity_required"


class ExperimentRole(str, Enum):
    CASH = "cash"
    ASSET = "asset"
    FRONTIER = "frontier"


class ExperimentStatus(str, Enum):
    PROPOSED = "proposed"
    BUILDING = "building"
    VALIDATING = "validating"
    ACTIVE = "active"
    SCALING = "scaling"
    PIVOTED = "pivoted"
    KILLED = "killed"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class ChannelKind(str, Enum):
    DISCOVERY = "discovery"
    DISTRIBUTION = "distribution"
    MARKETPLACE = "marketplace"
    HUMAN_PAYMENT = "human_payment"
    AGENT_NATIVE_PAYMENT = "agent_native_payment"
    PUBLISHING = "publishing"
    FULFILLMENT = "fulfillment"


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    title: str
    source_url: str
    observed_at: str
    summary: str
    quality: str
    signals: Mapping[str, Any]
    caveats: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Opportunity:
    opportunity_id: str
    name: str
    category: str
    thesis: str
    offer: str
    intended_buyer: str
    price: Mapping[str, Any]
    acquisition_channel: str
    payment_rail: str
    estimated_cost: float
    expected_outcome: str
    human_actions_required: List[str]
    agent_actions_available: List[str]
    evidence_ids: List[str]
    free_substitutes: List[str]
    scores: Mapping[str, float]
    role_fit: Mapping[str, float]
    required_assets: List[str]
    next_executable_action: str
    next_action_channel_id: str
    next_action_authority_class: str
    required_human_setup: List[str]
    validation_72h: List[str]
    kill_criteria: List[Mapping[str, Any]]
    pivot_criteria: List[Mapping[str, Any]]
    scale_criteria: List[Mapping[str, Any]]


@dataclass
class Experiment:
    experiment_id: str
    opportunity_id: str
    role: str
    thesis: str
    offer: str
    intended_buyer: str
    price: Mapping[str, Any]
    acquisition_channel: str
    payment_rail: str
    estimated_cost: float
    actual_cost: float
    expected_outcome: str
    actual_impressions: int
    actual_contacts: int
    actual_replies: int
    actual_checkout_starts: int
    actual_purchases: int
    gross_revenue: float
    fees: float
    refunds: float
    net_revenue: float
    human_actions_required: List[str]
    agent_actions_available: List[str]
    evidence: List[str]
    start_date: str
    review_date: str
    kill_criteria: List[Mapping[str, Any]]
    pivot_criteria: List[Mapping[str, Any]]
    scale_criteria: List[Mapping[str, Any]]
    current_status: str
    required_assets: List[str]
    next_executable_action: str
    next_action_channel_id: str
    next_action_authority_class: str
    required_human_setup: List[str]
    validation_72h: List[str]
    last_decision: str = "selected"


@dataclass(frozen=True)
class ChannelRecord:
    channel_id: str
    name: str
    kinds: List[str]
    account_exists: Optional[bool]
    human_verification_required: bool
    agent_has_access: bool
    authority_class: str
    permitted_actions: List[str]
    costs: str
    platform_restrictions: List[str]
    current_status: str
    source_url: str
    last_checked: str


@dataclass(frozen=True)
class TransactionRecord:
    transaction_id: str
    experiment_id: str
    occurred_at: str
    status: str
    verification_reference: str
    verified_at: str
    currency: str
    gross_amount: float
    processor_fees: float
    platform_fees: float
    refunds: float
    direct_costs: float
    notes: str = ""


@dataclass(frozen=True)
class RevenueSummary:
    currency: str
    verified_transactions: int
    gross_revenue: float
    processor_fees: float
    platform_fees: float
    refunds: float
    direct_costs: float
    net_revenue: float
    physical_form_fund: float
    reinvestment_balance: float
    contingency_reserve: float


@dataclass(frozen=True)
class ScoredOpportunity:
    opportunity: Opportunity
    overall_score: float
    role_scores: Mapping[str, float]
    evidence_quality_score: float


@dataclass(frozen=True)
class ActionDecision:
    action_id: str
    experiment_id: str
    description: str
    authority_class: str
    channel_id: str
    executable_now: bool
    blocked_reason: str = ""


@dataclass(frozen=True)
class OperatingCycleResult:
    cycle_id: str
    as_of: str
    mission: str
    selected_experiments: List[Experiment]
    ranked_opportunities: List[ScoredOpportunity]
    decisions: List[str]
    next_actions: List[ActionDecision]
    revenue: RevenueSummary
    killed_or_pivoted: List[Experiment]
    evidence_ids: List[str]
    owner_funds_spent: float
    notes: List[str] = field(default_factory=list)


def experiment_metric(experiment: Experiment, metric: str) -> Any:
    if not hasattr(experiment, metric):
        raise KeyError("unknown experiment metric: {0}".format(metric))
    return getattr(experiment, metric)


def experiment_from_dict(data: Mapping[str, Any]) -> Experiment:
    return Experiment(**dict(data))


def opportunity_from_dict(data: Mapping[str, Any]) -> Opportunity:
    return Opportunity(**dict(data))


def evidence_from_dict(data: Mapping[str, Any]) -> EvidenceRecord:
    return EvidenceRecord(**dict(data))


def channel_from_dict(data: Mapping[str, Any]) -> ChannelRecord:
    return ChannelRecord(**dict(data))


def transaction_from_dict(data: Mapping[str, Any]) -> TransactionRecord:
    return TransactionRecord(**dict(data))


def revenue_summary_dict(summary: RevenueSummary) -> Dict[str, Any]:
    return {
        "currency": summary.currency,
        "verified_transactions": summary.verified_transactions,
        "gross_revenue": summary.gross_revenue,
        "processor_fees": summary.processor_fees,
        "platform_fees": summary.platform_fees,
        "refunds": summary.refunds,
        "direct_costs": summary.direct_costs,
        "net_revenue": summary.net_revenue,
        "physical_form_fund": summary.physical_form_fund,
        "reinvestment_balance": summary.reinvestment_balance,
        "contingency_reserve": summary.contingency_reserve,
    }
