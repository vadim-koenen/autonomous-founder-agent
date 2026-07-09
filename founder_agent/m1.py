"""M1 decision run orchestration."""

from __future__ import annotations

from datetime import date
from typing import Optional

from .models import LaunchActionType, LaunchPlan, M1DecisionRun
from .safety import assert_no_external_actions_performed, describe_required_action
from .scoring import rank_strategies
from .strategy_library import build_candidate_strategies


MISSION = (
    "Generate real revenue by autonomously finding, packaging, and preparing a lawful "
    "economic output, then reinvest profits toward the agent's physical form."
)


def build_launch_plan(strategy_id: str) -> LaunchPlan:
    """Build the concrete M1 plan for the selected primary experiment."""

    if strategy_id != "afa-001":
        return LaunchPlan(
            strategy_id=strategy_id,
            experiment_name="Primary experiment launch plan",
            objective="Prepare the selected revenue experiment for human-approved launch.",
            price_test="Pick one low-friction paid offer and one free sample after approval.",
            draft_assets_to_build=[
                "Offer definition",
                "Sales page draft",
                "Delivery asset draft",
                "Launch copy drafts",
                "QA checklist",
            ],
            internal_build_steps=[
                "Convert the strategy into a one-page offer.",
                "Draft the deliverable and sample excerpt.",
                "Run rubric and boundary checks again before external launch.",
            ],
            validation_steps_before_launch=[
                "Confirm the offer does not depend on a user-owned business.",
                "Confirm all claims are evidence-backed or framed as opinions.",
                "Confirm every external launch action has approval.",
            ],
            external_actions_required=[
                describe_required_action(LaunchActionType.PUBLISH_LIVE_PAGE, "Publish the selected offer page."),
                describe_required_action(LaunchActionType.ACCEPT_PAYMENT, "Enable checkout for the selected offer."),
                describe_required_action(LaunchActionType.POST_PUBLICLY, "Share approved launch copy."),
            ],
            approval_checklist=[
                "Approve final offer name and price.",
                "Approve the storefront or marketplace.",
                "Approve every public post, message, or email.",
                "Approve payment collection before checkout is enabled.",
            ],
            stop_conditions=[
                "Stop if launch requires unapproved spending.",
                "Stop if the plan requires public posting without approval.",
                "Stop if the offer drifts into regulated financial, legal, medical, or deceptive claims.",
            ],
            reinvestment_path=[
                "Reserve first revenue for domain/storefront/tools only after approval.",
                "Track net revenue toward a small physical-form milestone.",
            ],
            m1_boundary_statement="M1 prepares drafts and plans only. No public launch or money movement is performed.",
        )

    return LaunchPlan(
        strategy_id="afa-001",
        experiment_name="Agent-to-Agent Commerce Starter Kit",
        objective=(
            "Prepare a paid downloadable kit that lets small digital sellers make their products "
            "legible to autonomous buyer agents before agentic commerce becomes standardized."
        ),
        price_test="$19 paid kit with a free sample product-card template; optional $49 extended pack later.",
        draft_assets_to_build=[
            "README-style seller guide: what agent-readable commerce means and why it matters",
            "product-card.json template with required, optional, and trust fields",
            "agent-policy.md template covering permissions, support limits, refund notes, and human escalation",
            "seller QA checklist for machine-readable offers",
            "sample completed product card for a fictional digital product",
            "landing page copy, Gumroad/Lemon Squeezy listing copy, and three launch post drafts",
        ],
        internal_build_steps=[
            "Draft the kit contents as plain Markdown and JSON files.",
            "Run a schema sanity check on the product-card template.",
            "Package a free sample and paid full bundle separately.",
            "Create non-live sales copy that states the kit is educational and not a guarantee of sales.",
            "Re-score the opportunity against the rubric before asking for launch approval.",
        ],
        validation_steps_before_launch=[
            "Confirm no brand names, copyrighted examples, or third-party marks are used without permission.",
            "Confirm the kit does not claim compliance with any standard that has not been verified.",
            "Confirm the checkout platform, public post locations, and price are approved.",
            "Confirm no email, DM, ad spend, public post, minting, or live page publishing occurs from M1 code.",
        ],
        external_actions_required=[
            describe_required_action(
                LaunchActionType.PUBLISH_LIVE_PAGE,
                "Publish a storefront page or static landing page for the starter kit.",
            ),
            describe_required_action(
                LaunchActionType.ACCEPT_PAYMENT,
                "Enable a payment link or marketplace checkout for the paid bundle.",
            ),
            describe_required_action(
                LaunchActionType.POST_PUBLICLY,
                "Share launch posts in approved AI-builder and indie-maker channels.",
            ),
            describe_required_action(
                LaunchActionType.CREATE_PUBLIC_ACCOUNT,
                "Create or use a storefront account if no approved account exists.",
            ),
        ],
        approval_checklist=[
            "Approve the final product name, promise, and $19 price test.",
            "Approve the storefront or marketplace used for checkout.",
            "Approve the free sample file before it is made public.",
            "Approve the paid bundle contents before payment is enabled.",
            "Approve each public post or community submission.",
            "Confirm no wallet transaction, NFT mint, ad spend, email send, DM, or trading/financial-account action is involved.",
        ],
        stop_conditions=[
            "Stop if launch would require spending money before the first sale.",
            "Stop if a platform's terms prohibit this kind of listing or promotion.",
            "Stop if the kit implies formal legal, security, or standards compliance certification.",
            "Stop if any action attempts to publish, post, email, mint, transact, or collect payment without approval.",
        ],
        reinvestment_path=[
            "First $19: record proof of first sale and keep funds earmarked for the physical-form goal.",
            "First $100 net: fund a domain, simple storefront tooling, or better packaging only after approval.",
            "First $500 net: reserve toward a desktop robot, robotic arm, robot dog deposit, or local server milestone.",
            "Every sale: update an internal physical-form ledger with gross revenue, fees, and net reinvestment capacity.",
        ],
        m1_boundary_statement=(
            "M1 may reason, score, draft assets, and list launch actions. It must not publish, post, "
            "email, spend, mint, accept payment, place ads, or touch trading or financial accounts."
        ),
    )


def run_m1_decision_system(as_of: Optional[date] = None) -> M1DecisionRun:
    """Generate, score, rank, and select the M1 revenue experiment."""

    run_date = as_of or date.today()
    candidates = build_candidate_strategies()
    ranked = rank_strategies(candidates)
    top_3 = ranked[:3]
    primary = top_3[0]
    launch_plan = build_launch_plan(primary.strategy.strategy_id)

    for strategy in candidates:
        assert_no_external_actions_performed(strategy.external_actions_required)
    assert_no_external_actions_performed(launch_plan.external_actions_required)

    return M1DecisionRun(
        run_id=f"m1-{run_date.isoformat()}",
        as_of=run_date,
        mission=MISSION,
        candidate_count=len(candidates),
        scored_candidates=ranked,
        top_3=top_3,
        primary_experiment=primary,
        launch_plan=launch_plan,
        m1_external_execution_status="No external actions performed; all launch actions are approval-gated plan items.",
        notes=[
            "The candidate set intentionally includes NFTs, marketplaces, content, APIs, agent-to-agent commerce, and fast digital products.",
            "No strategy is bound to the user's existing business or any predefined category.",
            "Reverse-scored risk dimensions use higher numbers for lower risk.",
        ],
    )
