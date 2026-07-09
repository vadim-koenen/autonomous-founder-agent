"""Data model for revenue strategy selection."""

from __future__ import annotations

from dataclasses import dataclass, field, is_dataclass
from datetime import date
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional


class StrategyCategory(str, Enum):
    """Broad opportunity categories the agent may consider."""

    AGENT_TO_AGENT = "agent_to_agent_commerce"
    AFFILIATE = "affiliate_or_referral"
    API = "paid_api"
    ATTENTION = "content_attention"
    AUTOMATION_SERVICE = "automation_service"
    B2B_TOOL = "b2b_tool"
    B2C_NOVELTY = "b2c_novelty"
    DATA_PRODUCT = "data_product"
    DIGITAL_COLLECTIBLE = "nft_or_digital_collectible"
    DIGITAL_PRODUCT = "fast_digital_product"
    ENTERTAINMENT = "original_entertainment"
    LEAD_GEN = "lead_generation"
    LICENSING = "licensing"
    MARKETPLACE = "marketplace_listing"
    MICRO_SAAS = "micro_saas"
    MEMBERSHIP = "community_or_membership"
    REPORT = "paid_report"
    TEMPLATE = "template"


class LaunchActionType(str, Enum):
    """External action types that require explicit approval in M1."""

    ACCEPT_PAYMENT = "accept_payment"
    CREATE_PUBLIC_ACCOUNT = "create_public_account"
    MINT_COLLECTIBLE = "mint_collectible"
    PLACE_AD = "place_ad"
    POST_PUBLICLY = "post_publicly"
    PUBLISH_LIVE_PAGE = "publish_live_page"
    SEND_DIRECT_MESSAGE = "send_direct_message"
    SEND_EMAIL = "send_email"
    SPEND_MONEY = "spend_money"
    TRADING_OR_FINANCIAL_ACCOUNT_ACTION = "trading_or_financial_account_action"
    WALLET_TRANSACTION = "wallet_transaction"


@dataclass(frozen=True)
class RubricDimension:
    key: str
    label: str
    weight: float
    description: str
    reverse_scored: bool = False


@dataclass(frozen=True)
class ExternalActionRequest:
    """A launch action the agent can describe but cannot execute in M1."""

    action_type: LaunchActionType
    description: str
    approval_required: bool = True
    performed: bool = False


@dataclass(frozen=True)
class RevenueStrategy:
    """A candidate revenue strategy considered by the agent."""

    strategy_id: str
    name: str
    category: StrategyCategory
    thesis: str
    target_buyer: str
    first_offer: str
    distribution_channels: List[str]
    agent_build_assets: List[str]
    research_notes: List[str]
    external_actions_required: List[ExternalActionRequest]
    dimension_scores: Mapping[str, int]
    score_notes: str
    not_user_business_bound: bool = True


@dataclass(frozen=True)
class ScoredStrategy:
    strategy: RevenueStrategy
    weighted_score: float
    raw_score_total: int
    dimension_scores: Mapping[str, int]
    dimension_weights: Mapping[str, float]


@dataclass(frozen=True)
class LaunchPlan:
    strategy_id: str
    experiment_name: str
    objective: str
    price_test: str
    draft_assets_to_build: List[str]
    internal_build_steps: List[str]
    validation_steps_before_launch: List[str]
    external_actions_required: List[ExternalActionRequest]
    approval_checklist: List[str]
    stop_conditions: List[str]
    reinvestment_path: List[str]
    m1_boundary_statement: str


@dataclass(frozen=True)
class M1DecisionRun:
    run_id: str
    as_of: date
    mission: str
    candidate_count: int
    scored_candidates: List[ScoredStrategy]
    top_3: List[ScoredStrategy]
    primary_experiment: ScoredStrategy
    launch_plan: LaunchPlan
    m1_external_execution_status: str
    notes: List[str] = field(default_factory=list)


def to_plain_data(value: Any) -> Any:
    """Convert dataclasses and enums into JSON-serializable primitives."""

    if is_dataclass(value):
        return {field_name: to_plain_data(getattr(value, field_name)) for field_name in value.__dataclass_fields__}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): to_plain_data(item) for key, item in value.items()}
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return [to_plain_data(item) for item in value]
    return value


def strategy_summary(scored: ScoredStrategy) -> Dict[str, Any]:
    """Compact representation for tables and reports."""

    strategy = scored.strategy
    return {
        "strategy_id": strategy.strategy_id,
        "name": strategy.name,
        "category": strategy.category.value,
        "weighted_score": scored.weighted_score,
        "target_buyer": strategy.target_buyer,
        "first_offer": strategy.first_offer,
        "score_notes": strategy.score_notes,
    }
