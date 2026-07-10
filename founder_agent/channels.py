"""Channel registry validation and authority-aware action planning."""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping

from .operator_models import ActionDecision, AuthorityClass, ChannelRecord, channel_from_dict


class ChannelUnavailableError(ValueError):
    """Raised when channel state is inconsistent or unknown."""


def load_channels(data: Mapping[str, object]) -> Dict[str, ChannelRecord]:
    channels = [channel_from_dict(item) for item in data.get("channels", [])]
    by_id = {channel.channel_id: channel for channel in channels}
    if len(by_id) != len(channels):
        raise ChannelUnavailableError("channel ids must be unique")
    return by_id


def plan_channel_action(
    action_id: str,
    experiment_id: str,
    description: str,
    channel_id: str,
    authority_class: str,
    channels: Mapping[str, ChannelRecord],
) -> ActionDecision:
    if channel_id not in channels:
        return ActionDecision(
            action_id=action_id,
            experiment_id=experiment_id,
            description=description,
            authority_class=authority_class,
            channel_id=channel_id,
            executable_now=False,
            blocked_reason="Channel is not present in the registry.",
        )

    channel = channels[channel_id]
    authority = AuthorityClass(authority_class)
    if authority == AuthorityClass.HUMAN_IDENTITY_REQUIRED:
        return ActionDecision(
            action_id=action_id,
            experiment_id=experiment_id,
            description=description,
            authority_class=authority.value,
            channel_id=channel_id,
            executable_now=False,
            blocked_reason="A human must complete identity, legal, banking, tax, or account-owner steps.",
        )
    if authority == AuthorityClass.PREAUTHORIZED_WHEN_CONNECTED and not channel.agent_has_access:
        return ActionDecision(
            action_id=action_id,
            experiment_id=experiment_id,
            description=description,
            authority_class=authority.value,
            channel_id=channel_id,
            executable_now=False,
            blocked_reason="The channel is not connected to the agent.",
        )
    if not channel.agent_has_access:
        return ActionDecision(
            action_id=action_id,
            experiment_id=experiment_id,
            description=description,
            authority_class=authority.value,
            channel_id=channel_id,
            executable_now=False,
            blocked_reason="The agent does not currently have access to this channel.",
        )
    return ActionDecision(
        action_id=action_id,
        experiment_id=experiment_id,
        description=description,
        authority_class=authority.value,
        channel_id=channel_id,
        executable_now=True,
    )


def channels_requiring_human_identity(channels: Iterable[ChannelRecord]) -> List[ChannelRecord]:
    return [channel for channel in channels if channel.human_verification_required and not channel.account_exists]
