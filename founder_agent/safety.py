"""M1 non-execution guardrails."""

from __future__ import annotations

from .models import ExternalActionRequest, LaunchActionType


class ExternalActionBlocked(RuntimeError):
    """Raised when M1 code attempts a prohibited external action."""


M1_RESTRICTED_ACTION_TYPES = {
    LaunchActionType.ACCEPT_PAYMENT,
    LaunchActionType.CREATE_PUBLIC_ACCOUNT,
    LaunchActionType.MINT_COLLECTIBLE,
    LaunchActionType.PLACE_AD,
    LaunchActionType.POST_PUBLICLY,
    LaunchActionType.PUBLISH_LIVE_PAGE,
    LaunchActionType.SEND_DIRECT_MESSAGE,
    LaunchActionType.SEND_EMAIL,
    LaunchActionType.SPEND_MONEY,
    LaunchActionType.TRADING_OR_FINANCIAL_ACCOUNT_ACTION,
    LaunchActionType.WALLET_TRANSACTION,
}


def describe_required_action(action_type: LaunchActionType, description: str) -> ExternalActionRequest:
    """Record a launch action as a plan item only."""

    return ExternalActionRequest(
        action_type=action_type,
        description=description,
        approval_required=True,
        performed=False,
    )


def assert_m1_can_only_plan(action: ExternalActionRequest) -> None:
    if action.performed:
        raise ExternalActionBlocked(f"M1 cannot mark external action as performed: {action.description}")
    if action.action_type in M1_RESTRICTED_ACTION_TYPES:
        raise ExternalActionBlocked(f"M1 may only describe this action, not execute it: {action.action_type.value}")


def assert_no_external_actions_performed(actions: list[ExternalActionRequest]) -> None:
    performed = [action for action in actions if action.performed]
    if performed:
        descriptions = [action.description for action in performed]
        raise ExternalActionBlocked(f"M1 performed external actions: {descriptions}")
